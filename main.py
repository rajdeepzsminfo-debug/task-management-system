import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh
import pytz
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. DATABASE SETUP (GOOGLE SHEETS)
# ==========================================
ADMIN_PASSWORD = "admin123" 

# Create the connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Blueprints for your Google Sheet Tabs (Ensure headers in Sheets match these exactly)
TASK_COLS = [
    "Employee", "Company", "Task", "Limit_Mins", "Assign_Time", "Start_Time",
    "Deadline", "Submit_Time", "Time_Variance", "Status", "Flag",
    "Pause_Start", "Scheduled_Date", "Frequency", "Total_Paused_Mins", "Pause_Count", "Remarks"
]
USER_COLS = ["Username", "Password", "Department"]
COMPANY_COLS = ["Company Name"]

# --- IST Time Helper ---
def get_now_ist():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

# --- Date Translator (Handles Google Sheets weird text formats) ---
def to_dt(str_val):
    if str_val == "N/A" or str_val is None or str_val == "":
        return None
    str_val = str(str_val).strip()
    try:
        return datetime.strptime(str_val, "%Y-%m-%d %I:%M:%S %p")
    except:
        try:
            return datetime.strptime(str_val, "%Y-%m-%d %H:%M:%S")
        except:
            return None

# --- DATABASE HELPERS (REPLACES OLD CSV FUNCTIONS) ---

def get_tasks(): 
    """Fetches tasks from Google Sheets 'Tasks' tab."""
    df = conn.read(worksheet="Tasks", ttl=0)
    if df.empty:
        return pd.DataFrame(columns=TASK_COLS)
    df = df.fillna("N/A").astype(str)
    # Internal helper for sorting
    df['Assign_DT'] = pd.to_datetime(df['Assign_Time'], errors='coerce')
    if "Remarks" not in df.columns:
        df["Remarks"] = ""
    return df

def save_tasks(df): 
    """Saves tasks to Google Sheets 'Tasks' tab."""
    if 'Assign_DT' in df.columns: 
        df = df.drop(columns=['Assign_DT'])
    conn.update(worksheet="Tasks", data=df)

def get_users(): 
    """Fetches users from 'Users' tab."""
    df = conn.read(worksheet="Users", ttl=0)
    if df.empty:
        return pd.DataFrame(columns=USER_COLS)
    return df.astype(str)

def save_users(df): 
    """Saves users to 'Users' tab."""
    conn.update(worksheet="Users", data=df)

def get_companies():
    """Fetches companies from 'Companies' tab."""
    df = conn.read(worksheet="Companies", ttl=0)
    if df.empty:
        return pd.DataFrame(columns=COMPANY_COLS)
    return df

def save_companies(df):
    """Saves companies to 'Companies' tab."""
    conn.update(worksheet="Companies", data=df)

# --- FRAGMENT: THE LIVE TIMER ---
@st.fragment(run_every="1s")
def render_timer(deadline_str):
    deadline_dt = to_dt(deadline_str)
    if deadline_dt:
        now = get_now_ist()
        diff = deadline_dt.replace(tzinfo=None) - now.replace(tzinfo=None)
        secs = int(diff.total_seconds())
        if secs > 0:
            st.metric("⏳ Time Remaining", f"{secs//60}m {secs%60}s")
        else:
            st.error("⚠️ OVERDUE")
            st.metric("🚨 Time Overdue", f"{abs(secs)//60}m {abs(secs)%60}s")
    else:
        st.info("🕒 Timer will start once task begins.")
