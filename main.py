# ==========================================
# 1. PAGE CONFIG & GLOBAL SETTINGS
# ==========================================
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz
import time

st.set_page_config(page_title="ZSM Task Control", layout="wide", page_icon="🚩")

# Initialize Supabase
url: str = st.secrets["supabase"]["url"]
key: str = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

ADMIN_PASSWORD = "admin123" 

# --- GLOBAL REFRESH (Every 60 Seconds) ---
st_autorefresh(interval=60000, key="datarefresh")

# ==========================================
# 2. LOGIC HELPERS
# ==========================================

def get_now_ist():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def to_dt(str_val):
    """Handles N/A and Supabase ISO formats safely."""
    if not str_val or str_val in ["N/A", "None", "", "Waiting"]:
        return None
    try:
        # Use pandas to automatically detect ISO 8601 or custom strings
        dt = pd.to_datetime(str_val)
        return dt.to_pydatetime()
    except:
        return None

def render_timer(deadline_str):
    """Fixes NameError and displays countdown."""
    try:
        now = get_now_ist().replace(tzinfo=None)
        deadline = to_dt(deadline_str)
        if deadline:
            deadline = deadline.replace(tzinfo=None)
            diff = deadline - now
            if diff.total_seconds() > 0:
                hours, remainder = divmod(int(diff.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                st.error(f"⏳ Time Remaining: {hours:02d}:{minutes:02d}:{seconds:02d}")
            else:
                st.warning("⚠️ Deadline Passed!")
    except Exception:
        st.error("Timer Error")

# ==========================================
# 3. DATABASE HELPERS (SUPABASE)
# ==========================================

@st.cache_data(ttl=30) 
def get_tasks():
    response = supabase.table("tasks").select("*").execute()
    return pd.DataFrame(response.data)

def get_users():
    try:
        response = supabase.table("users").select("*").execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

def get_companies():
    try:
        response = supabase.table("companies").select("*").execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

# ==========================================
# 4. LOGIN INTERFACE
# ==========================================

if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None

if st.session_state.role is None:
    st.title("🚩 ZSM Task Control Center")
    st.markdown("---") 
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👨‍💼 Admin Portal")
        pwd = st.text_input("Admin Access Key", type="password")
        if st.button("Login as Admin", use_container_width=True):
            if pwd == ADMIN_PASSWORD:
                st.session_state.role = "Admin"
                st.session_state.user = "Administrator"
                st.rerun()
            else:
                st.error("❌ Invalid Access Key")
    
    with col2:
        st.subheader("👥 User Login")
        u_name = st.text_input("Username").strip()
        u_pwd = st.text_input("Password", type="password").strip()
        
        if st.button("Login", use_container_width=True):
            users = get_users() 
            if not users.empty:
                # Case-insensitive login check
                match = users[(users['Username'].str.lower() == u_name.lower()) & (users['Password'] == u_pwd)]
                if not match.empty:
                    user_row = match.iloc[0]
                    st.session_state.role = user_row.get('Role', 'Employee')
                    st.session_state.user = user_row['Username']
                    st.success(f"Welcome, {st.session_state.user}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials")
            else:
                st.error("❌ No users found in database.")
    st.stop()

# ==========================================
# 5. ASSIGN TASK MODULE
# ==========================================

st.sidebar.title(f"🚩 {st.session_state.role} Portal")
if st.sidebar.button("Log Out"):
    st.session_state.role = None
    st.session_state.user = None
    st.cache_data.clear() 
    st.rerun()

if st.session_state.role == "Admin":
    menu = st.sidebar.radio("Main Menu", ["Assign Task", "Live Reports", "User Management", "Companies"])
    
    if menu == "Assign Task":
        st.title("👨‍💼 Task Assignment")
        users_df = get_users()
        comp_db = get_companies()
        
        u_list = [f"{u['Username']} ({u.get('Department', 'N/A')})" for _, u in users_df.iterrows()] if not users_df.empty else ["No Users"]
        comp_list = comp_db["Company Name"].tolist() if not comp_db.empty else ["No Companies"]

        with st.form("assignment_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: selected_u = st.selectbox("Assign To", u_list)
            with c2: company = st.selectbox("Company", comp_list)
            with c3: mins = st.number_input("Limit (Mins)", min_value=1, value=15)
            
            c4, c5 = st.columns(2)
            with c4: s_date = st.date_input("Scheduled Date", get_now_ist())
            with c5: freq = st.selectbox("Frequency", ["Once", "Daily", "Weekly", "Monthly"])

            desc = st.text_area("Task Details")
            
            if st.form_submit_button("🚀 ASSIGN TASK"):
                real_name = selected_u.split(" (")[0]
                new_task = {
                    "Employee": real_name, 
                    "Company": company, 
                    "Task": desc.strip(),
                    "Limit_Mins": int(mins), 
                    "Assign_Time": get_now_ist().isoformat(),
                    "Status": "Pending",
                    "Scheduled_Date": s_date.strftime("%Y-%m-%d"),
                    "Frequency": freq,
                    "Total_Paused_Mins": "0.0", # Sending as text for your table
                    "Time_Variance": "00:00",    # Sending as text for your table
                    "Flag": "WHITE"
                }
                supabase.table("tasks").insert(new_task).execute()
                st.cache_data.clear()
                st.success(f"Task assigned to {real_name}!")
                st.rerun()
    
    
    # --- MENU 2: LIVE REPORTS ---
    elif menu == "Live Reports":
        st.title("📊 Live Monitoring & Reports")
        
        df = get_tasks()
        
        f1, f2, f3 = st.columns(3)
        with f1: target_day = st.date_input("Filter Date", get_now_ist())
        # Safety check: if df is empty, unique() will fail
        emp_list = df['Employee'].unique().tolist() if not df.empty else []
        with f2: emp_f = st.multiselect("Filter Employee", emp_list)
        with f3: stat_f = st.multiselect("Filter Status", ["Pending", "Running", "Paused", "Finished"])

        if not df.empty:
            # Apply Filters
            df = df[df['Scheduled_Date'] == target_day.strftime("%Y-%m-%d")]
            if emp_f: df = df[df['Employee'].isin(emp_f)]
            if stat_f: df = df[df['Status'].isin(stat_f)]

            # Excel Export logic
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='TaskReport')
            
            st.download_button(label="📥 Download as Excel", data=buffer.getvalue(),
                             file_name=f"ZSM_Report_{target_day}.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             use_container_width=True)

            st.divider()
            
            if df.empty:
                st.info("No tasks found for the selected filters.")
            else:
                for _, row in df.iterrows():
                    row_id = row['id'] 
                    with st.expander(f"{row['Status']} | {row['Employee']} - {row['Task'][:30]}..."):
                        c1, c2, c3 = st.columns([3, 2, 2])
                        with c1:
                            st.write(f"**Task:** {row['Task']}")
                            st.caption(f"Company: {row['Company']} | Assigned: {row['Assign_Time']}")
                        with c2:
                            st.write(f"**Status:** {row['Status']}")
                            st.write(f"**Goal:** {row['Limit_Mins']} mins")
                        
                        with c3:
                            if st.button("✏️ Edit", key=f"edit_{row_id}"):
                                st.session_state[f"editing_{row_id}"] = True
                            
                            if st.button("🗑️ Delete", key=f"del_{row_id}"):
                                supabase.table("tasks").delete().eq("id", row_id).execute()
                                st.cache_data.clear()
                                st.toast("Task Deleted")
                                time.sleep(0.5)
                                st.rerun()
                        
                        # Inline Editing Logic
                        if st.session_state.get(f"editing_{row_id}", False):
                            st.markdown("---")
                            new_mins = st.number_input("Adjust Mins", value=int(row['Limit_Mins']), key=f"min_{row_id}")
                            current_stat = row['Status'] if row['Status'] in ["Pending", "Running", "Paused", "Finished"] else "Pending"
                            new_stat = st.selectbox("Force Status", ["Pending", "Running", "Paused", "Finished"], 
                                                 index=["Pending", "Running", "Paused", "Finished"].index(current_stat), key=f"stat_{row_id}")
                            
                            se1, se2 = st.columns(2)
                            with se1:
                                if st.button("💾 Save Changes", key=f"save_{row_id}", use_container_width=True):
                                    supabase.table("tasks").update({
                                        "Limit_Mins": int(new_mins),
                                        "Status": new_stat
                                    }).eq("id", row_id).execute()
                                    st.session_state[f"editing_{row_id}"] = False
                                    st.cache_data.clear()
                                    st.success("Updated!")
                                    st.rerun()
                            with se2:
                                if st.button("Cancel", key=f"can_{row_id}", use_container_width=True):
                                    st.session_state[f"editing_{row_id}"] = False
                                    st.rerun()

    # --- MENU 3: USER MANAGEMENT ---
    elif menu == "User Management":
        st.title("👥 User Management")
        
        with st.expander("➕ Add New User"):
            with st.form("add_user_form", clear_on_submit=True):
                new_u = st.text_input("Username").strip()
                new_p = st.text_input("Password", type="password").strip()
                new_d = st.selectbox("Department", ["Book Keeping", "Notice", "TAX", "Payroll", "IT", "CRM", "Accountant"])
                new_r = st.selectbox("System Role", ["Employee", "Admin"])
                
                if st.form_submit_button("Create Account"):
                    if new_u and new_p:
                        try:
                            supabase.table("users").insert({
                                "Username": new_u, 
                                "Password": new_p, 
                                "Department": new_d, 
                                "Role": new_r
                            }).execute()
                            st.cache_data.clear()
                            st.success(f"Account for {new_u} created!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error("Error: This username might already exist.")
                    else:
                        st.error("Please fill in both Username and Password.")

        # Display Current Staff
        st.subheader("Current Staff List")
        users_df = get_users()
        if not users_df.empty:
            st.dataframe(users_df[["Username", "Department", "Role"]], use_container_width=True)
            
            # Simple Delete User Option
            user_to_del = st.selectbox("Select User to Remove", ["Select..."] + users_df['Username'].tolist())
            if st.button("🗑️ Delete User") and user_to_del != "Select...":
                supabase.table("users").delete().eq("username", user_to_del).execute()
                st.cache_data.clear()
                st.warning(f"User {user_to_del} removed.")
                time.sleep(1)
                st.rerun()

        # ==========================================
# 3. ADMIN PORTAL (CONTINUED)
# ==========================================

    # --- MENU 4: COMPANY & REVENUE ---
    elif menu == "Companies":
        st.title("🏢 Company & Revenue Management")
        tab_a, tab_b = st.tabs(["Add/Edit Companies", "💰 Revenue Report"])
        
        with tab_a:
            comp_df = get_companies()
            with st.expander("➕ Add New Client/Company"):
                c_name = st.text_input("Company Name")
                c_rate = st.number_input("Hourly Billing Rate ($)", min_value=0.0, step=1.0)
                if st.button("Save Company"):
                    if c_name:
                        try:
                            # Ensuring numeric rate is cast to float for DB
                            supabase.table("companies").insert({
                                "Company Name": c_name.strip(), 
                                "Hourly Rate": float(c_rate)
                            }).execute()
                            st.cache_data.clear()
                            st.success(f"Added {c_name}!")
                            time.sleep(0.5)
                            st.rerun()
                        except: 
                            st.error("Error: Company might already exist.")

            st.subheader("Active Client List")
            if not comp_df.empty:
                st.dataframe(comp_df[["Company Name", "Hourly Rate"]], use_container_width=True)
                to_del_c = st.selectbox("Delete Company", ["---"] + comp_df["Company Name"].tolist())
                if st.button("🗑️ Delete Selected Client"):
                    if to_del_c != "---":
                        supabase.table("companies").delete().eq("Company Name", to_del_c).execute()
                        st.cache_data.clear()
                        st.warning(f"Deleted {to_del_c}")
                        time.sleep(0.5)
                        st.rerun()
            else:
                st.info("No companies registered yet.")

        with tab_b:
            st.subheader("Total Billings (Finished tasks)")
            t_df = get_tasks()
            c_df = get_companies()
            
            if not t_df.empty and not c_df.empty:
                # Filter to only finished tasks for revenue
                finished = t_df[t_df["Status"] == "Finished"].copy()
                
                if not finished.empty:
                    # Clean up rates
                    c_df["Hourly Rate"] = pd.to_numeric(c_df["Hourly Rate"], errors='coerce').fillna(0)
                    
                    def calc_hours(r):
                        start, end = to_dt(r['Start_Time']), to_dt(r['Submit_Time'])
                        if start and end:
                            # Remove timezone info for subtraction
                            diff = end.replace(tzinfo=None) - start.replace(tzinfo=None)
                            return max(0, diff.total_seconds() / 3600)
                        return 0.0
                    
                    finished['Hours'] = finished.apply(calc_hours, axis=1)
                    report = finished.merge(c_df, left_on="Company", right_on="Company Name", how="left")
                    report["Total Billable"] = report["Hours"] * report["Hourly Rate"].fillna(0)
                    
                    m1, m2 = st.columns(2)
                    m1.metric("💰 Total Revenue", f"${report['Total Billable'].sum():,.2f}")
                    m2.metric("⏱️ Total Hours", f"{report['Hours'].sum():.2f}")
                    
                    st.dataframe(report[["Company", "Employee", "Task", "Hours", "Total Billable"]], use_container_width=True)
                else:
                    st.info("No finished tasks found to generate revenue report.")

# ==========================================
# 4. EMPLOYEE VIEW (COLLISION-SAFE)
# ==========================================
elif st.session_state.role == "Employee":
    tab1, tab2 = st.tabs(["🚀 Active Tasks", "📜 My Reports"])
    
    with tab1:
        st.title(f"👷 {st.session_state.user}'s Workspace")
        df = get_tasks()
        now_ist = get_now_ist()
        today_str = now_ist.strftime("%Y-%m-%d")
        
        # Filter for current employee's tasks that are not finished
        active_tasks = df[
            (df["Employee"] == st.session_state.user) & 
            (df["Status"] != "Finished") &
            (df["Scheduled_Date"] <= today_str)
        ].copy()
        
        if active_tasks.empty:
            st.info("No active tasks for today. Take a breather! ☕")
        
        for _, row in active_tasks.iterrows():
            row_id = row['id']
            with st.container(border=True):
                c_top1, c_top2 = st.columns([3, 1])
                c_top1.subheader(f"🏢 {row['Company']}")
                c_top2.write(f"⏱️ **Limit: {row['Limit_Mins']}m**")
                st.write(f"**Task Details:** {row['Task']}")

                # --- STATE: PENDING ---
                if row["Status"] == "Pending":
                    if st.button("▶️ START TASK", key=f"start_{row_id}", use_container_width=True, type="primary"):
                        start_now = get_now_ist().replace(tzinfo=None)
                        # Safely handle numeric limit
                        try:
                            l_mins = int(row["Limit_Mins"])
                        except:
                            l_mins = 15
                        
                        deadline = start_now + timedelta(minutes=l_mins)
                        
                        supabase.table("tasks").update({
                            "Start_Time": start_now.isoformat(),
                            "Deadline": deadline.isoformat(),
                            "Status": "Running"
                        }).eq("id", row_id).execute()
                        
                        st.cache_data.clear()
                        st.rerun()

                # --- STATE: RUNNING ---
                elif row["Status"] == "Running":
                    render_timer(row["Deadline"])

                    col_p, col_f = st.columns(2)
                    
                    if col_p.button("⏸️ PAUSE", key=f"pause_{row_id}", use_container_width=True):
                        p_start = get_now_ist().isoformat()
                        p_count = int(row.get("Pause_Count", 0) or 0)
                        
                        supabase.table("tasks").update({
                            "Pause_Start": p_start,
                            "Status": "Paused",
                            "Pause_Count": p_count + 1
                        }).eq("id", row_id).execute()
                        
                        st.cache_data.clear()
                        st.rerun()

                    if col_f.button("✅ FINISH", key=f"fin_init_{row_id}", use_container_width=True):
                        st.session_state[f"finish_mode_{row_id}"] = True
                        st.rerun()

                    # --- SUBMISSION FORM ---
            if st.session_state.get(f"finish_mode_{row_id}", False):
                with st.form(key=f"form_{row_id}"):
                    frozen_time = st.session_state.get(f"finish_time_{row_id}")
                    # Safety check for display
                    f_dt_display = to_dt(frozen_time)
                    display_str = f_dt_display.strftime('%I:%M %p') if f_dt_display else "Now"
                    st.info(f"Submitting at: {display_str}")
                    
                    remarks = st.text_area("What was done?", placeholder="Enter work summary...")
                    
                    if st.form_submit_button("Submit to Admin"):
                        f_dt = to_dt(frozen_time).replace(tzinfo=None)
                        d_dt = to_dt(row["Deadline"]).replace(tzinfo=None)
                        
                        # Variance Math (Handled in Python)
                        var_sec = int((f_dt - d_dt).total_seconds())
                        abs_v = abs(var_sec)
                        # v_str is a text string like "-05:30" or "+02:15"
                        v_str = f"{'+' if var_sec > 0 else '-'}{abs_v//3600:02d}:{(abs_v%3600)//60:02d}"
                        
                        # Use plain text flags to avoid encoding errors (ðŸŸ¢)
                        flag = "GREEN" if var_sec <= 0 else "RED"
                        
                        # Atomic Update to Supabase (All values sent as strings/ints)
                        supabase.table("tasks").update({
                            "Status": "Finished",
                            "Submit_Time": f_dt.isoformat(),
                            "Time_Variance": v_str,
                            "Flag": flag,
                            "Remarks": remarks.strip()
                        }).eq("id", row_id).execute()
                        
                        # Recurring logic call
                        if row.get("Frequency") != "Once":
                            handle_recurring_tasks(row)
                        
                        st.cache_data.clear()
                        if f"finish_mode_{row_id}" in st.session_state:
                            del st.session_state[f"finish_mode_{row_id}"]
                        st.success("Task Logged Successfully!")
                        time.sleep(1)
                        st.rerun()

            # --- STATUS LOGIC: PAUSED ---
            elif row["Status"] == "Paused":
                st.warning("☕ Status: On Break")
                if st.button("▶️ RESUME TASK", key=f"res_{row_id}", use_container_width=True, type="primary"):
                    now = get_now_ist().replace(tzinfo=None)
                    p_start = to_dt(row.get("Pause_Start"))
                    
                    if p_start:
                        p_start = p_start.replace(tzinfo=None)
                        pause_dur = now - p_start
                        
                        # Calculate new deadline
                        old_deadline = to_dt(row.get("Deadline")).replace(tzinfo=None)
                        new_deadline = old_deadline + pause_dur
                        
                        # Calculate total paused mins (saved as text)
                        prev_p = float(str(row.get("Total_Paused_Mins") or 0.0))
                        new_p_total = prev_p + (pause_dur.total_seconds() / 60)
                        
                        supabase.table("tasks").update({
                            "Total_Paused_Mins": str(round(new_p_total, 2)),
                            "Deadline": new_deadline.isoformat(),
                            "Status": "Running",
                            "Pause_Start": "N/A"
                        }).eq("id", row_id).execute()
                        
                        st.cache_data.clear()
                        st.rerun()

    # --- TAB 2: WORK HISTORY ---
    with tab2:
        st.title("📊 My Work History")
        df_history = get_tasks()
        
        if not df_history.empty:
            my_history = df_history[df_history["Employee"] == st.session_state.user].copy()
            
            if not my_history.empty:
                period = st.radio("View Period", ["Today", "All Time"], horizontal=True)
                now_ist = get_now_ist().replace(tzinfo=None)
                
                if period == "Today":
                    today_str = now_ist.strftime("%Y-%m-%d")
                    report_df = my_history[my_history["Scheduled_Date"] == today_str].copy()
                else:
                    report_df = my_history.copy()

                if not report_df.empty:
                    # Summary Metrics
                    finished_tasks = report_df[report_df["Status"] == "Finished"]
                    m1, m2 = st.columns(2)
                    m1.metric("Tasks Completed", len(finished_tasks))
                    m2.metric("Latest Variance", finished_tasks['Time_Variance'].iloc[0] if not finished_tasks.empty else "N/A")
                    
                    st.divider()
                    
                    # Performance Dataframe
                    st.dataframe(
                        report_df.sort_values("id", ascending=False)[["Company", "Task", "Status", "Time_Variance", "Flag", "Remarks"]],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No records for this period.")

# ==========================================
# 5. RECURRING TASK LOGIC (BOTTOM OF SCRIPT)
# ==========================================

def handle_recurring_tasks(old_row):
    """Creates the next instance of a recurring task."""
    freq = old_row.get("Frequency")
    if freq == "Once": return

    current_date = datetime.strptime(old_row["Scheduled_Date"], "%Y-%m-%d")
    
    if freq == "Daily":
        next_date = current_date + timedelta(days=1)
    elif freq == "Weekly":
        next_date = current_date + timedelta(weeks=1)
    elif freq == "Monthly":
        next_date = current_date + timedelta(days=30)
    else:
        return

    # Prepare new task object
    next_task = {
        "Employee": old_row["Employee"],
        "Company": old_row["Company"],
        "Task": old_row["Task"],
        "Limit_Mins": old_row["Limit_Mins"],
        "Assign_Time": get_now_ist().isoformat(),
        "Status": "Pending",
        "Scheduled_Date": next_date.strftime("%Y-%m-%d"),
        "Frequency": freq,
        "Total_Paused_Mins": "0.0",
        "Time_Variance": "00:00",
        "Flag": "WHITE"
    }
    
    try:
        supabase.table("tasks").insert(next_task).execute()
    except Exception as e:
        print(f"Recurring error: {e}")
