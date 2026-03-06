import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh
import os
import pytz
from streamlit_gsheets import GSheetsConnection # type: ignore
conn = st.connection("gsheets", type=GSheetsConnection)
# ==========================================
# 1. DATABASE SETUP & HELPERS
# ==========================================
ADMIN_PASSWORD = "admin123" 
comp_db_global = get_companies()
COMPANY_LIST = comp_db_global["Company_Name"].tolist()
# --- DATABASE HELPERS ---

def get_now_ist():
    # Define IST timezone
    ist = pytz.timezone('Asia/Kolkata')
    # Get current time in IST
    return datetime.now(ist).replace(tzinfo=None)


def get_companies():
    # This pulls your company names and rates from the "Companies" tab
    try:
        df = conn.read(worksheet="Companies", ttl=0)
        if df.empty:
            # Fallback if the sheet is accidentally cleared
            return pd.DataFrame({"Company_Name": ["Default Co"], "Hourly_Rate": [0.0]})
        return df
    except:
        # Emergency fallback
        return pd.DataFrame({"Company_Name": ["Error Loading"], "Hourly_Rate": [0.0]})

def save_companies(df):
    # This saves changes back to the "Companies" tab
    conn.update(worksheet="Companies", data=df)


def to_dt(str_val):
    if str_val == "N/A" or not isinstance(str_val, str) or str_val == "":
        return None
    try:
        # Try 12-hour format first
        return datetime.strptime(str_val, "%Y-%m-%d %I:%M:%S %p")
    except:
        try:
            # Fallback for old 24-hour records
            return datetime.strptime(str_val, "%Y-%m-%d %H:%M:%S")
        except:
            # If both fail, return None
            return None
@st.fragment(run_every="1s")
def render_timer(deadline_str):
    deadline_dt = to_dt(deadline_str)
    if deadline_dt:
        diff = deadline_dt - get_now_ist()
        secs = int(diff.total_seconds())
        if secs > 0:
            st.metric("⏳ Time Remaining", f"{secs//60}m {secs%60}s")
        else:
            st.error("⚠️ OVERDUE")
            st.metric("Time Overdue", f"{abs(secs)//60}m {abs(secs)%60}s")

TASK_COLS = ["Employee", "Company", "Task", "Limit_Mins", "Assign_Time", "Start_Time", 
             "Deadline", "Submit_Time", "Time_Variance", "Status", "Flag", "Pause_Start", 
             "Scheduled_Date", "Frequency", "Total_Paused_Mins", "Pause_Count"]
USER_COLS = ["Username", "Password", "Department"]

for db, cols in {TASK_DB: TASK_COLS, USER_DB: USER_COLS}.items():
    if not os.path.exists(db):
        pd.DataFrame(columns=cols).to_csv(db, index=False)

def get_tasks():
    # This pulls fresh data from your "Tasks" tab in Google Sheets
    df = conn.read(worksheet="Tasks", ttl=0).fillna("N/A").astype(str)
    if "Remarks" not in df.columns:
        df["Remarks"] = ""
    # Keep this for your sorting logic
    df['Assign_DT'] = pd.to_datetime(df['Assign_Time'], errors='coerce')
    return df

def save_tasks(df):
    # Remove the helper column before saving back to the cloud
    if 'Assign_DT' in df.columns:
        df = df.drop(columns=['Assign_DT'])
    conn.update(worksheet="Tasks", data=df)
def get_users(): 
    return conn.read(worksheet="Users", ttl=0).astype(str)

def save_users(df): 
    conn.update(worksheet="Users", data=df)