# ==========================================
# RECURRING TASK LOGIC (STEP 2)
# ==========================================
def handle_recurring_tasks(finished_row):
    """Creates a new task in Google Sheets based on frequency when one is finished."""
    
    # 1. If 'Once', stop here
    if finished_row['Frequency'] == "Once":
        return
    
    # 2. Calculate the next scheduled date
    try:
        # We ensure we are reading the date correctly from the sheet string
        current_sched = datetime.strptime(str(finished_row['Scheduled_Date']).strip(), "%Y-%m-%d")
    except:
        return # Exit if date format is wrong or empty

    # Frequency Math
    if finished_row['Frequency'] == "Daily":
        next_date = current_sched + timedelta(days=1)
    elif finished_row['Frequency'] == "Weekly":
        next_date = current_sched + timedelta(weeks=1)
    elif finished_row['Frequency'] == "Semi-Monthly":
        next_date = current_sched + timedelta(days=15)
    elif finished_row['Frequency'] == "Monthly":
        # Simplified monthly (30 days)
        next_date = current_sched + timedelta(days=30)
    else:
        return

    # 3. Fetch fresh data from Google Sheets to prepare for insertion
    df = get_tasks()
    
    # 4. Prepare the new row data
    # We create a dictionary to ensure we only include the columns we want
    new_task_data = {
        "Employee": str(finished_row['Employee']),
        "Company": str(finished_row['Company']),
        "Task": str(finished_row['Task']),
        "Limit_Mins": str(finished_row['Limit_Mins']),
        "Assign_Time": get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p"), # New assignment timestamp
        "Start_Time": "Waiting",
        "Deadline": "N/A",
        "Submit_Time": "N/A",
        "Time_Variance": "N/A",
        "Status": "Pending",
        "Flag": "⚪",
        "Pause_Start": "N/A",
        "Scheduled_Date": next_date.strftime("%Y-%m-%d"),
        "Frequency": str(finished_row['Frequency']),
        "Total_Paused_Mins": "0",
        "Pause_Count": "0",
        "Remarks": ""
    }
    
    # 5. Save to Google Sheets
    new_row_df = pd.DataFrame([new_task_data])
    updated_df = pd.concat([df, new_row_df], ignore_index=True)
    save_tasks(updated_df)

# ==========================================
# 2. LOGIN PAGE VS DASHBOARD CONTROL
# ==========================================
# This must be the very first Streamlit command after imports
st.set_page_config(page_title="Corp-Task Pro", layout="wide", page_icon="🚩")

# Initialize session states if they don't exist
if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None

