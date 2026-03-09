import streamlit as st
import pandas as pd
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz
import time

# ==========================================
# 1. PAGE CONFIG & GLOBAL SETTINGS
# ==========================================
st.set_page_config(page_title="ZSM Task Control", layout="wide", page_icon="🚩")

# Initialize Supabase
# Ensure these are in your .streamlit/secrets.toml
url: str = st.secrets["supabase"]["url"]
key: str = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

ADMIN_PASSWORD = "admin123" 

# --- BLUEPRINTS ---
TASK_COLS = [
    "Employee", "Company", "Task", "Limit_Mins", "Assign_Time", "Start_Time",
    "Deadline", "Submit_Time", "Time_Variance", "Status", "Flag",
    "Pause_Start", "Scheduled_Date", "Frequency", "Total_Paused_Mins", 
    "Pause_Count", "Remarks"
]
USER_COLS = ["Username", "Password", "Department", "Role"]
COMPANY_COLS = ["Company Name", "Hourly Rate"]

# --- GLOBAL REFRESH (Every 60 Seconds) ---
st_autorefresh(interval=60000, key="datarefresh")

# ==========================================
# 2. LOGIC HELPERS (MOVED UP FOR SCOPE)
# ==========================================

def get_now_ist():
    """Returns current time in IST."""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def to_dt(str_val):
    """Safely handles N/A and multiple string formats including Supabase ISO."""
    if not str_val or str_val in ["N/A", "None", ""]:
        return None
    
    # Try common formats + Supabase ISO format
    str_val = str(str_val).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d %I:%M:%S %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str_val, fmt)
        except ValueError:
            # Handle ISO 8601 automatically if strptime fails
            try:
                return pd.to_datetime(str_val).to_pydatetime()
            except:
                continue
    return None

def render_timer(deadline_str):
    """Calculates and displays the countdown timer."""
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

@st.cache_data(ttl=60) # Reduced TTL for better responsiveness with 80 users
def get_tasks(): 
    """Fetches live tasks from Supabase."""
    try:
        response = supabase.table("tasks").select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            return pd.DataFrame(columns=TASK_COLS)
        
        # Keep original logic: fillna and ensure Remarks exists
        df = df.fillna("N/A")
        if "Remarks" not in df.columns:
            df["Remarks"] = ""
        return df
    except Exception as e:
        st.error(f"DB Fetch Error: {e}")
        return pd.DataFrame(columns=TASK_COLS)

def save_tasks_new_row(new_row_dict):
    """Inserts a single new task into Supabase."""
    try:
        supabase.table("tasks").insert(new_row_dict).execute()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error saving task: {e}")

@st.cache_data(ttl=600)
def get_users(): 
    """Fetches users from Supabase."""
    response = supabase.table("users").select("*").execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=USER_COLS)
    return df.astype(str)

@st.cache_data(ttl=600)
def get_companies():
    """Fetches companies from Supabase."""
    response = supabase.table("companies").select("*").execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=COMPANY_COLS)
    return df

# ==========================================
# 4. LOGIN & ADMIN INTERFACE (PARTIAL)
# ==========================================

if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None

