import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import pytz
from streamlit_gsheets import GSheetsConnection # type: ignore

# --- PAGE CONFIG ---
st.set_page_config(page_title="Task Management System", layout="wide")

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HELPER FUNCTIONS ---
def get_now_ist():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def to_dt(val):
    try:
        if not val or val == "N/A" or val == "Waiting": return None
        return datetime.strptime(val, "%I:%M:%S %p")
    except:
        return None

def get_tasks():
    # Pulls fresh data from the "Tasks" tab
    df = conn.read(worksheet="Tasks", ttl=0).fillna("N/A").astype(str)
    if "Remarks" not in df.columns:
        df["Remarks"] = ""
    # Helper for sorting and reports
    df['Assign_DT'] = pd.to_datetime(df['Assign_Time'], errors='coerce')
    return df

def save_tasks(df):
    # Saves changes back to the cloud
    if 'Assign_DT' in df.columns:
        df = df.drop(columns=['Assign_DT'])
    conn.update(worksheet="Tasks", data=df)

def get_users(): 
    return conn.read(worksheet="Users", ttl=0).astype(str)

def save_users(df): 
    conn.update(worksheet="Users", data=df)

def get_companies():
    return conn.read(worksheet="Companies", ttl=0)

# --- INITIAL DATA LOAD ---
users_df = get_users()
comp_db_global = get_companies()
u_display_list = [f"{r['Username']} ({r['Role']})" for _, r in users_df.iterrows()]
user_map = {f"{r['Username']} ({r['Role']})": r['Username'] for _, r in users_df.iterrows()}

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None

if not st.session_state.logged_in:
    st.title("🔐 Login")
    user_input = st.selectbox("Select Your Name", users_df['Username'].tolist())
    if st.button("Login"):
        role = users_df[users_df['Username'] == user_input]['Role'].values[0]
        st.session_state.logged_in = True
        st.session_state.user = user_input
        st.session_state.role = role
        st.rerun()
else:
    # --- SIDEBAR ---
    st.sidebar.title(f"👋 {st.session_state.user}")
    menu_options = ["My Tasks", "Live Dashboard"]
    if st.session_state.role == "Admin":
        menu_options += ["Task Assignment", "User Management", "Reports"]
    
    menu = st.sidebar.radio("Navigation", menu_options)
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 1. MY TASKS ---
    if menu == "My Tasks":
        st.title("📝 My Tasks")
        df = get_tasks()
        my_tasks = df[df['Employee'] == st.session_state.user]
        
        for index, row in my_tasks.iterrows():
            with st.expander(f"{row['Company']} - {row['Task']} [{row['Status']}]"):
                if row['Status'] == "Pending":
                    if st.button("▶️ Start Task", key=f"start_{index}"):
                        df.at[index, 'Status'] = "Running"
                        df.at[index, 'Start_Time'] = get_now_ist().strftime("%I:%M:%S %p")
                        save_tasks(df)
                        st.rerun()
                elif row['Status'] == "Running":
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Submit", key=f"sub_{index}"):
                        df.at[index, 'Status'] = "Completed"
                        df.at[index, 'Submit_Time'] = get_now_ist().strftime("%I:%M:%S %p")
                        save_tasks(df)
                        st.rerun()
                    if col2.button("⏸️ Pause", key=f"pau_{index}"):
                        df.at[index, 'Status'] = "Paused"
                        df.at[index, 'Pause_Start'] = get_now_ist().strftime("%I:%M:%S %p")
                        save_tasks(df)
                        st.rerun()

    # --- 2. TASK ASSIGNMENT ---
    elif menu == "Task Assignment":
        st.title("🚀 Assign New Task")
        msg_spot = st.empty()
        with st.form("task_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: selected_display = st.selectbox("Employee", u_display_list)
            with c2: comp = st.selectbox("Company", comp_db_global["Company_Name"].tolist())
            with c3: mins = st.number_input("Limit (Mins)", min_value=1, value=15)
            
            c4, c5 = st.columns(2)
            with c4: sched_date = st.date_input("Schedule Date", get_now_ist())
            with c5: freq = st.selectbox("Frequency", ["Once", "Daily", "Weekly", "Monthly"])

            tsk = st.text_area("Task Description")
            if st.form_submit_button("Assign Task"):
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
                st.success("Task Assigned!")
                time.sleep(1)
                st.rerun()

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