# If not logged in, show login UI and stop
if st.session_state.role is None:
    # Use a container to ensure login UI is isolated
    login_container = st.container()
    with login_container:
        st.title("🚩 ZSM Task Control Center")
        st.markdown("---") # Visual separator
        
        col1, col2 = st.columns(2)
        
        # --- ADMIN LOGIN ---
        with col1:
            st.subheader("👨‍💼 Admin Login")
            pwd = st.text_input("Admin Password", type="password", key="admin_pwd_input")
            if st.button("Login as Admin", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.role = "Admin"
                    st.session_state.user = "Administrator" # Set a default name for admin
                    st.rerun()
                else:
                    st.error("❌ Invalid Admin Password")
        
        # --- EMPLOYEE LOGIN ---
        with col2:
            st.subheader("👥 Employee Login")
            u_name = st.text_input("Username", key="emp_user_input").strip()
            u_pwd = st.text_input("Password", type="password", key="emp_pwd_input").strip()
            
            if st.button("Login as Employee", use_container_width=True):
                # We pull the latest users from Google Sheets
                users = get_users()
                
                if not users.empty:
                    # SAFETY CHECK: Clean the data from Sheets (remove spaces/lowercase for comparison)
                    users['Username_Clean'] = users['Username'].astype(str).str.strip()
                    users['Password_Clean'] = users['Password'].astype(str).str.strip()
                    
                    # Try to find a match
                    match = users[(users['Username_Clean'] == u_name) & 
                                  (users['Password_Clean'] == u_pwd)]
                    
                    if not match.empty:
                        # Success! Save the actual Username from the Sheet
                        st.session_state.role = "Employee"
                        st.session_state.user = match.iloc[0]['Username']
                        st.success(f"Welcome back, {st.session_state.user}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid Credentials")
                else:
                    st.error("⚠️ No users found in database. Contact Admin.")
                    
    st.stop() # CRITICAL: Prevents the rest of the script from running until logged in
# ==========================================
# 3. DASHBOARD UI (GOOGLE SHEETS VERSION)
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
            # Create display name: "John (Tax)"
            u_display_list = users_df.apply(lambda x: f"{x['Username']} ({x.get('Department', 'N/A')})", axis=1).tolist()
            # Map "John (Tax)" back to "John" for database saving
            user_map = dict(zip(u_display_list, users_df['Username']))
        else:
            u_display_list = ["No Users Available"]
            user_map = {}

        msg_spot = st.empty()

        with st.form("task_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: 
                selected_display = st.selectbox("Assign To Employee", u_display_list)
            with c2: 
                # FETCH COMPANIES FROM GOOGLE SHEETS
                comp_db = get_companies()
                if not comp_db.empty:
                    comp_options = comp_db["Company Name"].tolist()
                else:
                    comp_options = ["No Companies Found"]
                comp = st.selectbox("Company Name", comp_options)
            with c3: 
                mins = st.number_input("Minutes Allowed", min_value=1, value=15)
            
            # --- SCHEDULING FIELDS ---
            c4, c5 = st.columns(2)
            with c4: sched_date = st.date_input("Schedule Date", get_now_ist())
            with c5: freq = st.selectbox("Repeat Frequency", ["Once", "Daily", "Weekly", "Semi-Monthly", "Monthly"])

            tsk = st.text_area("Task Description")
            submitted = st.form_submit_button("🚀 SCHEDULE / ASSIGN TASK")
            
            if submitted:
                if not u_display_list or u_display_list == ["No Users Available"]:
                    st.error("Cannot assign task: No employees found.")
                elif tsk.strip() == "":
                    st.error("Please enter a task description.")
                elif comp == "No Companies Found":
                    st.error("Please add a company in Company Management first.")
                else:
                    # GET CLEAN USERNAME
                    emp = user_map.get(selected_display, selected_display)
                    
                    df = get_tasks()
                    new_row = {
                        "Employee": str(emp), 
                        "Company": str(comp), 
                        "Task": str(tsk), 
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
                        "Total_Paused_Mins": "0",
                        "Pause_Count": "0",
                        "Remarks": "" # Added to keep columns aligned
                    }
                    
                    # Save to Google Sheets
                    new_df = pd.DataFrame([new_row])
                    updated_df = pd.concat([df, new_df], ignore_index=True)
                    save_tasks(updated_df)
                    
                    st.toast(f"Task scheduled for {emp}!", icon='✅')
                    msg_spot.success(f"🎉 SUCCESS: Task for {comp} scheduled for {sched_date}!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()

    elif menu == "Reports & Overrides":
        st.title("📊 Global Performance Reports & Overrides")
        
        # Load fresh data from Google Sheets
        df = get_tasks()
        
        # --- FILTERS ---
        f1, f2, f3 = st.columns(3)
        
        # FETCH LIVE LISTS FOR FILTERS
        all_companies = get_companies()["Company Name"].tolist()
        all_employees = get_users()['Username'].tolist()
        
        c_filt = f1.multiselect("Filter by Company", all_companies)
        e_filt = f2.multiselect("Filter by Employee", all_employees)
        s_filt = f3.multiselect("Filter by Status", ["Pending", "Running", "Paused", "Finished"])
        
        if c_filt: df = df[df['Company'].isin(c_filt)]
        if e_filt: df = df[df['Employee'].isin(e_filt)]
        if s_filt: df = df[df['Status'].isin(s_filt)]        
        
        
        
        # ==========================================
        # 3. ADMIN CONTROLS & REPORTS (GSHEETS VERSION)
        # ==========================================

        # --- EXCEL EXPORT BUTTON ---
        if not df.empty:
            st.write("---")
            import io
            buffer = io.BytesIO()
            
            export_df = df.copy()
            if 'Assign_DT' in export_df.columns:
                export_df = export_df.drop(columns=['Assign_DT'])
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='TaskReport')
            
            st.download_button(
                label="📥 Download Report as Excel",
                data=buffer.getvalue(),
                file_name=f"Task_Report_{get_now_ist().strftime('%Y-%m-%d_%I-%M-%p')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.write("---")

        # --- TASK LIST & OVERRIDES ---
        if df.empty:
            st.info("No tasks match these filters.")
        else:
            h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 2, 2])
            h1.write("**Employee/Company**")
            h2.write("**Task Description**")
            h3.write("**Status/Mins**")
            h4.write("**Time Info**")
            h5.write("**Actions**")
            st.divider()

            for idx, row in df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 2])
                
                # We use a Unique Key for every task to find it in Google Sheets later
                task_key = f"{row['Employee']}_{row['Assign_Time']}"
                
                col1.write(f"👤 {row['Employee']}")
                col1.caption(f"🏢 {row['Company']}")
                col2.write(row['Task'])
                
                status_color = {"Pending": "⚪", "Running": "🔵", "Paused": "🟡", "Finished": row['Flag']}
                col3.write(f"{status_color.get(row['Status'], '⚪')} {row['Status']}")
                col3.write(f"⏱️ {row['Limit_Mins']} mins")
                
                col4.caption(f"Assigned: {row['Assign_Time']}")
                if row['Submit_Time'] != "N/A":
                    col4.caption(f"Submitted: {row['Submit_Time']}")

                edit_btn = col5.button("✏️ Edit", key=f"edit_task_{idx}")
                del_btn = col5.button("🗑️ Delete", key=f"del_task_{idx}")

                # --- DELETE LOGIC (SAFE VERSION) ---
                if del_btn:
                    full_df = get_tasks()
                    # Find the row where both Employee and Assign_Time match exactly
                    full_df = full_df[~((full_df['Employee'] == row['Employee']) & (full_df['Assign_Time'] == row['Assign_Time']))]
                    save_tasks(full_df)
                    st.toast("Task deleted from Cloud!")
                    time.sleep(0.5); st.rerun()

                # --- EDIT LOGIC (SAFE VERSION) ---
                if st.session_state.get(f"is_editing_{idx}", False):
                    with st.container(border=True):
                        st.write(f"**Modifying Task for {row['Employee']}**")
                        new_mins = st.number_input("Change Minutes Allowed", min_value=1, value=int(float(row['Limit_Mins'])), key=f"new_min_{idx}")
                        new_status = st.selectbox("Change Status", ["Pending", "Running", "Paused", "Finished"], 
                                                index=["Pending", "Running", "Paused", "Finished"].index(row['Status']), key=f"new_stat_{idx}")
                        
                        c_save, c_cancel = st.columns(2)
                        if c_save.button("💾 Save Overrides", key=f"save_over_{idx}"):
                            full_df = get_tasks()
                            # Find specific row index in the fresh database
                            match_idx = full_df[(full_df['Employee'] == row['Employee']) & (full_df['Assign_Time'] == row['Assign_Time'])].index
                            
                            if not match_idx.empty:
                                target_idx = match_idx[0]
                                full_df.at[target_idx, 'Limit_Mins'] = str(new_mins)
                                full_df.at[target_idx, 'Status'] = new_status
                                
                                if new_status == "Running" and row['Start_Time'] != "Waiting":
                                    start_dt = to_dt(row['Start_Time'])
                                    if start_dt:
                                        new_deadline = start_dt + timedelta(minutes=new_mins)
                                        full_df.at[target_idx, 'Deadline'] = new_deadline.strftime("%Y-%m-%d %I:%M:%S %p")
                                
                                save_tasks(full_df)
                                st.session_state[f"is_editing_{idx}"] = False
                                st.success("Cloud Updated!")
                                time.sleep(1); st.rerun()
                        
                        if c_cancel.button("Cancel", key=f"cancel_over_{idx}"):
                            st.session_state[f"is_editing_{idx}"] = False
                            st.rerun()

                if edit_btn:
                    st.session_state[f"is_editing_{idx}"] = True
                    st.rerun()

    # --- USER MANAGEMENT (SAFE VERSION) ---
    elif menu == "User Management":
        st.title("👥 User Management")
        u_df = get_users()
        # (The form code remains largely the same, but use save_users(u_df))
        # Note: Use the "Matching by Username" logic for Deleting users provided in the first step.

    # --- COMPANY MANAGEMENT (GSHEETS TAB VERSION) ---
    elif menu == "Company Management":
        st.title("🏢 Company & Financial Management")
        tab_a, tab_b = st.tabs(["Add/Edit Companies", "💰 Revenue Report"])
        
        with tab_a:
            comp_df = get_companies()
            with st.expander("➕ Add New Company"):
                c_name = st.text_input("Company Name")
                c_rate = st.number_input("Hourly Billing Rate ($)", min_value=0.0, step=1.0)
                if st.button("Save to Database"):
                    if c_name:
                        # Refresh to check for duplicates
                        fresh_comp = get_companies()
                        if c_name.strip() not in fresh_comp["Company Name"].values:
                            new_row = pd.DataFrame([{"Company Name": c_name.strip(), "Hourly Rate": str(c_rate)}])
                            save_companies(pd.concat([fresh_comp, new_row], ignore_index=True))
                            st.success(f"Added {c_name}!"); time.sleep(1); st.rerun()
                        else: st.error("Company exists!")

            st.subheader("Client List")
            st.dataframe(comp_df, use_container_width=True)
            
            to_del = st.selectbox("Select Company to Delete", ["---"] + comp_df["Company Name"].tolist())
            if st.button("🗑️ Delete Selected"):
                if to_del != "---":
                    fresh_comp = get_companies()
                    fresh_comp = fresh_comp[fresh_comp["Company Name"] != to_del]
                    save_companies(fresh_comp)
                    st.warning(f"Deleted {to_del}"); time.sleep(1); st.rerun()

        with tab_b:
            st.subheader("Earnings (Finished Tasks)")
            t_df = get_tasks()
            c_df = get_companies()
            c_df["Hourly Rate"] = pd.to_numeric(c_df["Hourly Rate"], errors='coerce').fillna(0)
            
            finished = t_df[t_df["Status"] == "Finished"].copy()
            if not finished.empty:
                def calc_h(r):
                    s, f = to_dt(r['Start_Time']), to_dt(r['Submit_Time'])
                    return (f - s).total_seconds() / 3600 if s and f else 0.0
                
                finished['Hours'] = finished.apply(calc_h, axis=1)
                # Merge based on the Company Name column in the Sheet
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
        
        # Fetch fresh data from Google Sheets
        df = get_tasks()
        
        # Filter Logic: Only show tasks for this user that are NOT finished and date has arrived
        today_str = get_now_ist().strftime("%Y-%m-%d")
        active_tasks = df[
            (df["Employee"] == st.session_state.user) & 
            (df["Status"] != "Finished") &
            (df["Scheduled_Date"] <= today_str)
        ]
        
        if active_tasks.empty:
            st.info("No active tasks for today. Take a breather! ☕")
        
        for idx, row in active_tasks.iterrows():
            with st.container(border=True):
                st.subheader(f"🏢 {row['Company']}")
                st.write(f"**Task:** {row['Task']}")
                st.caption(f"Limit: {row['Limit_Mins']} mins")

                # --- 1. PENDING STATUS ---
                if row["Status"] == "Pending":
                    if st.button("▶️ ACCEPT & START", key=f"s_{idx}", use_container_width=True):
                        now = get_now_ist()
                        try:
                            # Handle potential string decimals from Sheets (e.g., "15.0")
                            mins_val = int(float(str(row["Limit_Mins"])))
                        except:
                            mins_val = 15
                        
                        deadline = now + timedelta(minutes=mins_val)
                        
                        df.at[idx, "Start_Time"] = now.strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Deadline"] = deadline.strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Status"] = "Running"
                        save_tasks(df)
                        st.rerun()

                # --- 2. RUNNING STATUS ---
                elif row["Status"] == "Running":
                    # Show the ticking timer fragment
                    if not st.session_state.get(f"finish_mode_{idx}", False):
                        render_timer(row["Deadline"])
                    else:
                        st.warning("⚠️ Timer stopped. Waiting for remarks.")

                    c1, c2 = st.columns(2)
                    
                    if c1.button("⏸️ PAUSE", key=f"p_{idx}", use_container_width=True):
                        df.at[idx, "Pause_Start"] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Status"] = "Paused"
                        try:
                            current_count = int(float(str(row.get("Pause_Count", 0))))
                        except:
                            current_count = 0
                        df.at[idx, "Pause_Count"] = str(current_count + 1)
                        save_tasks(df)
                        st.rerun()
                        
                    if c2.button("✅ FINISH", key=f"f_{idx}", use_container_width=True):
                        st.session_state[f"finish_time_{idx}"] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                        st.session_state[f"finish_mode_{idx}"] = True
                        st.rerun()

                    # --- REMARK / SUBMIT AREA ---
                    if st.session_state.get(f"finish_mode_{idx}", False):
                        st.markdown("---")
                        # Retrieve the time captured when they first clicked 'Finish'
                        frozen_time = st.session_state.get(f"finish_time_{idx}")
                        st.write(f"⏱️ Time Captured: **{frozen_time}**")
                        
                        remark_input = st.text_area(
                            "Final Remarks", 
                            key=f"txt_{idx}", 
                            placeholder="What did you achieve? Any blockers?"
                        )
                        
                        sub_c1, sub_c2 = st.columns(2)
                        
                        # FIX: Separated the key assignment to avoid VS Code errors (No walrus operator)
                        btn_key = f"save_{idx}"
                        
                        if sub_c1.button("Confirm Submit", key=btn_key, type="primary", use_container_width=True):
                            # 1. Calculate time difference
                            finish_dt = to_dt(frozen_time)
                            deadline_dt = to_dt(row["Deadline"])
                            
                            # Calculate Variance (Seconds)
                            if finish_dt and deadline_dt:
                                var_seconds = int((finish_dt - deadline_dt).total_seconds())
                                abs_var = abs(var_seconds)
                                variance_str = f"{'+' if var_seconds > 0 else '-'}{abs_var//60:02d}:{abs_var%60:02d}"
                                flag_val = "🟢 GREEN" if var_seconds <= 0 else "🔴 RED"
                            else:
                                variance_str = "N/A"
                                flag_val = "⚪"

                            # 2. Get fresh data and update the specific row
                            df = get_tasks()
                            
                            # Match by Employee and Assign_Time to ensure we hit the right row in Google Sheets
                            match_idx = df[(df['Employee'] == row['Employee']) & (df['Assign_Time'] == row['Assign_Time'])].index
                            
                            if not match_idx.empty:
                                target_idx = match_idx[0]
                                df.at[target_idx, "Status"] = "Finished"
                                df.at[target_idx, "Submit_Time"] = frozen_time
                                df.at[target_idx, "Time_Variance"] = variance_str
                                df.at[target_idx, "Flag"] = flag_val
                                df.at[target_idx, "Remarks"] = str(remark_input).replace(",", ";") # Clean for CSV/Sheets
                                
                                # 3. Save to Google Sheets
                                save_tasks(df)
                                
                                # 4. Trigger Recurring Task Logic
                                handle_recurring_tasks(df.iloc[target_idx])
                                
                                # 5. Clean up session state so the form disappears
                                if f"finish_mode_{idx}" in st.session_state:
                                    del st.session_state[f"finish_mode_{idx}"]
                                if f"finish_time_{idx}" in st.session_state:
                                    del st.session_state[f"finish_time_{idx}"]
                                
                                st.success("Task Submitted and Cloud Updated!")
                                time.sleep(1)
                                st.rerun()

                        # Cancel button to go back to the timer
                        if sub_c2.button("Cancel", key=f"can_{idx}", use_container_width=True):
                            st.session_state[f"finish_mode_{idx}"] = False
                            st.rerun()

                # --- 3. PAUSED STATUS ---
                elif row["Status"] == "Paused":
                    st.warning("☕ TASK PAUSED")
                    if st.button("▶️ RESUME", key=f"r_{idx}", use_container_width=True):
                        # 1. Fetch fresh data from Cloud
                        df = get_tasks()
                        
                        # Match the specific row
                        match_idx = df[(df['Employee'] == row['Employee']) & (df['Assign_Time'] == row['Assign_Time'])].index
                        
                        if not match_idx.empty:
                            target_idx = match_idx[0]
                            
                            # --- THE FIX: Convert String to Datetime safely ---
                            p_start_raw = row.get("Pause_Start", "N/A")
                            p_start = to_dt(str(p_start_raw)) # Ensure it's a string for the function
                            
                            now = get_now_ist()
                            
                            # Only perform math if p_start was successfully converted
                            if p_start and isinstance(p_start, datetime):
                                pause_dur = now - p_start
                                mins_paused = pause_dur.total_seconds() / 60
                                
                                try:
                                    # Convert previous pauses to float safely
                                    prev_total = row.get("Total_Paused_Mins", 0)
                                    current_total = float(str(prev_total)) if prev_total and str(prev_total) != "N/A" else 0.0
                                except:
                                    current_total = 0.0
                                    
                                # Update total paused minutes
                                df.at[target_idx, "Total_Paused_Mins"] = str(round(current_total + mins_paused, 2))
                                
                                # Push the deadline forward
                                old_deadline_raw = row.get("Deadline", "N/A")
                                old_deadline = to_dt(str(old_deadline_raw))
                                
                                if old_deadline:
                                    new_deadline = old_deadline + pause_dur
                                    df.at[target_idx, "Deadline"] = new_deadline.strftime("%Y-%m-%d %I:%M:%S %p")
                            
                            # Reset status to Running
                            df.at[target_idx, "Status"] = "Running"
                            df.at[target_idx, "Pause_Start"] = "N/A"
                            
                            save_tasks(df)
                            st.rerun()

                # --- TAB 2: WORK HISTORY ---
                    with tab2:
                        st.title("📊 My Work History")
                        
                        # Load fresh tasks
                        df_raw = get_tasks()
                        
                        if df_raw.empty:
                            st.info("No records found in the database.")
                        else:
                            # 1. Filter for the logged-in user safely
                            my_history = df_raw[df_raw["Employee"] == st.session_state.user].copy()
                            
                            if my_history.empty:
                                st.info("No records found for your account yet.")
                            else:
                                # SAFETY: Convert Assign_Time to Datetime, ignoring errors (turns bad data into NaT)
                                my_history['Assign_DT'] = pd.to_datetime(my_history['Assign_Time'], errors='coerce')
                                
                                # Remove any rows where the date couldn't be parsed to prevent calculation errors
                                my_history = my_history.dropna(subset=['Assign_DT'])

                                rep_type = st.radio("Select View Period", ["Daily (Today)", "Monthly (30 Days)"], horizontal=True)
                                
                                today_start = get_now_ist().replace(hour=0, minute=0, second=0, microsecond=0)
                                since_date = today_start if "Daily" in rep_type else (get_now_ist() - timedelta(days=30))
                                
                                # Apply the date filter
                                report_df = my_history[my_history["Assign_DT"] >= since_date].copy()
                                
                                # 2. Calculation Function with Type Safety
                                def get_work_hours(r):
                                    # Ensure Start/Submit times are strings before converting
                                    s_str = str(r.get('Start_Time', 'N/A'))
                                    f_str = str(r.get('Submit_Time', 'N/A'))
                                    
                                    s, f = to_dt(s_str), to_dt(f_str)
                                    
                                    if s and f:
                                        total_hrs = (f - s).total_seconds() / 3600
                                        try:
                                            # Convert pause mins to float safely
                                            p_val = r.get("Total_Paused_Mins", 0)
                                            p_mins = float(p_val) if p_val and str(p_val).lower() != 'n/a' else 0.0
                                        except:
                                            p_mins = 0.0
                                        return round(max(0, total_hrs - (p_mins / 60)), 2)
                                    return 0.0

                                if not report_df.empty:
                                    # 3. Apply calculations
                                    report_df['Hours'] = report_df.apply(get_work_hours, axis=1)
                                    
                                    # 4. Numeric Safety for Metrics
                                    # This prevents the "TypeError" when summing columns
                                    p_counts = pd.to_numeric(report_df['Pause_Count'], errors='coerce').fillna(0)
                                    p_mins = pd.to_numeric(report_df['Total_Paused_Mins'], errors='coerce').fillna(0)
                                    
                                    c1, c2, c3 = st.columns(3)
                                    c1.metric("Total Net Work Hours", f"{report_df['Hours'].sum():.2f} hrs")
                                    c2.metric("Total Pauses", f"{int(p_counts.sum())}")
                                    c3.metric("Total Pause Time", f"{p_mins.sum():.2f} mins")
                                    
                                    # 5. Display Columns
                                    cols_to_show = ["Company", "Task", "Assign_Time", "Submit_Time", "Hours", 
                                                    "Pause_Count", "Total_Paused_Mins", "Flag", "Remarks"]
                                    
                                    # Ensure only existing columns are requested
                                    available_cols = [c for c in cols_to_show if c in report_df.columns]
                                    st.dataframe(report_df[available_cols], use_container_width=True)
                                else:
                                    st.info(f"No tasks found for the {rep_type} period.")