if st.session_state.role is None:
    login_container = st.container()
    with login_container:
        st.title("🚩 ZSM Task Control Center")
        st.markdown("---") 
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👨‍💼 Admin Portal")
            pwd = st.text_input("Admin Access Key", type="password", key="admin_pwd_input")
            if st.button("Login as Admin", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.role = "Admin"
                    st.session_state.user = "Administrator"
                    st.rerun()
                else:
                    st.error("❌ Invalid Access Key")
        
        with col2:
            st.subheader("👥 User Login")
            u_name = st.text_input("Username", key="emp_user_input").strip()
            u_pwd = st.text_input("Password", type="password", key="emp_pwd_input").strip()
            
            if st.button("Login", use_container_width=True):
                users = get_users() 
                if not users.empty:
                    match = users[(users['Username'].str.strip() == u_name) & (users['Password'].str.strip() == u_pwd)]
                    if not match.empty:
                        user_row = match.iloc[0]
                        st.session_state.role = user_row.get('Role', 'Employee')
                        st.session_state.user = user_row['Username']
                        st.success(f"Welcome, {st.session_state.user}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid Credentials")
    st.stop()

# ==========================================
# 3. DASHBOARD UI (ADMIN VIEW)
# ==========================================

# Sidebar Logout (Shared)
st.sidebar.title(f"🚩 {st.session_state.role} Portal")
if st.session_state.user:
    st.sidebar.write(f"Logged in: **{st.session_state.user}**")

if st.sidebar.button("Log Out", use_container_width=True):
    st.session_state.role = None
    st.session_state.user = None
    st.cache_data.clear() 
    st.rerun()

# --- ADMIN VIEW LOGIC ---
if st.session_state.role == "Admin":
    menu = st.sidebar.radio("Main Menu", ["Assign Task", "Live Reports", "User Management", "Companies"])
    
    # --- MENU 1: ASSIGN TASK ---
    if menu == "Assign Task":
        st.title("👨‍💼 Task Assignment")
        
        users_df = get_users()
        comp_db = get_companies()
        
        u_list = users_df.apply(lambda x: f"{x['Username']} ({x.get('Department', 'N/A')})", axis=1).tolist() if not users_df.empty else ["No Users"]
        user_map = dict(zip(u_list, users_df['Username'])) if not users_df.empty else {}
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
                if not desc.strip():
                    st.error("Task description cannot be empty!")
                else:
                    real_name = user_map.get(selected_u, selected_u)
                    
                    # DIRECT INSERT TO SUPABASE (Faster & Safer)
                    new_task = {
                        "Employee": str(real_name), 
                        "Company": str(company), 
                        "Task": str(desc),
                        "Limit_Mins": int(mins), 
                        "Assign_Time": get_now_ist().isoformat(),
                        "Start_Time": "Waiting", 
                        "Deadline": "N/A", 
                        "Submit_Time": "N/A",
                        "Time_Variance": 0.0, 
                        "Status": "Pending", 
                        "Flag": "⚪",
                        "Pause_Start": "N/A", 
                        "Scheduled_Date": s_date.strftime("%Y-%m-%d"),
                        "Frequency": freq, 
                        "Total_Paused_Mins": 0.0, 
                        "Pause_Count": 0, 
                        "Remarks": ""
                    }
                    
                    try:
                        supabase.table("tasks").insert(new_task).execute()
                        st.cache_data.clear()
                        st.success(f"Task assigned to {real_name}!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # --- MENU 2: LIVE REPORTS ---
    elif menu == "Live Reports":
        st.title("📊 Live Monitoring & Reports")
        
        df = get_tasks()
        
        f1, f2, f3 = st.columns(3)
        with f1: target_day = st.date_input("Filter Date", get_now_ist())
        with f2: emp_f = st.multiselect("Filter Employee", df['Employee'].unique() if not df.empty else [])
        with f3: stat_f = st.multiselect("Filter Status", ["Pending", "Running", "Paused", "Finished"])

        if not df.empty:
            # Filter logic
            df = df[df['Scheduled_Date'] == target_day.strftime("%Y-%m-%d")]
            if emp_f: df = df[df['Employee'].isin(emp_f)]
            if stat_f: df = df[df['Status'].isin(stat_f)]

        if not df.empty:
            # Excel Export logic (Same as yours, just using Supabase DF)
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='TaskReport')
            
            st.download_button(label="📥 Download as Excel", data=buffer.getvalue(),
                             file_name=f"ZSM_Report_{target_day}.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             use_container_width=True)

            st.divider()
            for _, row in df.iterrows():
                # Using row['id'] as the unique key for all buttons
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
                            time.sleep(1)
                            st.rerun()
                    
                    if st.session_state.get(f"editing_{row_id}", False):
                        st.markdown("---")
                        new_mins = st.number_input("Adjust Mins", value=int(row['Limit_Mins']), key=f"min_{row_id}")
                        new_stat = st.selectbox("Force Status", ["Pending", "Running", "Paused", "Finished"], 
                                             index=["Pending", "Running", "Paused", "Finished"].index(row['Status']), key=f"stat_{row_id}")
                        
                        if st.button("💾 Save", key=f"save_{row_id}"):
                            supabase.table("tasks").update({
                                "Limit_Mins": int(new_mins),
                                "Status": new_stat
                            }).eq("id", row_id).execute()
                            st.session_state[f"editing_{row_id}"] = False
                            st.cache_data.clear()
                            st.success("Updated!")
                            st.rerun()
                        if st.button("Cancel", key=f"can_{row_id}"):
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
                new_r = st.selectbox("System Role", ["Employee"])
                
                if st.form_submit_button("Create Account"):
                    if new_u and new_p:
                        # Direct Insert (No need to download all users first)
                        try:
                            supabase.table("users").insert({
                                "Username": new_u, "Password": new_p, 
                                "Department": new_d, "Role": new_r
                            }).execute()
                            st.cache_data.clear()
                            st.success(f"Account for {new_u} created!")
                            time.sleep(1); st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e} (Maybe username already exists?)")
                    else:
                        st.error("Fill all fields!")

        # ==========================================
# 3. ADMIN PORTAL (CONTINUED)
# ==========================================

        # 2. VIEW & DELETE USERS
        st.subheader("Current Staff List")
        u_df = get_users()
        
        search_u = st.text_input("🔍 Search User", "")
        display_df = u_df.copy()
        if search_u:
            display_df = display_df[display_df['Username'].str.contains(search_u, case=False)]
        
        st.dataframe(display_df[["Username", "Department", "Role"]], use_container_width=True)

        # Delete Action using Supabase
        to_del_u = st.selectbox("Select User to Remove", ["---"] + display_df["Username"].tolist())
        if st.button("🗑️ Permanent Delete User"):
            if to_del_u != "---":
                try:
                    # Direct delete from Supabase
                    supabase.table("users").delete().eq("Username", to_del_u).execute()
                    st.cache_data.clear()
                    st.warning(f"User {to_del_u} removed.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting user: {e}")

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
                            supabase.table("companies").insert({
                                "Company Name": c_name.strip(), 
                                "Hourly Rate": float(c_rate)
                            }).execute()
                            st.cache_data.clear()
                            st.success(f"Added {c_name}!"); time.sleep(1); st.rerun()
                        except: st.error("Error: Company might already exist.")

            st.subheader("Active Client List")
            st.dataframe(comp_df, use_container_width=True)
            
            to_del_c = st.selectbox("Delete Company", ["---"] + comp_df["Company Name"].tolist())
            if st.button("🗑️ Delete Selected Client"):
                if to_del_c != "---":
                    supabase.table("companies").delete().eq("Company Name", to_del_c).execute()
                    st.cache_data.clear()
                    st.warning(f"Deleted {to_del_c}"); time.sleep(1); st.rerun()

        with tab_b:
            st.subheader("Total Billings (Calculated from Finished Tasks)")
            t_df = get_tasks()
            c_df = get_companies()
            
            # Ensure rates are numeric
            c_df["Hourly Rate"] = pd.to_numeric(c_df["Hourly Rate"], errors='coerce').fillna(0)
            
            finished = t_df[t_df["Status"] == "Finished"].copy()
            if not finished.empty:
                def calc_h(r):
                    s, f = to_dt(r['Start_Time']), to_dt(r['Submit_Time'])
                    if s and f:
                        s, f = s.replace(tzinfo=None), f.replace(tzinfo=None)
                        return (f - s).total_seconds() / 3600
                    return 0.0
                
                finished['Hours'] = finished.apply(calc_h, axis=1)
                report = finished.merge(c_df, left_on="Company", right_on="Company Name", how="left")
                report["Total Billable"] = report["Hours"] * report["Hourly Rate"].fillna(0)
                
                m1, m2 = st.columns(2)
                m1.metric("💰 Total Revenue", f"${report['Total Billable'].sum():,.2f}")
                m2.metric("⏱️ Total Hours", f"{report['Hours'].sum():.2f}")
                
                st.dataframe(report[["Company", "Employee", "Task", "Hours", "Hourly Rate", "Total Billable"]], use_container_width=True)
            else:
                st.info("No billable data yet.")

# ==========================================
# 4. EMPLOYEE VIEW (COLLISION-SAFE)
# ==========================================
elif st.session_state.role == "Employee":
    tab1, tab2 = st.tabs(["🚀 Active Tasks", "📜 My Reports"])
    
    with tab1:
        st.title(f"👷 {st.session_state.user}'s Workspace")
        df = get_tasks()
        today_str = get_now_ist().strftime("%Y-%m-%d")
        
        active_tasks = df[
            (df["Employee"] == st.session_state.user) & 
            (df["Status"] != "Finished") &
            (df["Scheduled_Date"] <= today_str)
        ].copy()
        
        if active_tasks.empty:
            st.info("No active tasks for today. Take a breather! ☕")
        
        for idx, row in active_tasks.iterrows():
            row_id = row['id'] # Use the Primary Key ID
            with st.container(border=True):
                c_top1, c_top2 = st.columns([3, 1])
                c_top1.subheader(f"🏢 {row['Company']}")
                c_top2.write(f"⏱️ **{row['Limit_Mins']}m**")
                st.write(f"**Task:** {row['Task']}")

                # --- START TASK ---
                if row["Status"] == "Pending":
                    if st.button("▶️ START TASK", key=f"start_{row_id}", use_container_width=True, type="primary"):
                        now = get_now_ist().replace(tzinfo=None)
                        mins_val = int(float(str(row["Limit_Mins"])))
                        deadline = now + timedelta(minutes=mins_val)
                        
                        supabase.table("tasks").update({
                            "Start_Time": now.isoformat(),
                            "Deadline": deadline.isoformat(),
                            "Status": "Running"
                        }).eq("id", row_id).execute()
                        
                        st.cache_data.clear()
                        st.rerun()

                # --- RUNNING TASK ---
                elif row["Status"] == "Running":
                    render_timer(row["Deadline"])

                    col_p, col_f = st.columns(2)
                    
                    # Pause Logic
                    if col_p.button("⏸️ PAUSE", key=f"pause_{row_id}", use_container_width=True):
                        now_str = get_now_ist().isoformat()
                        current_p_count = int(row.get("Pause_Count", 0) or 0)
                        
                        supabase.table("tasks").update({
                            "Pause_Start": now_str,
                            "Status": "Paused",
                            "Pause_Count": current_p_count + 1
                        }).eq("id", row_id).execute()
                        
                        st.cache_data.clear()
                        st.rerun()
                    # --- FINISH INITIATION ---
                    if col_f.button("✅ FINISH", key=f"fin_btn_{row_id}", use_container_width=True):
                        st.session_state[f"finish_time_{row_id}"] = get_now_ist().isoformat()
                        st.session_state[f"finish_mode_{row_id}"] = True
                        st.rerun()

                    # --- SUBMISSION FORM ---
                    if st.session_state.get(f"finish_mode_{row_id}", False):
                        with st.form(key=f"form_{row_id}"):
                            frozen_time = st.session_state.get(f"finish_time_{row_id}")
                            st.info(f"Submitting at: {to_dt(frozen_time).strftime('%I:%M %p')}")
                            remarks = st.text_area("What was done?", placeholder="Enter remarks...")
                            
                            if st.form_submit_button("Submit to Admin"):
                                f_dt = to_dt(frozen_time).replace(tzinfo=None)
                                d_dt = to_dt(row["Deadline"]).replace(tzinfo=None)
                                
                                # Variance Math
                                var_sec = int((f_dt - d_dt).total_seconds())
                                abs_v = abs(var_sec)
                                v_str = f"{'+' if var_sec > 0 else '-'}{abs_v//60:02d}:{abs_v%60:02d}"
                                flag = " GREEN" if var_sec <= 0 else "RED"
                                
                                # Atomic Update to Supabase
                                supabase.table("tasks").update({
                                    "Status": "Finished",
                                    "Submit_Time": frozen_time,
                                    "Time_Variance": v_str,
                                    "Flag": flag,
                                    "Remarks": remarks.strip()
                                }).eq("id", row_id).execute()
                                
                                # Handle Recurring logic (if any)
                                handle_recurring_tasks(row)
                                
                                st.cache_data.clear()
                                del st.session_state[f"finish_mode_{row_id}"]
                                st.success("Task Logged Successfully!")
                                time.sleep(1)
                                st.rerun()

                # --- STATUS LOGIC: PAUSED ---
                elif row["Status"] == "Paused":
                    st.warning("☕ Status: On Break")
                    if st.button("▶️ RESUME TASK", key=f"res_{row_id}", use_container_width=True, type="primary"):
                        now = get_now_ist().replace(tzinfo=None)
                        p_start = to_dt(row.get("Pause_Start")).replace(tzinfo=None)
                        pause_dur = now - p_start
                        
                        # Calculate new deadline by adding pause duration
                        old_deadline = to_dt(row.get("Deadline")).replace(tzinfo=None)
                        new_deadline = old_deadline + pause_dur
                        
                        # Calculate total paused mins
                        prev_p = float(row.get("Total_Paused_Mins") or 0.0)
                        new_p_total = prev_p + (pause_dur.total_seconds() / 60)
                        
                        supabase.table("tasks").update({
                            "Total_Paused_Mins": round(new_p_total, 2),
                            "Deadline": new_deadline.isoformat(),
                            "Status": "Running",
                            "Pause_Start": "N/A"
                        }).eq("id", row_id).execute()
                        
                        st.cache_data.clear()
                        st.rerun()

    # --- TAB 2: WORK HISTORY ---
    with tab2:
        st.title("📊 My Work History")
        # Fetch fresh data
        df_history = get_tasks()
        
        if df_history.empty:
            st.info("No records found.")
        else:
            # Filter for current employee
            my_history = df_history[df_history["Employee"] == st.session_state.user].copy()
            
            if my_history.empty:
                st.info("No history found for your account yet.")
            else:
                period = st.radio("View Period", ["Today", "Last 30 Days", "All Time"], horizontal=True)

                # Process dates for filtering
                my_history['Assign_DT'] = pd.to_datetime(my_history['Assign_Time']).dt.tz_localize(None)
                now_naive = get_now_ist().replace(tzinfo=None)
                
                if period == "Today":
                    start_date = now_naive.replace(hour=0, minute=0, second=0)
                elif period == "Last 30 Days":
                    start_date = now_naive - timedelta(days=30)
                else:
                    start_date = datetime(2000, 1, 1)

                report_df = my_history[my_history["Assign_DT"] >= start_date].copy()

                if not report_df.empty:
                    # Net Hours Calculation
                    def get_net_hours(r):
                        s = to_dt(r.get('Start_Time'))
                        f = to_dt(r.get('Submit_Time'))
                        if s and f:
                            s, f = s.replace(tzinfo=None), f.replace(tzinfo=None)
                            gross_hrs = (f - s).total_seconds() / 3600
                            p_hrs = float(r.get("Total_Paused_Mins") or 0.0) / 60
                            return round(max(0, gross_hrs - p_hrs), 2)
                        return 0.0

                    report_df['Net_Hours'] = report_df.apply(get_net_hours, axis=1)
                    
                    # Summary Metrics
                    m1, m2, m3 = st.columns(3)
                    finished_tasks = report_df[report_df["Status"] == "Finished"]
                    
                    m1.metric("Net Work Time", f"{report_df['Net_Hours'].sum():.2f} hrs")
                    m2.metric("Completed Tasks", len(finished_tasks))
                    m3.metric("Avg Variance", finished_tasks['Time_Variance'].iloc[0] if not finished_tasks.empty else "N/A")
                    
                    st.divider()
                    
                    # Clean display
                    display_cols = ["Company", "Task", "Status", "Scheduled_Date", "Net_Hours", "Flag", "Remarks"]
                    st.dataframe(
                        report_df.sort_values("Assign_DT", ascending=False)[display_cols],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Net_Hours": st.column_config.NumberColumn("Hours", format="%.2f"),
                            "Flag": "Performance Flag"
                        }
                    )
                else:
                    st.info("No tasks found for this period.")
