import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh
import os
import pytz
from streamlit_gsheets import GSheetsConnection # type: ignore

# --- PAGE CONFIG ---
st.set_page_config(page_title="Task Management System", layout="wide")

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 1. DATABASE SETUP & HELPERS
# ==========================================
ADMIN_PASSWORD = "admin123" 

# IST Time Helper
def get_now_ist():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def to_dt(val):
    try:
        if not val or val == "N/A" or val == "Waiting": return None
        return datetime.strptime(val, "%I:%M:%S %p")
    except:
        return None

# --- CLOUD DATA FUNCTIONS ---
def get_tasks():
    df = conn.read(worksheet="Tasks", ttl=0).fillna("N/A").astype(str)
    if "Remarks" not in df.columns: df["Remarks"] = ""
    df['Assign_DT'] = pd.to_datetime(df['Assign_Time'], errors='coerce')
    return df

def save_tasks(df):
    if 'Assign_DT' in df.columns: df = df.drop(columns=['Assign_DT'])
    conn.update(worksheet="Tasks", data=df)

def get_users():
    return conn.read(worksheet="Users", ttl=0).astype(str)

def save_users(df):
    conn.update(worksheet="Users", data=df)

def get_companies():
    # This pulls from your "Companies" tab where you put the names and rates
    return conn.read(worksheet="Companies", ttl=0)

# --- INITIAL DATA LOAD ---
users_df = get_users()
comp_db_global = get_companies()
# This keeps your dynamic list logic
COMPANY_LIST = comp_db_global["Company_Name"].tolist()

# ==========================================
# 2. LOGIN SYSTEM (YOUR EXACT LOGIC)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None

if not st.session_state.logged_in:
    st.title("🔐 Access Portal")
    user_list = users_df['Username'].tolist()
    u_input = st.selectbox("Identify Yourself", ["Select User"] + user_list)
    
    if u_input != "Select User":
        role = users_df[users_df['Username'] == u_input]['Role'].values[0]
        if role == "Admin":
            pwd = st.text_input("Admin Password", type="password")
            if st.button("Verify & Enter"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.logged_in, st.session_state.user, st.session_state.role = True, u_input, "Admin"
                    st.rerun()
                else: st.error("Invalid Admin Password")
        else:
            if st.button("Enter Dashboard"):
                st.session_state.logged_in, st.session_state.user, st.session_state.role = True, u_input, "Employee"
                st.rerun()
else:
    # --- AUTO REFRESH ---
    st_autorefresh(interval=30000, key="datarefresh")

    # --- SIDEBAR ---
    st.sidebar.title(f"👤 {st.session_state.user}")
    st.sidebar.info(f"Role: {st.session_state.role}")
    
    menu_options = ["My Workspace", "Live Monitor"]
    if st.session_state.role == "Admin":
        menu_options += ["Assign Task", "User Management", "Reports"]
    
    menu = st.sidebar.radio("Navigate", menu_options)
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 1. MY WORKSPACE ---
    if menu == "My Workspace":
        st.header("⚡ My Active Tasks")
        df = get_tasks()
        my_tasks = df[df['Employee'] == st.session_state.user]
        
        if my_tasks.empty:
            st.info("No tasks assigned to you.")
        else:
            for index, row in my_tasks.iterrows():
                with st.expander(f"{row['Company']} - {row['Task']} ({row['Status']})"):
                    # Your timer logic continues here...
                    if row['Status'] == "Pending":
                        if st.button("▶️ Start", key=f"start_{index}"):
                            df.at[index, 'Status'] = "Running"
                            df.at[index, 'Start_Time'] = get_now_ist().strftime("%I:%M:%S %p")
                            save_tasks(df)
                            st.rerun()
                    # (Keep all your existing timer/pause logic below this)

    # --- 2. ASSIGN TASK (THE FIXED VERSION) ---
    elif menu == "Assign Task":
        st.header("🎯 Task Distribution")
        u_display_list = [f"{r['Username']} ({r['Role']})" for _, r in users_df.iterrows()]
        user_map = {f"{r['Username']} ({r['Role']})": r['Username'] for _, r in users_df.iterrows()}
        
        msg_spot = st.empty()
        with st.form("task_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: selected_display = st.selectbox("Assign To", u_display_list)
            with c2: comp = st.selectbox("Company", COMPANY_LIST)
            with c3: mins = st.number_input("Mins Allowed", min_value=1, value=15)
            
            c4, c5 = st.columns(2)
            with c4: sched_date = st.date_input("Schedule Date", get_now_ist())
            with c5: freq = st.selectbox("Repeat", ["Once", "Daily", "Weekly", "Monthly"])

            tsk = st.text_area("Task Details")
            submitted = st.form_submit_button("🚀 SCHEDULE TASK")
            
            if submitted:
                emp = user_map.get(selected_display)
                df = get_tasks()
                new_row = {
                    "Employee": emp, "Company": comp, "Task": tsk, "Limit_Mins": str(mins),
                    "Assign_Time": get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p"),
                    "Status": "Pending", "Scheduled_Date": str(sched_date), "Frequency": freq,
                    "Total_Paused_Mins": 0, "Pause_Count": 0, "Remarks": "",
                    "Start_Time": "Waiting", "Deadline": "N/A", "Submit_Time": "N/A", 
                    "Time_Variance": "N/A", "Flag": "⚪", "Pause_Start": "N/A"
                }
                save_tasks(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                st.balloons()
                st.success(f"Task assigned to {emp}!")
                time.sleep(1)
                st.rerun()

    # --- 3. LIVE MONITOR ---
    elif menu == "Live Monitor":
        st.header("📊 Live Dashboard")
        st.dataframe(get_tasks().drop(columns=['Assign_DT']), use_container_width=True)

    
    # --- 3. USER MANAGEMENT ---
    elif menu == "User Management":
        st.title("👥 Employee Database")
        with st.expander("Add New Employee"):
            new_u = st.text_input("Name")
            new_r = st.selectbox("Role", ["Employee", "Admin"])
            if st.button("Save User"):
                u_df = get_users()
                save_users(pd.concat([u_df, pd.DataFrame([{"Username": new_u, "Role": new_r}])]))
                st.rerun()

    # --- 4. LIVE DASHBOARD ---
    elif menu == "Live Dashboard":
        st.title("📊 Live Monitoring")
        st.dataframe(get_tasks().drop(columns=['Assign_DT']), use_container_width=True)

    # --- 5. REPORTS ---
    elif menu == "Reports":
        st.title("📅 Performance Reports")
        df = get_tasks()
        st.write("Summary of all completed tasks:")
        st.dataframe(df[df['Status'] == "Completed"], use_container_width=True)