# ==========================================
# RECURRING TASK LOGIC (STEP 2)
# ==========================================
def handle_recurring_tasks(finished_row):
    """Creates a new task based on the frequency when one is finished."""
    # If the frequency is 'Once', we don't need to create a new task
    if finished_row['Frequency'] == "Once":
        return
    
    # Calculate the next scheduled date based on frequency
    try:
        current_sched = datetime.strptime(finished_row['Scheduled_Date'], "%Y-%m-%d")
    except:
        return # Exit if date format is wrong

    if finished_row['Frequency'] == "Daily":
        next_date = current_sched + timedelta(days=1)
    elif finished_row['Frequency'] == "Weekly":
        next_date = current_sched + timedelta(weeks=1)
    elif finished_row['Frequency'] == "Semi-Monthly":
        next_date = current_sched + timedelta(days=15)
    elif finished_row['Frequency'] == "Monthly":
        next_date = current_sched + timedelta(days=30)
    
    # Prepare the data for the next recurring instance
    df = get_tasks()
    new_task = finished_row.copy()
    new_task['Scheduled_Date'] = next_date.strftime("%Y-%m-%d")
    new_task['Assign_Time'] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
    new_task['Status'] = "Pending"
    new_task['Start_Time'] = "Waiting"
    new_task['Deadline'] = "N/A"
    new_task['Submit_Time'] = "N/A"
    new_task['Time_Variance'] = "N/A"
    new_task['Flag'] = "⚪"
    new_task['Pause_Start'] = "N/A"
    
    # Save the future task to the CSV
    updated_df = pd.concat([df, pd.DataFrame([new_task])], ignore_index=True)
    save_tasks(updated_df)

# ==========================================
# 2. LOGIN PAGE VS DASHBOARD CONTROL
# ==========================================
st.set_page_config(page_title="Corp-Task Pro", layout="wide")

if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None

