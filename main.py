import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh
from streamlit_gsheets import GSheetsConnection
import os
import pytz
import io

# ==========================================
# 1. DATABASE SETUP & HELPERS (GOOGLE SHEETS)
# ==========================================
ADMIN_PASSWORD = "admin123" 

# Replace these with your actual Google Sheet URLs from your browser address bar
TASKS_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_TASKS_SHEET_ID"
USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_USERS_SHEET_ID"
COMPANIES_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_COMPANIES_SHEET_ID"

# Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# [REPLACE THE LIST BELOW WITH YOUR FULL 40,000 CHARACTER LIST]
COMPANY_LIST = ["Pearl Hospitality LLC", "Shri Guru Om Inc", "276 Old Country Road LLC", "Impact Wireless LLC"]

def get_now_ist():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)

# --- GOOGLE SHEETS ADAPTER FUNCTIONS ---

def get_companies():
    try:
        df = conn.read(spreadsheet=COMPANIES_SHEET_URL, ttl="0")
        if df.empty: raise ValueError
        return df
    except:
        df = pd.DataFrame({"Company Name": COMPANY_LIST, "Hourly Rate": [0.0]*len(COMPANY_LIST)})
        conn.update(spreadsheet=COMPANIES_SHEET_URL, data=df)
        return df

def save_companies(df):
    conn.update(spreadsheet=COMPANIES_SHEET_URL, data=df)

def get_tasks(): 
    try:
        df = conn.read(spreadsheet=TASKS_SHEET_URL, ttl="0").fillna("N/A").astype(str)
        if "Remarks" not in df.columns: df["Remarks"] = ""
        df['Assign_DT'] = pd.to_datetime(df['Assign_Time'], errors='coerce')
        return df
    except:
        # Initialize empty task sheet if it fails
        cols = ["Employee", "Company", "Task", "Limit_Mins", "Assign_Time", "Start_Time", 
                "Deadline", "Submit_Time", "Time_Variance", "Status", "Flag", "Pause_Start", 
                "Scheduled_Date", "Frequency", "Total_Paused_Mins", "Pause_Count", "Remarks"]
        return pd.DataFrame(columns=cols)

def save_tasks(df): 
    if 'Assign_DT' in df.columns: 
        df = df.drop(columns=['Assign_DT'])
    conn.update(spreadsheet=TASKS_SHEET_URL, data=df)

def get_users(): 
    try:
        return conn.read(spreadsheet=USERS_SHEET_URL, ttl="0").astype(str)
    except:
        return pd.DataFrame(columns=["Username", "Password", "Department"])

def save_users(df): 
    conn.update(spreadsheet=USERS_SHEET_URL, data=df)

def to_dt(str_val):
    if str_val == "N/A" or not isinstance(str_val, str) or str_val == "": return None
    for fmt in ("%Y-%m-%d %I:%M:%S %p", "%Y-%m-%d %H:%M:%S"):
        try: return datetime.strptime(str_val, fmt)
        except: continue
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

# ==========================================
# 2. LOGIC & UI (RETAINED FROM ORIGINAL)
# ==========================================

def handle_recurring_tasks(finished_row):
    if finished_row['Frequency'] == "Once": return
    try:
        current_sched = datetime.strptime(finished_row['Scheduled_Date'], "%Y-%m-%d")
    except: return 
    
    offsets = {"Daily": 1, "Weekly": 7, "Semi-Monthly": 15, "Monthly": 30}
    next_date = current_sched + timedelta(days=offsets.get(finished_row['Frequency'], 0))
    
    df = get_tasks()
    new_task = finished_row.copy()
    new_task.update({
        'Scheduled_Date': next_date.strftime("%Y-%m-%d"),
        'Assign_Time': get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p"),
        'Status': "Pending", 'Start_Time': "Waiting", 'Deadline': "N/A", 
        'Submit_Time': "N/A", 'Time_Variance': "N/A", 'Flag': "⚪", 'Pause_Start': "N/A"
    })
    save_tasks(pd.concat([df, pd.DataFrame([new_task])], ignore_index=True))

st.set_page_config(page_title="Corp-Task Pro", layout="wide")
if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None

