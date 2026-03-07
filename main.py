import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz
import time
def render_timer(deadline_str):
    """Calculates and displays the countdown timer."""
    try:
        now = get_now_ist().replace(tzinfo=None)
        deadline = to_dt(deadline_str).replace(tzinfo=None)
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
# 1. PAGE CONFIG & GLOBAL SETTINGS
# ==========================================
# MUST be the first Streamlit command
st.set_page_config(page_title="ZSM Task Control", layout="wide", page_icon="🚩")

ADMIN_PASSWORD = "admin123" 

# --- BLUEPRINTS (Column Definitions) ---
TASK_COLS = [
    "Employee", "Company", "Task", "Limit_Mins", "Assign_Time", "Start_Time",
    "Deadline", "Submit_Time", "Time_Variance", "Status", "Flag",
    "Pause_Start", "Scheduled_Date", "Frequency", "Total_Paused_Mins", 
    "Pause_Count", "Remarks"
]
USER_COLS = ["Username", "Password", "Department", "Role"]
COMPANY_COLS = ["Company Name", "Hourly Rate"]

# Create the connection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GLOBAL REFRESH (Every 60 Seconds) ---
st_autorefresh(interval=60000, key="datarefresh")

# ==========================================
# 2. DATABASE HELPERS (CACHED FOR 80 USERS)
# ==========================================

@st.cache_data(ttl=600) # Cache for 10 minutes
def get_tasks(): 
    """Fetches live tasks from Google Sheets."""
    df = conn.read(worksheet="Tasks", ttl=0)
    if df.empty:
        return pd.DataFrame(columns=TASK_COLS)
    
    df = df.fillna("N/A").astype(str)
    # Ensure timezone-naive for safety in calculations
    df['Assign_DT'] = pd.to_datetime(df['Assign_Time'], errors='coerce').dt.tz_localize(None)
    
    if "Remarks" not in df.columns:
        df["Remarks"] = ""
    return df

def save_tasks(df): 
    """Saves tasks and clears cache so users see updates immediately."""
    if 'Assign_DT' in df.columns: 
        df = df.drop(columns=['Assign_DT'])
    conn.update(worksheet="Tasks", data=df)
    st.cache_data.clear() 

@st.cache_data(ttl=600)
def get_users(): 
    """Fetches users with caching."""
    df = conn.read(worksheet="Users", ttl=0)
    if df.empty:
        return pd.DataFrame(columns=USER_COLS)
    return df.astype(str)

def save_users(df): 
    conn.update(worksheet="Users", data=df)
    st.cache_data.clear()

@st.cache_data(ttl=600)
def get_companies():
    """Fetches companies with caching."""
    df = conn.read(worksheet="Companies", ttl=0)
    if df.empty:
        return pd.DataFrame(columns=COMPANY_COLS)
    return df

def save_companies(df):
    conn.update(worksheet="Companies", data=df)
    st.cache_data.clear()

# ==========================================
# 3. LOGIC HELPERS
# ==========================================