# If not logged in, show login UI and stop
if st.session_state.role is None:
    # Use a container to ensure login UI is isolated
    login_container = st.container()
    with login_container:
        st.title("🚩 ZSM Task Control Center")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Admin Login")
            pwd = st.text_input("Admin Password", type="password", key="admin_pwd_input")
            if st.button("Login as Admin", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.role = "Admin"
                    st.rerun()
                else:
                    st.error("Invalid Admin Password")
        with col2:
            st.subheader("Employee Login")
            u_name = st.text_input("Username", key="emp_user_input").strip()
            u_pwd = st.text_input("Password", type="password", key="emp_pwd_input").strip()
            if st.button("Login as Employee", use_container_width=True):
                users = get_users()
                match = users[(users['Username'] == u_name) & (users['Password'] == u_pwd)]
                if not match.empty:
                    st.session_state.role = "Employee"
                    st.session_state.user = u_name
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    st.stop() # CRITICAL: This stops the script from showing the dashboard below

# ==========================================
# 3. DASHBOARD UI (ONLY REACHED IF LOGGED IN)
# ==========================================

# Sidebar Logout (Shared)
st.sidebar.title(f"Logged in as: {st.session_state.role}")
if st.session_state.user:
    st.sidebar.write(f"User: {st.session_state.user}")

if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.session_state.user = None
    st.rerun()

# --- ADMIN VIEW ---
if st.session_state.role == "Admin":
    menu = st.sidebar.radio("Main Menu", ["Dashboard", "Reports & Overrides", "User Management", "Company Management"])
    
    if menu == "Dashboard":
        st.title("👨‍💼 Task Assignment")
        
        # --- PART 1: PREPARE LIST WITH DEPARTMENTS ---
        users_df = get_users()
        if not users_df.empty:
            # Create list: "John (Tax)"
            u_display_list = users_df.apply(lambda x: f"{x['Username']} ({x.get('Department', 'N/A')})", axis=1).tolist()
            # Map "John (Tax)" -> "John"
            user_map = dict(zip(u_display_list, users_df['Username']))
        else:
            u_display_list = ["No Users Available"]
            user_map = {}

        msg_spot = st.empty()

        with st.form("task_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: 
                # Use the display list for the dropdown
                selected_display = st.selectbox("Assign To Employee", u_display_list)
            with c2: 
                # Fetch companies from Google Sheets
                comp_db = get_companies()
                # Ensure we use 'Company_Name' to match your sheet header
                comp = st.selectbox("Select Company", comp_db["Company_Name"].tolist())
            with c3: 
                mins = st.number_input("Minutes Allowed", min_value=1, value=15)
            
            # --- SCHEDULING FIELDS ---
            c4, c5 = st.columns(2)
            with c4: 
                sched_date = st.date_input("Schedule Date", get_now_ist())
            with c5: 
                freq = st.selectbox("Repeat Frequency", ["Once", "Daily", "Weekly", "Semi-Monthly", "Monthly"])

            tsk = st.text_area("Task Description")
            submitted = st.form_submit_button("🚀 SCHEDULE / ASSIGN TASK")
            
            if submitted:
                if not u_display_list or u_display_list == ["No Users Available"]:
                    st.error("Cannot assign task: No employees found.")
                elif tsk.strip() == "":
                    st.error("Please enter a task description.")
                else:
                    # --- GET CLEAN USERNAME ---
                    emp = user_map.get(selected_display, selected_display)
                    
                    # Fetch existing tasks from Google Sheets
                    df = get_tasks()
                    
                    # Prepare the new row with ALL necessary columns
                    new_row = {
                        "Employee": emp, 
                        "Company": comp, 
                        "Task": tsk, 
                        "Limit_Mins": str(mins), 
                        "Assign_Time": get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p"),
                        "Start_Time": "Waiting", 
                        "Deadline": "N/A", 
                        "Submit_Time": "N/A", 
                        "Time_Variance": "N/A", 
                        "Status": "Pending", 
                        "Flag": "⚪", 
                        "Pause_Start": "N/A",
                        "Scheduled_Date": sched_date.strftime("%Y-%m-%d"),
                        "Frequency": freq,
                        "Total_Paused_Mins": 0,
                        "Pause_Count": 0,
                        "Remarks": ""
                    }
                    
                    # Save the updated dataframe to Google Sheets
                    updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_tasks(updated_df)
                    
                    # --- SUCCESS EFFECTS ---
                    st.toast(f"Task scheduled for {emp}!", icon='✅')
                    msg_spot.success(f"🎉 SUCCESS: Task for {comp} scheduled for {sched_date}!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()

    elif menu == "Reports & Overrides":
        st.title("📊 Global Performance Reports & Overrides")
        
        # Load fresh data
        df = get_tasks()
        
        # --- FILTERS ---
        f1, f2, f3 = st.columns(3)
        c_filt = f1.multiselect("Filter by Company", COMPANY_LIST)
        e_filt = f2.multiselect("Filter by Employee", get_users()['Username'].tolist())
        s_filt = f3.multiselect("Filter by Status", ["Pending", "Running", "Paused", "Finished"])
        
        if c_filt: df = df[df['Company'].isin(c_filt)]
        if e_filt: df = df[df['Employee'].isin(e_filt)]
        if s_filt: df = df[df['Status'].isin(s_filt)]
        # ==========================================
        # NEW: EXCEL EXPORT BUTTON
        # ==========================================
        if not df.empty:
            st.write("---")
            # Create a buffer to hold the excel data
            import io
            buffer = io.BytesIO()
            
            # Clean the dataframe for export (remove internal columns)
            export_df = df.copy()
            if 'Assign_DT' in export_df.columns:
                export_df = export_df.drop(columns=['Assign_DT'])
            
            # Use Pandas to write to Excel
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='TaskReport')
            
            # Create the download button
            st.download_button(
                label="📥 Download Report as Excel",
                data=buffer.getvalue(),
                file_name=f"Task_Report_{get_now_ist().strftime('%Y-%m-%d_%I-%M-%p')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.write("---")
        # ==========================================

        # ... (Rest of your existing code: Headers and for idx, row in df.iterrows():)        
        
        if df.empty:
            st.info("No tasks match these filters.")
        else:
            # Display Headers for the custom table
            h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 2, 2])
            h1.write("**Employee/Company**")
            h2.write("**Task Description**")
            h3.write("**Status/Mins**")
            h4.write("**Time Info**")
            h5.write("**Actions**")
            st.divider()

            for idx, row in df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 2])
                
                # Column 1: Who & Where
                col1.write(f"👤 {row['Employee']}")
                col1.caption(f"🏢 {row['Company']}")
                
                # Column 2: Task
                col2.write(row['Task'])
                
                # Column 3: Status & Limit
                status_color = {"Pending": "⚪", "Running": "🔵", "Paused": "🟡", "Finished": row['Flag']}
                col3.write(f"{status_color.get(row['Status'], '⚪')} {row['Status']}")
                col3.write(f"⏱️ {row['Limit_Mins']} mins")
                
                # Column 4: Time Details
                col4.caption(f"Assigned: {row['Assign_Time']}")
                if row['Submit_Time'] != "N/A":
                    col4.caption(f"Submitted: {row['Submit_Time']}")

                # Column 5: Action Buttons
                edit_btn = col5.button("✏️ Edit", key=f"edit_task_{idx}")
                del_btn = col5.button("🗑️ Delete", key=f"del_task_{idx}")

                # --- DELETE LOGIC ---
                if del_btn:
                    full_df = get_tasks() # Get latest
                    full_df = full_df.drop(idx)
                    save_tasks(full_df)
                    st.toast("Task deleted successfully!")
                    time.sleep(1)
                    st.rerun()

                # --- EDIT LOGIC (Inline Form) ---
                if st.session_state.get(f"is_editing_{idx}", False):
                    with st.container(border=True):
                        st.write(f"**Modifying Task for {row['Employee']}**")
                        new_mins = st.number_input("Change Minutes Allowed", min_value=1, value=int(float(row['Limit_Mins'])), key=f"new_min_{idx}")
                        new_status = st.selectbox("Change Status", ["Pending", "Running", "Paused", "Finished"], index=["Pending", "Running", "Paused", "Finished"].index(row['Status']), key=f"new_stat_{idx}")
                        
                        c_save, c_cancel = st.columns(2)
                        if c_save.button("💾 Save Overrides", key=f"save_over_{idx}"):
                            full_df = get_tasks()
                            full_df.at[idx, 'Limit_Mins'] = str(new_mins)
                            full_df.at[idx, 'Status'] = new_status
                            
                            # If admin changes time while task is running, we must recalculate the Deadline
                            if new_status == "Running" and row['Start_Time'] != "Waiting":
                                start_dt = to_dt(row['Start_Time'])
                                if start_dt:
                                    new_deadline = start_dt + timedelta(minutes=new_mins)
                                    full_df.at[idx, 'Deadline'] = new_deadline.strftime("%Y-%m-%d %H:%M:%S")
                            
                            save_tasks(full_df)
                            st.session_state[f"is_editing_{idx}"] = False
                            st.success("Task updated!")
                            time.sleep(1)
                            st.rerun()
                            
                        if c_cancel.button("Cancel", key=f"cancel_over_{idx}"):
                            st.session_state[f"is_editing_{idx}"] = False
                            st.rerun()

                if edit_btn:
                    st.session_state[f"is_editing_{idx}"] = True
                    st.rerun()

    elif menu == "User Management":
        st.title("👥 User Management")
        u_df = get_users()
        with st.form("add_user", clear_on_submit=True):
            st.subheader("Add New Employee")
            c1, c2, c3 = st.columns(3)
            with c1: nu = st.text_input("New Username")
            with c2: np = st.text_input("New Password")
            # --- NEW DEPARTMENT DROPDOWN ---
            with c3: dept = st.selectbox("Department", ["Accountant", "Tax", "Audit", "Payroll", "Admin Support", "Notices", "Sales Tax", "Book Keeping"])
            
            if st.form_submit_button("➕ Save User"):
                if nu and np:
                    if nu in u_df['Username'].values:
                        st.error("User already exists!")
                    else:
                        # Save the username, password, and department
                        new_u = pd.DataFrame([{"Username": nu, "Password": np, "Department": dept}])
                        u_df = pd.concat([u_df, new_u], ignore_index=True)
                        save_users(u_df)
                        st.success(f"User {nu} added to {dept}!")
                        time.sleep(1); st.rerun()
                else: st.warning("Fill all fields.")
        st.divider()
        st.subheader("Current Employees")
        
        if u_df.empty:
            st.info("No users found.")
        else:
            # Header Row
            h1, h2, h3 = st.columns([2, 2, 2])
            h1.write("**Username**")
            h2.write("**Password**")
            h3.write("**Actions**")
            st.divider()

            for i, r in u_df.iterrows():
                row_c1, row_c2, row_c3 = st.columns([2, 2, 2])
                row_c1.write(r['Username'])
                
                # Password Display with Toggle
                is_visible = st.toggle("Show", key=f"show_{i}")
                row_c2.write(f"`{r['Password']}`" if is_visible else "********")
                
                # Action Buttons (Edit and Delete)
                btn_col1, btn_col2 = row_c3.columns(2)
                
                # EDIT PASSWORD LOGIC
                if btn_col1.button("✏️ Edit", key=f"edt_{i}"):
                    st.session_state[f"editing_{i}"] = True

                if btn_col2.button("🗑️ Delete", key=f"del_{i}"):
                    save_users(u_df.drop(i))
                    st.toast("User deleted")
                    time.sleep(0.5); st.rerun()

                # If Edit is clicked, show an inline input field
                if st.session_state.get(f"editing_{i}", False):
                    with st.container(border=True):
                        new_pass = st.text_input(f"New Password for {r['Username']}", key=f"newpass_{i}")
                        c_save, c_cancel = st.columns(2)
                        if c_save.button("💾 Save Update", key=f"save_upd_{i}"):
                            if new_pass:
                                u_df.at[i, 'Password'] = new_pass
                                save_users(u_df)
                                st.session_state[f"editing_{i}"] = False
                                st.success("Password Updated!")
                                time.sleep(1); st.rerun()
                            else:
                                st.error("Password cannot be empty")
                        if c_cancel.button("✖️ Cancel", key=f"can_upd_{i}"):
                            st.session_state[f"editing_{i}"] = False
                            st.rerun()
    elif menu == "Company Management":
            st.title("🏢 Company & Financial Management")
            
            tab_a, tab_b = st.tabs(["Add/Edit Companies", "💰 Revenue Report"])
            
            with tab_a:
                comp_df = get_companies()
                with st.expander("➕ Add New Company"):
                    c_name = st.text_input("Company Name")
                    c_rate = st.number_input("Hourly Billing Rate ($)", min_value=0.0, step=1.0)
                    if st.button("Save to Database"):
                        if c_name and c_name not in comp_df["Company Name"].values:
                            new_row = pd.DataFrame([{"Company Name": c_name.strip(), "Hourly Rate": c_rate}])
                            save_companies(pd.concat([comp_df, new_row], ignore_index=True))
                            st.success(f"Added {c_name}!"); time.sleep(1); st.rerun()

            st.subheader("Client List")
            st.dataframe(comp_df, use_container_width=True)
            
            to_del = st.selectbox("Select Company to Delete", ["---"] + comp_df["Company Name"].tolist())
            if st.button("🗑️ Delete Selected"):
                if to_del != "---":
                    save_companies(comp_df[comp_df["Company Name"] != to_del])
                    st.warning(f"Deleted {to_del}"); time.sleep(1); st.rerun()

            with tab_b:
                st.subheader("Earnings (Finished Tasks)")
                t_df = get_tasks()
                c_df = get_companies()
                # Ensure rates are numbers for calculation
                c_df["Hourly Rate"] = pd.to_numeric(c_df["Hourly Rate"], errors='coerce').fillna(0)
                
                finished = t_df[t_df["Status"] == "Finished"].copy()
                
                if not finished.empty:
                    def calc_h(r):
                        s, f = to_dt(r['Start_Time']), to_dt(r['Submit_Time'])
                        return (f - s).total_seconds() / 3600 if s and f else 0.0
                    
                    finished['Hours'] = finished.apply(calc_h, axis=1)
                    report = finished.merge(c_df, left_on="Company", right_on="Company Name", how="left")
                    report["Total Billable"] = report["Hours"] * report["Hourly Rate"]
                    
                    st.metric("Total Revenue", f"${report['Total Billable'].sum():,.2f}")
                    st.dataframe(report[["Company", "Employee", "Task", "Hours", "Hourly Rate", "Total Billable"]], use_container_width=True)
                else:
                    st.info("No finished tasks found.")                            