if st.session_state.role is None:
    st.title("🚩 ZSM Task Control Center")
    c1, c2 = st.columns(2)
    with c1:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login as Admin"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.role = "Admin"; st.rerun()
    with c2:
        u_name = st.text_input("Username")
        u_pwd = st.text_input("Password", type="password")
        if st.button("Login as Employee"):
            users = get_users()
            if not users[(users['Username'] == u_name) & (users['Password'] == u_pwd)].empty:
                st.session_state.role = "Employee"; st.session_state.user = u_name; st.rerun()
    st.stop()

# --- SHARED SIDEBAR ---
if st.sidebar.button("Logout"):
    st.session_state.role = None; st.rerun()

if st.session_state.role == "Admin":
    menu = st.sidebar.radio("Menu", ["Dashboard", "Reports", "Users", "Companies"])
    
    if menu == "Dashboard":
        st.title("👨‍💼 Task Assignment")
        u_df = get_users()
        u_list = u_df.apply(lambda x: f"{x['Username']} ({x['Department']})", axis=1).tolist() if not u_df.empty else []
        
        with st.form("assign"):
            emp_sel = st.selectbox("Employee", u_list)
            comp_db = get_companies()
            comp_sel = st.selectbox("Company", comp_db["Company Name"].tolist())
            mins = st.number_input("Minutes", 1, 1440, 15)
            freq = st.selectbox("Frequency", ["Once", "Daily", "Weekly", "Semi-Monthly", "Monthly"])
            task_desc = st.text_area("Description")
            if st.form_submit_button("Assign"):
                df = get_tasks()
                new_row = {
                    "Employee": emp_sel.split(" (")[0], "Company": comp_sel, "Task": task_desc,
                    "Limit_Mins": str(mins), "Assign_Time": get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p"),
                    "Status": "Pending", "Scheduled_Date": get_now_ist().strftime("%Y-%m-%d"),
                    "Frequency": freq, "Total_Paused_Mins": 0, "Pause_Count": 0, "Flag": "⚪"
                }
                save_tasks(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                st.success("Assigned!"); time.sleep(1); st.rerun()

    # [REPORTS, USERS, COMPANIES TABS REMAIN SAME AS YOUR ORIGINAL LOGIC]
    # Just ensure they use get_tasks()/save_tasks() instead of CSV paths.

elif st.session_state.role == "Employee":
    tab1, tab2 = st.tabs(["Active Tasks", "History"])
    with tab1:
        df = get_tasks()
        my_tasks = df[(df["Employee"] == st.session_state.user) & (df["Status"] != "Finished")]
        for idx, row in my_tasks.iterrows():
            with st.container(border=True):
                st.write(f"**{row['Company']}**: {row['Task']}")
                if row["Status"] == "Pending" and st.button("Start", key=f"st_{idx}"):
                    df.at[idx, "Start_Time"] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                    df.at[idx, "Deadline"] = (get_now_ist() + timedelta(minutes=int(float(row["Limit_Mins"])))).strftime("%Y-%m-%d %I:%M:%S %p")
                    df.at[idx, "Status"] = "Running"
                    save_tasks(df); st.rerun()
                # Pause/Finish logic continues here...

# ==========================================
# 4. ADMIN: REPORTS, USERS, & COMPANIES
# ==========================================

    elif menu == "Reports & Overrides":
        st.title("📊 Global Performance Reports & Overrides")
        df = get_tasks()
        
        f1, f2, f3 = st.columns(3)
        c_filt = f1.multiselect("Filter by Company", COMPANY_LIST)
        e_filt = f2.multiselect("Filter by Employee", get_users()['Username'].tolist())
        s_filt = f3.multiselect("Filter by Status", ["Pending", "Running", "Paused", "Finished"])
        
        if c_filt: df = df[df['Company'].isin(c_filt)]
        if e_filt: df = df[df['Employee'].isin(e_filt)]
        if s_filt: df = df[df['Status'].isin(s_filt)]

        if not df.empty:
            st.write("---")
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

            h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 2, 2])
            h1.write("**Employee/Company**")
            h2.write("**Task Description**")
            h3.write("**Status/Mins**")
            h4.write("**Time Info**")
            h5.write("**Actions**")
            st.divider()

            for idx, row in df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 2])
                col1.write(f"👤 {row['Employee']}")
                col1.caption(f"🏢 {row['Company']}")
                col2.write(row['Task'])
                status_color = {"Pending": "⚪", "Running": "🔵", "Paused": "🟡", "Finished": row['Flag']}
                col3.write(f"{status_color.get(row['Status'], '⚪')} {row['Status']}")
                col3.write(f"⏱️ {row['Limit_Mins']} mins")
                col4.caption(f"Assigned: {row['Assign_Time']}")
                if row['Submit_Time'] != "N/A":
                    col4.caption(f"Submitted: {row['Submit_Time']}")

                if col5.button("🗑️ Delete", key=f"del_task_{idx}"):
                    full_df = get_tasks().drop(idx)
                    save_tasks(full_df)
                    st.toast("Task deleted!"); time.sleep(1); st.rerun()

    elif menu == "User Management":
        st.title("👥 User Management")
        u_df = get_users()
        with st.form("add_user", clear_on_submit=True):
            st.subheader("Add New Employee")
            c1, c2, c3 = st.columns(3)
            nu = c1.text_input("New Username")
            np = c2.text_input("New Password")
            dept = c3.selectbox("Department", ["Accountant", "Tax", "Audit", "Payroll", "Admin Support", "Notices", "Sales Tax", "Book Keeping"])
            if st.form_submit_button("➕ Save User"):
                if nu and np:
                    if nu in u_df['Username'].values: st.error("User exists!")
                    else:
                        new_u = pd.DataFrame([{"Username": nu, "Password": np, "Department": dept}])
                        save_users(pd.concat([u_df, new_u], ignore_index=True))
                        st.success(f"Added {nu}!"); time.sleep(1); st.rerun()

        st.subheader("Current Employees")
        for i, r in u_df.iterrows():
            row_c1, row_c2, row_c3 = st.columns([2, 2, 2])
            row_c1.write(r['Username'])
            is_visible = st.toggle("Show", key=f"show_{i}")
            row_c2.write(f"`{r['Password']}`" if is_visible else "********")
            if row_c3.button("🗑️ Delete", key=f"del_u_{i}"):
                save_users(u_df.drop(i))
                st.toast("User deleted"); time.sleep(0.5); st.rerun()

    elif menu == "Company Management":
            st.title("🏢 Company Management")
            tab_a, tab_b = st.tabs(["Add/Edit Companies", "💰 Revenue Report"])
            with tab_a:
                comp_df = get_companies()
                with st.expander("➕ Add New Company"):
                    c_name = st.text_input("Company Name")
                    c_rate = st.number_input("Hourly Billing Rate ($)", min_value=0.0, step=1.0)
                    if st.button("Save to Database"):
                        new_row = pd.DataFrame([{"Company Name": c_name.strip(), "Hourly Rate": c_rate}])
                        save_companies(pd.concat([comp_df, new_row], ignore_index=True))
                        st.success("Added!"); time.sleep(1); st.rerun()
                st.dataframe(comp_df, use_container_width=True)

            with tab_b:
                t_df = get_tasks()
                c_df = get_companies()
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
                    st.dataframe(report[["Company", "Employee", "Task", "Hours", "Total Billable"]], use_container_width=True)