def get_now_ist():
    """Returns current time in IST."""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def to_dt(str_val):
    """Safely handles N/A, None, and multiple string formats."""
    if not str_val or str_val in ["N/A", "None", ""]:
        return None
    
    str_val = str(str_val).strip()
    for fmt in ("%Y-%m-%d %I:%M:%S %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str_val, fmt)
        except ValueError:
            continue
    return None

def handle_recurring_tasks(finished_row):
    """Creates a new task based on frequency logic."""
    if str(finished_row.get('Frequency', 'Once')) == "Once":
        return
    
    try:
        sched_str = str(finished_row['Scheduled_Date']).strip()
        current_sched = datetime.strptime(sched_str, "%Y-%m-%d")
    except:
        current_sched = get_now_ist().replace(tzinfo=None)

    freq = finished_row['Frequency']
    if freq == "Daily":
        next_date = current_sched + timedelta(days=1)
    elif freq == "Weekly":
        next_date = current_sched + timedelta(weeks=1)
    elif freq == "Semi-Monthly":
        next_date = current_sched + timedelta(days=15)
    elif freq == "Monthly":
        next_date = current_sched + timedelta(days=30)
    else:
        return

    now_naive = get_now_ist().replace(tzinfo=None)
    
    new_task_data = {
        "Employee": str(finished_row['Employee']),
        "Company": str(finished_row['Company']),
        "Task": str(finished_row['Task']),
        "Limit_Mins": str(finished_row['Limit_Mins']),
        "Assign_Time": now_naive.strftime("%Y-%m-%d %I:%M:%S %p"),
        "Start_Time": "Waiting",
        "Deadline": "N/A",
        "Submit_Time": "N/A",
        "Time_Variance": "N/A",
        "Status": "Pending",
        "Flag": "⚪",
        "Pause_Start": "N/A",
        "Scheduled_Date": next_date.strftime("%Y-%m-%d"),
        "Frequency": str(freq),
        "Total_Paused_Mins": "0",
        "Pause_Count": "0",
        "Remarks": ""
    }
    
    df = get_tasks()
    new_row_df = pd.DataFrame([new_task_data])
    updated_df = pd.concat([df, new_row_df], ignore_index=True)
    save_tasks(updated_df)

# ==========================================
# 4. LOGIN INTERFACE
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
            st.subheader("👥 Employee/User Login")
            u_name = st.text_input("Username", key="emp_user_input").strip()
            u_pwd = st.text_input("Password", type="password", key="emp_pwd_input").strip()
            
            if st.button("Login", use_container_width=True):
                users = get_users() 
                
                if not users.empty:
                    users['U_Clean'] = users['Username'].astype(str).str.strip()
                    users['P_Clean'] = users['Password'].astype(str).str.strip()
                    
                    match = users[(users['U_Clean'] == u_name) & (users['P_Clean'] == u_pwd)]
                    
                    if not match.empty:
                        user_row = match.iloc[0]
                        st.session_state.role = user_row.get('Role', 'Employee')
                        st.session_state.user = user_row['Username']
                        st.success(f"Welcome, {st.session_state.user}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid Username or Password")
                else:
                    st.error("⚠️ User database empty. Contact Admin.")
                    
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
                    all_tasks = get_tasks() 
                    
                    new_row = {
                        "Employee": str(real_name), "Company": str(company), "Task": str(desc),
                        "Limit_Mins": str(mins), "Assign_Time": get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p"),
                        "Start_Time": "Waiting", "Deadline": "N/A", "Submit_Time": "N/A",
                        "Time_Variance": "N/A", "Status": "Pending", "Flag": "⚪",
                        "Pause_Start": "N/A", "Scheduled_Date": s_date.strftime("%Y-%m-%d"),
                        "Frequency": freq, "Total_Paused_Mins": "0", "Pause_Count": "0", "Remarks": ""
                    }
                    
                    updated_df = pd.concat([all_tasks, pd.DataFrame([new_row])], ignore_index=True)
                    save_tasks(updated_df)
                    st.success(f"Task assigned to {real_name}!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

    # --- MENU 2: LIVE REPORTS & OVERRIDES ---
    elif menu == "Live Reports":
        st.title("📊 Live Monitoring & Reports")
        
        # 1. Fetch Data
        df = get_tasks()
        
        # 2. Filters
        f1, f2, f3 = st.columns(3)
        with f1: target_day = st.date_input("Filter Date", get_now_ist())
        with f2: emp_f = st.multiselect("Filter Employee", df['Employee'].unique() if not df.empty else [])
        with f3: stat_f = st.multiselect("Filter Status", ["Pending", "Running", "Paused", "Finished"])

        # 3. Apply Filters
        if not df.empty:
            df = df[df['Scheduled_Date'] == target_day.strftime("%Y-%m-%d")]
            if emp_f: df = df[df['Employee'].isin(emp_f)]
            if stat_f: df = df[df['Status'].isin(stat_f)]

        # 4. Export Section
        if not df.empty:
            import io
            buffer = io.BytesIO()
            export_df = df.copy()
            # Clean internal helper columns
            if 'Assign_DT' in export_df.columns: export_df.drop(columns=['Assign_DT'], inplace=True)
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='TaskReport')
            
            st.download_button(
                label="📥 Download as Excel",
                data=buffer.getvalue(),
                file_name=f"ZSM_Report_{target_day}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        # 5. Task Display & Override Table
        if df.empty:
            st.info("No tasks found for selected filters.")
        else:
            st.divider()
            for idx, row in df.iterrows():
                with st.expander(f"{row['Status']} | {row['Employee']} - {row['Task'][:30]}..."):
                    c1, c2, c3 = st.columns([3, 2, 2])
                    
                    with c1:
                        st.write(f"**Task:** {row['Task']}")
                        st.caption(f"Company: {row['Company']} | Assigned: {row['Assign_Time']}")
                    
                    with c2:
                        st.write(f"**Status:** {row['Status']}")
                        st.write(f"**Goal:** {row['Limit_Mins']} mins")
                    
                    with c3:
                        # EDIT LOGIC
                        if st.button("✏️ Edit Task", key=f"edit_{idx}"):
                            st.session_state[f"editing_{idx}"] = True
                        
                        # DELETE LOGIC
                        if st.button("🗑️ Delete", key=f"del_{idx}"):
                            full_db = get_tasks()
                            # Use Employee + Assign_Time as a unique ID
                            mask = (full_db['Employee'] == row['Employee']) & (full_db['Assign_Time'] == row['Assign_Time'])
                            full_db = full_db[~mask]
                            save_tasks(full_db)
                            st.toast("Task Deleted")
                            time.sleep(1)
                            st.rerun()
                    
                    # Edit Form
                    if st.session_state.get(f"editing_{idx}", False):
                        st.markdown("---")
                        new_mins = st.number_input("Adjust Mins", value=int(row['Limit_Mins']), key=f"min_{idx}")
                        new_stat = st.selectbox("Force Status", ["Pending", "Running", "Paused", "Finished"], 
                                            index=["Pending", "Running", "Paused", "Finished"].index(row['Status']), key=f"stat_{idx}")
                        
                        if st.button("💾 Save Changes", key=f"save_{idx}"):
                            full_db = get_tasks()
                            match = full_db[(full_db['Employee'] == row['Employee']) & (full_db['Assign_Time'] == row['Assign_Time'])].index
                            if not match.empty:
                                target = match[0]
                                full_db.at[target, 'Limit_Mins'] = str(new_mins)
                                full_db.at[target, 'Status'] = new_stat
                                save_tasks(full_db)
                                st.session_state[f"editing_{idx}"] = False
                                st.success("Updated!")
                                st.rerun()
                        if st.button("Cancel", key=f"can_{idx}"):
                            st.session_state[f"editing_{idx}"] = False
                            st.rerun()
    
    
    # --- MENU 3: USER MANAGEMENT (SAFE FOR 80 USERS) ---
    elif menu == "User Management":
        st.title("👥 User Management")
        
        # 1. ADD NEW USER FORM
        with st.expander("➕ Add New User / Employee"):
            with st.form("add_user_form", clear_on_submit=True):
                new_u = st.text_input("Username").strip()
                new_p = st.text_input("Password", type="password").strip()
                new_d = st.selectbox("Department", ["Operations", "Sales", "IT", "HR", "Finance", "Management"])
                new_r = st.selectbox("System Role", ["Employee", "Admin"])
                
                if st.form_submit_button("Create Account"):
                    if new_u and new_p:
                        u_df = get_users() # Uses 10-min cache
                        if new_u in u_df['Username'].values:
                            st.error("Username already exists!")
                        else:
                            new_row = pd.DataFrame([{
                                "Username": new_u, 
                                "Password": new_p, 
                                "Department": new_d, 
                                "Role": new_r
                            }])
                            save_users(pd.concat([u_df, new_row], ignore_index=True)) # Clears cache
                            st.success(f"Account for {new_u} created!")
                            time.sleep(1); st.rerun()
                    else:
                        st.error("Fill all fields!")

        # 2. VIEW & DELETE USERS
        st.subheader("Current Staff List")
        u_df = get_users()
        
        # Display as a clean table with a search bar
        search_u = st.text_input("🔍 Search User", "")
        display_df = u_df.copy()
        if search_u:
            display_df = display_df[display_df['Username'].str.contains(search_u, case=False)]
        
        st.dataframe(display_df[["Username", "Department", "Role"]], use_container_width=True)

        # Delete Action
        to_del_u = st.selectbox("Select User to Remove", ["---"] + display_df["Username"].tolist())
        if st.button("🗑️ Permanent Delete User"):
            if to_del_u != "---":
                fresh_u = get_users()
                fresh_u = fresh_u[fresh_u["Username"] != to_del_u]
                save_users(fresh_u)
                st.warning(f"User {to_del_u} removed."); time.sleep(1); st.rerun()

    # --- MENU 4: COMPANY & REVENUE (OPTIMIZED) ---
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
                        fresh_comp = get_companies()
                        if c_name.strip() not in fresh_comp["Company Name"].values:
                            new_row = pd.DataFrame([{"Company Name": c_name.strip(), "Hourly Rate": str(c_rate)}])
                            save_companies(pd.concat([fresh_comp, new_row], ignore_index=True))
                            st.success(f"Added {c_name}!"); time.sleep(1); st.rerun()
                        else: st.error("Company exists!")

            st.subheader("Active Client List")
            st.dataframe(comp_df, use_container_width=True)
            
            to_del_c = st.selectbox("Delete Company", ["---"] + comp_df["Company Name"].tolist())
            if st.button("🗑️ Delete Selected Client"):
                if to_del_c != "---":
                    fresh_comp = get_companies()
                    fresh_comp = fresh_comp[fresh_comp["Company Name"] != to_del_c]
                    save_companies(fresh_comp)
                    st.warning(f"Deleted {to_del_c}"); time.sleep(1); st.rerun()

        with tab_b:
            st.subheader("Total Billings (Calculated from Finished Tasks)")
            t_df = get_tasks()
            c_df = get_companies()
            
            # Convert rates to numbers safely
            c_df["Hourly Rate"] = pd.to_numeric(c_df["Hourly Rate"], errors='coerce').fillna(0)
            
            finished = t_df[t_df["Status"] == "Finished"].copy()
            if not finished.empty:
                # Timezone-safe hour calculation
                def calc_h(r):
                    s, f = to_dt(r['Start_Time']), to_dt(r['Submit_Time'])
                    if s and f:
                        # Ensure both are naive for subtraction
                        s, f = s.replace(tzinfo=None), f.replace(tzinfo=None)
                        return (f - s).total_seconds() / 3600
                    return 0.0
                
                finished['Hours'] = finished.apply(calc_h, axis=1)
                report = finished.merge(c_df, left_on="Company", right_on="Company Name", how="left")
                report["Total Billable"] = report["Hours"] * report["Hourly Rate"]
                
                # Metrics Row
                m1, m2 = st.columns(2)
                m1.metric("💰 Total Revenue", f"${report['Total Billable'].sum():,.2f}")
                m2.metric("⏱️ Total Hours", f"{report['Hours'].sum():.2f}")
                
                st.dataframe(report[["Company", "Employee", "Task", "Hours", "Hourly Rate", "Total Billable"]], use_container_width=True)
            else:
                st.info("No billable data yet. Tasks must be marked as 'Finished' to show here.")                            

    # ==========================================
# 4. EMPLOYEE VIEW (SCALABLE & COLLISION-SAFE)
# ==========================================
elif st.session_state.role == "Employee":
    # Define tabs at the top level of the Employee role
    tab1, tab2 = st.tabs(["🚀 Active Tasks", "📜 My Reports"])
    
    # --- TAB 1: ACTIVE TASKS ---
    with tab1:
        st.title(f"👷 {st.session_state.user}'s Workspace")
        
        # 1. Fetch data
        df = get_tasks()
        
        # 2. Filter: Only this user, not finished, and due today or earlier
        today_str = get_now_ist().strftime("%Y-%m-%d")
        active_tasks = df[
            (df["Employee"] == st.session_state.user) & 
            (df["Status"] != "Finished") &
            (df["Scheduled_Date"] <= today_str)
        ].copy()
        
        if active_tasks.empty:
            st.info("No active tasks for today. Take a breather! ☕")
        
        for idx, row in active_tasks.iterrows():
            with st.container(border=True):
                # UI Header
                c_top1, c_top2 = st.columns([3, 1])
                c_top1.subheader(f"🏢 {row['Company']}")
                c_top2.write(f"⏱️ **{row['Limit_Mins']}m**")
                st.write(f"**Task:** {row['Task']}")

                # --- STATUS LOGIC: PENDING ---
                if row["Status"] == "Pending":
                    if st.button("▶️ START TASK", key=f"start_{idx}", use_container_width=True, type="primary"):
                        master_df = get_tasks()
                        m_idx = master_df[(master_df['Employee'] == row['Employee']) & (master_df['Assign_Time'] == row['Assign_Time'])].index
                        
                        if not m_idx.empty:
                            now = get_now_ist().replace(tzinfo=None)
                            mins_val = int(float(str(row["Limit_Mins"])))
                            deadline = now + timedelta(minutes=mins_val)
                            
                            master_df.at[m_idx[0], "Start_Time"] = now.strftime("%Y-%m-%d %I:%M:%S %p")
                            master_df.at[m_idx[0], "Deadline"] = deadline.strftime("%Y-%m-%d %I:%M:%S %p")
                            master_df.at[m_idx[0], "Status"] = "Running"
                            
                            save_tasks(master_df)
                            st.rerun()

                # --- STATUS LOGIC: RUNNING ---
                elif row["Status"] == "Running":
                    # LIVE TIMER
                    if not st.session_state.get(f"finish_mode_{idx}", False):
                        render_timer(row["Deadline"])
                    else:
                        st.warning("⚠️ Timer paused for submission.")

                    col_p, col_f = st.columns(2)
                    
                    # Pause Logic
                    if col_p.button("⏸️ PAUSE", key=f"pause_{idx}", use_container_width=True):
                        master_df = get_tasks()
                        m_idx = master_df[(master_df['Employee'] == row['Employee']) & (master_df['Assign_Time'] == row['Assign_Time'])].index
                        if not m_idx.empty:
                            now_str = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                            master_df.at[m_idx[0], "Pause_Start"] = now_str
                            master_df.at[m_idx[0], "Status"] = "Paused"
                            
                            try:
                                p_count = int(float(str(row.get("Pause_Count", 0))))
                            except:
                                p_count = 0
                            master_df.at[m_idx[0], "Pause_Count"] = str(p_count + 1)
                            
                            save_tasks(master_df)
                            st.rerun()

                    # Finish Initiation
                    if col_f.button("✅ FINISH", key=f"fin_btn_{idx}", use_container_width=True):
                        st.session_state[f"finish_time_{idx}"] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                        st.session_state[f"finish_mode_{idx}"] = True
                        st.rerun()

                    # Submission Form
                    if st.session_state.get(f"finish_mode_{idx}", False):
                        with st.form(key=f"form_{idx}"):
                            frozen_time = st.session_state.get(f"finish_time_{idx}")
                            st.info(f"Submitting at: {frozen_time}")
                            remarks = st.text_area("What was done?", placeholder="Enter remarks...")
                            
                            if st.form_submit_button("Submit to Admin"):
                                master_df = get_tasks()
                                m_idx = master_df[(master_df['Employee'] == row['Employee']) & (master_df['Assign_Time'] == row['Assign_Time'])].index
                                
                                if not m_idx.empty:
                                    f_dt = to_dt(frozen_time).replace(tzinfo=None)
                                    d_dt = to_dt(row["Deadline"]).replace(tzinfo=None)
                                    var_sec = int((f_dt - d_dt).total_seconds())
                                    
                                    abs_v = abs(var_sec)
                                    v_str = f"{'+' if var_sec > 0 else '-'}{abs_v//60:02d}:{abs_v%60:02d}"
                                    flag = "🟢 GREEN" if var_sec <= 0 else "🔴 RED"
                                    
                                    target = m_idx[0]
                                    master_df.at[target, "Status"] = "Finished"
                                    master_df.at[target, "Submit_Time"] = frozen_time
                                    master_df.at[target, "Time_Variance"] = v_str
                                    master_df.at[target, "Flag"] = flag
                                    master_df.at[target, "Remarks"] = remarks.replace(",", ";")
                                    
                                    save_tasks(master_df)
                                    handle_recurring_tasks(master_df.iloc[target])
                                    del st.session_state[f"finish_mode_{idx}"]
                                    st.success("Task Logged Successfully!")
                                    time.sleep(1)
                                    st.rerun()

                # --- STATUS LOGIC: PAUSED ---
                elif row["Status"] == "Paused":
                    st.warning("☕ Status: On Break")
                    if st.button("▶️ RESUME TASK", key=f"res_{idx}", use_container_width=True, type="primary"):
                        master_df = get_tasks()
                        m_idx = master_df[(master_df['Employee'] == row['Employee']) & (master_df['Assign_Time'] == row['Assign_Time'])].index
                        if not m_idx.empty:
                            target = m_idx[0]
                            now = get_now_ist().replace(tzinfo=None)
                            p_start = to_dt(row.get("Pause_Start")).replace(tzinfo=None)
                            pause_dur = now - p_start
                            
                            try:
                                prev_p = float(row.get("Total_Paused_Mins", 0))
                            except:
                                prev_p = 0.0
                            
                            master_df.at[target, "Total_Paused_Mins"] = str(round(prev_p + (pause_dur.total_seconds()/60), 2))
                            old_d = to_dt(row.get("Deadline")).replace(tzinfo=None)
                            master_df.at[target, "Deadline"] = (old_d + pause_dur).strftime("%Y-%m-%d %I:%M:%S %p")
                            master_df.at[target, "Status"] = "Running"
                            master_df.at[target, "Pause_Start"] = "N/A"
                            
                            save_tasks(master_df)
                            st.rerun()

            # --- TAB 2: WORK HISTORY ---
            with tab2:
                st.title("📊 My Work History")
                df_raw = get_tasks()
                
                if df_raw.empty:
                    st.info("No records found.")
                else:
                    my_history = df_raw[df_raw["Employee"] == st.session_state.user].copy()
                    
                    if my_history.empty:
                        st.info("No history found for your account yet.")
                    else:
                        rep_type = st.radio("View Period", ["Today", "Last 30 Days", "All Time"], horizontal=True)

                        # Timezone-Safe Filtering
                        my_history['Assign_DT'] = pd.to_datetime(my_history['Assign_Time'], errors='coerce').dt.tz_localize(None)
                        my_history = my_history.dropna(subset=['Assign_DT'])
                        
                        now_naive = get_now_ist().replace(tzinfo=None)
                        if rep_type == "Today":
                            since_date = now_naive.replace(hour=0, minute=0, second=0, microsecond=0)
                        elif rep_type == "Last 30 Days":
                            since_date = now_naive - timedelta(days=30)
                        else:
                            since_date = datetime(2000, 1, 1)

                        report_df = my_history[my_history["Assign_DT"] >= since_date].copy()

                        if not report_df.empty:
                            # Net Hours Calculation Function
                            def get_net_hours(r):
                                s = to_dt(str(r.get('Start_Time', 'N/A')))
                                f = to_dt(str(r.get('Submit_Time', 'N/A')))
                                if s and f:
                                    s, f = s.replace(tzinfo=None), f.replace(tzinfo=None)
                                    gross_hrs = (f - s).total_seconds() / 3600
                                    try:
                                        p_val = r.get("Total_Paused_Mins", 0)
                                        p_hrs = float(p_val) / 60 if p_val and str(p_val) != "N/A" else 0.0
                                    except:
                                        p_hrs = 0.0
                                    return round(max(0, gross_hrs - p_hrs), 2)
                                return 0.0

                            report_df['Net_Hours'] = report_df.apply(get_net_hours, axis=1)
                            
                            # Metrics Summary
                            st.markdown("### 📈 Performance Summary")
                            m1, m2, m3 = st.columns(3)
                            p_mins = pd.to_numeric(report_df['Total_Paused_Mins'], errors='coerce').fillna(0)
                            
                            m1.metric("Net Work Time", f"{report_df['Net_Hours'].sum():.2f} hrs")
                            m2.metric("Total Tasks", len(report_df[report_df["Status"] == "Finished"]))
                            m3.metric("Pause Duration", f"{p_mins.sum():.1f} mins")
                            
                            st.write("---")
                            
                            # Data Display
                            display_cols = ["Company", "Task", "Status", "Assign_Time", "Submit_Time", "Net_Hours", "Flag", "Remarks"]
                            report_df = report_df.sort_values("Assign_DT", ascending=False)
                            
                            st.dataframe(
                                report_df[display_cols], 
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Net_Hours": st.column_config.NumberColumn("Hours", format="%.2f hrs"),
                                    "Flag": "Performance"
                                }
                            )
                        else:
                            st.info("No tasks found for this period.")