# --- EMPLOYEE VIEW ---
elif st.session_state.role == "Employee":
    tab1, tab2 = st.tabs(["🚀 Active Tasks", "📜 My Reports"])
    
    with tab1:
        st.title(f"👷 {st.session_state.user}'s Workspace")
        df = get_tasks()
        today_start = get_now_ist().replace(hour=0, minute=0, second=0)
# --- STEP 5: FILTER BY DATE ---
        today_str = get_now_ist().strftime("%Y-%m-%d")
        
        # Only show tasks for this user that are NOT finished and whose date has arrived
        active_tasks = df[
            (df["Employee"] == st.session_state.user) & 
            (df["Status"] != "Finished") &
            (df["Scheduled_Date"] <= today_str)
        ]
        if active_tasks.empty:
            st.info("No active tasks for today.")
        
        for idx, row in active_tasks.iterrows():
            with st.container(border=True):
                st.subheader(f"🏢 {row['Company']}")
                st.write(f"**Task:** {row['Task']}")
        
                # --- REPLACE THE OLD BUTTON LOGIC WITH THIS ---
                if row["Status"] == "Pending":
                    if st.button("▶️ ACCEPT & START", key=f"s_{idx}"):
                        now = get_now_ist()
                        try:
                            # Convert to float then int to handle strings like "15.0"
                            mins_val = int(float(str(row["Limit_Mins"])))
                        except:
                            mins_val = 15 # Default fallback
                        
                        deadline = now + timedelta(minutes=mins_val)
                        
                        df.at[idx, "Start_Time"] = now.strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Deadline"] = deadline.strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Status"] = "Running"
                        save_tasks(df)
                        st.rerun()
                # --- END OF REPLACEMENT ---

                elif row["Status"] == "Running":
                    # This calls the fragment to tick every second
                    if not st.session_state.get(f"finish_mode_{idx}", False):
                        render_timer(row["Deadline"])
                    else:
                        st.warning("⚠️ Timer stopped. Waiting for remarks.")  

                    # Indent these lines so they stay inside the 'elif'
                    c1, c2 = st.columns(2)
                    
                    if c1.button("⏸️ PAUSE", key=f"p_{idx}"):
                        df.at[idx, "Pause_Start"] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Status"] = "Paused"
                        current_count = int(float(str(row.get("Pause_Count", 0))))
                        df.at[idx, "Pause_Count"] = current_count + 1
                        save_tasks(df)
                        st.rerun()
                        
                    if c2.button("✅ FINISH", key=f"f_{idx}"):
                        st.session_state[f"finish_time_{idx}"] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                        st.session_state[f"finish_mode_{idx}"] = True

                    # --- REMARK INPUT AREA ---
                    if st.session_state.get(f"finish_mode_{idx}", False):
                        st.markdown("---")
                        frozen_time = st.session_state[f"finish_time_{idx}"]
                        st.write(f"⏱️ Time Captured: **{frozen_time}**")
                        
                        remark_input = st.text_area("Final Remarks", key=f"txt_{idx}", placeholder="Enter task details or reason for delay...")
                        
                        sub_c1, sub_c2 = st.columns(2)
                        
                        if sub_c1.button("Confirm Submit", key=f"save_{idx}", type="primary"):
                            finish_dt = to_dt(frozen_time)
                            deadline_dt = to_dt(row["Deadline"])
                            var = int((finish_dt - deadline_dt).total_seconds())
                            
                            df.at[idx, "Flag"] = "🟢 GREEN" if var <= 0 else "🔴 RED"
                            df.at[idx, "Submit_Time"] = frozen_time
                            df.at[idx, "Time_Variance"] = f"{'+' if var > 0 else '-'}{abs(var)//60:02d}:{abs(var)%60:02d}"
                            df.at[idx, "Status"] = "Finished"
                            df.at[idx, "Remarks"] = remark_input # This saves the text
                            
                            save_tasks(df)
                            del st.session_state[f"finish_mode_{idx}"]
                            del st.session_state[f"finish_time_{idx}"]
                            handle_recurring_tasks(df.iloc[idx]) 
                            st.rerun()

                        if sub_c2.button("Cancel", key=f"can_{idx}"):
                            st.session_state[f"finish_mode_{idx}"] = False
                            st.rerun()                       
                        
                        # --- SAVE CURRENT TASK ---
                        save_tasks(df)
                        
                        # --- ADD THIS LINE HERE (STEP 4) ---
                        handle_recurring_tasks(df.iloc[idx]) 
                        
                        st.rerun()
                elif row["Status"] == "Paused":
                    st.warning("☕ TASK PAUSED")
                    if st.button("▶️ RESUME", key=f"r_{idx}"):
                        p_start = to_dt(row["Pause_Start"])
                        now = get_now_ist()
                        pause_dur = now - p_start
                        mins_paused = int(pause_dur.total_seconds() // 60)
                        current_total_paused = float(str(row.get("Total_Paused_Mins", 0)))
                        df.at[idx, "Total_Paused_Mins"] = str(round(current_total_paused + mins_paused, 2))
                        new_deadline = to_dt(row["Deadline"]) + pause_dur
                        df.at[idx, "Deadline"] = new_deadline.strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Status"] = "Running"
                        df.at[idx, "Pause_Start"] = "N/A"
                        save_tasks(df); st.rerun()

    with tab2:
        st.title("📊 Work History")
        df = get_tasks()
        today_start = get_now_ist().replace(hour=0, minute=0, second=0)
        my_history = df[df["Employee"] == st.session_state.user]
        rep_type = st.radio("Period", ["Daily (Today)", "Monthly (30 Days)"], horizontal=True)
        since_date = today_start if "Daily" in rep_type else (get_now_ist() - timedelta(days=30))
        report_df = my_history[my_history["Assign_DT"] >= since_date].copy()
        
        def get_work_hours(r):
            s, f = to_dt(r['Start_Time']), to_dt(r['Submit_Time'])
            return round((f - s).total_seconds() / 3600, 2) if s and f else 0.0

        if not report_df.empty:
            # 1. Calculate work hours
            report_df['Hours'] = report_df.apply(get_work_hours, axis=1)
            
            # 2. Show Summary Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Work Hours", f"{report_df['Hours'].sum():.2f} hrs")
            c2.metric("Total Pauses", f"{pd.to_numeric(report_df['Pause_Count'], errors='coerce').sum():.0f}")
            c3.metric("Total Pause Time", f"{pd.to_numeric(report_df['Total_Paused_Mins'], errors='coerce').sum():.2f} mins")
            
            # 3. Show Detailed Dataframe
            st.dataframe(
                report_df[[
                    "Company", "Task", "Assign_Time", "Submit_Time", "Hours", "Pause_Count","Total_Paused_Mins", "Flag", "Remarks"]], 
                use_container_width=True
            )
        else:

            st.info("No records found.")