# ==========================================
# 5. EMPLOYEE VIEW: ACTIVE TASKS & HISTORY
# ==========================================

                elif st.session_state.role == "Employee":
                    tab1, tab2 = st.tabs(["🚀 Active Tasks", "📜 My Reports"])
                    with tab1:
                        st.title(f"👷 {st.session_state.user}'s Workspace")
                        df = get_tasks()
                        today_str = get_now_ist().strftime("%Y-%m-%d")
                        active_tasks = df[(df["Employee"] == st.session_state.user) & (df["Status"] != "Finished") & (df["Scheduled_Date"] <= today_str)]
                        
                        if active_tasks.empty: st.info("No tasks for today.")
                        for idx, row in active_tasks.iterrows():
                            with st.container(border=True):
                                st.subheader(f"🏢 {row['Company']}")
                                st.write(f"**Task:** {row['Task']}")
                                
                                if row["Status"] == "Pending":
                                    if st.button("▶️ ACCEPT & START", key=f"s_{idx}"):
                                        now = get_now_ist()
                                        m_val = int(float(str(row["Limit_Mins"])))
                                        df.at[idx, "Start_Time"] = now.strftime("%Y-%m-%d %I:%M:%S %p")
                                        df.at[idx, "Deadline"] = (now + timedelta(minutes=m_val)).strftime("%Y-%m-%d %I:%M:%S %p")
                                        df.at[idx, "Status"] = "Running"
                                        save_tasks(df); st.rerun()

                elif row["Status"] == "Running":
                    if not st.session_state.get(f"finish_mode_{idx}", False):
                        render_timer(row["Deadline"])
                    
                    c1, c2 = st.columns(2)
                    if c1.button("⏸️ PAUSE", key=f"p_{idx}"):
                        df.at[idx, "Pause_Start"] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Status"] = "Paused"
                        df.at[idx, "Pause_Count"] = int(float(str(row.get("Pause_Count", 0)))) + 1
                        save_tasks(df); st.rerun()
                        
                    if c2.button("✅ FINISH", key=f"f_{idx}"):
                        st.session_state[f"finish_time_{idx}"] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                        st.session_state[f"finish_mode_{idx}"] = True

                    if st.session_state.get(f"finish_mode_{idx}", False):
                        frozen_time = st.session_state[f"finish_time_{idx}"]
                        remark_input = st.text_area("Final Remarks", key=f"txt_{idx}")
                        if st.button("Confirm Submit", key=f"save_{idx}", type="primary"):
                            finish_dt, deadline_dt = to_dt(frozen_time), to_dt(row["Deadline"])
                            var = int((finish_dt - deadline_dt).total_seconds())
                            df.at[idx, "Flag"] = "🟢 GREEN" if var <= 0 else "🔴 RED"
                            df.at[idx, "Submit_Time"], df.at[idx, "Status"] = frozen_time, "Finished"
                            df.at[idx, "Time_Variance"] = f"{'+' if var > 0 else '-'}{abs(var)//60:02d}:{abs(var)%60:02d}"
                            df.at[idx, "Remarks"] = remark_input
                            save_tasks(df)
                            handle_recurring_tasks(df.iloc[idx])
                            st.rerun()

                elif row["Status"] == "Paused":
                    st.warning("☕ TASK PAUSED")
                    if st.button("▶️ RESUME", key=f"r_{idx}"):
                        p_start, now = to_dt(row["Pause_Start"]), get_now_ist()
                        pause_dur = now - p_start
                        df.at[idx, "Total_Paused_Mins"] = float(str(row.get("Total_Paused_Mins", 0))) + (pause_dur.total_seconds()/60)
                        df.at[idx, "Deadline"] = (to_dt(row["Deadline"]) + pause_dur).strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Status"], df.at[idx, "Pause_Start"] = "Running", "N/A"
                        save_tasks(df); st.rerun()

                with tab2:
                    st.title("📊 Work History")
                    df = get_tasks()
                    my_history = df[df["Employee"] == st.session_state.user]
                    rep_type = st.radio("Period", ["Daily (Today)", "Monthly (30 Days)"], horizontal=True)
                    since_date = get_now_ist().replace(hour=0, minute=0, second=0) if "Daily" in rep_type else (get_now_ist() - timedelta(days=30))
                    report_df = my_history[my_history["Assign_DT"] >= since_date].copy()
                    
                    if not report_df.empty:
                        def get_work_hours(r):
                            s, f = to_dt(r['Start_Time']), to_dt(r['Submit_Time'])
                            return round((f - s).total_seconds() / 3600, 2) if s and f else 0.0
                        report_df['Hours'] = report_df.apply(get_work_hours, axis=1)
                        st.metric("Total Work Hours", f"{report_df['Hours'].sum():.2f} hrs")
                        st.dataframe(report_df[["Company", "Task", "Assign_Time", "Submit_Time", "Hours", "Flag", "Remarks"]], use_container_width=True)
                    else: st.info("No records found.")
