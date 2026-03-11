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
import io

st.set_page_config(page_title="ZSM Task Control", layout="wide", page_icon="🚩")

# Initialize Supabase
url: str = st.secrets["supabase"]["url"]
key: str = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

ADMIN_PASSWORD = "admin123" 

# --- GLOBAL REFRESH (Every 60 Seconds) ---
st_autorefresh(interval=60000, key="datarefresh")

def handle_recurring_tasks(row):
    """Resets a recurring task using the unique ID."""
    try:
        supabase.table("tasks").update({
            "Status": "Pending",
            "Start_Time": None,
            "Submit_Time": None,
            "Pause_Start": "N/A",
            "Pause_Count": 0,
            "Total_Paused_Mins": "0",
            "Time_Variance": None,
            "Flag": None,
            "Remarks": None
        }).eq("id", row["id"]).execute()
    except Exception as e:
        st.error(f"Failed to reset recurring task: {e}")

# ==========================================
# 2. LOGIC HELPERS
# ==========================================

def get_now_ist():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def to_dt(str_val):
    if not str_val or str_val in ["N/A", "None", "", "Waiting"]:
        return None
    try:
        dt = pd.to_datetime(str_val)
        return dt.to_pydatetime()
    except Exception:
        return None

def render_timer(deadline_str):
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
    response = supabase.table("users").select("*").execute()
    return pd.DataFrame(response.data)

def get_companies():
    response = supabase.table("companies").select("*").execute()
    return pd.DataFrame(response.data)

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
    st.stop()

# ==========================================
# 5. ADMIN MODULE
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
        u_list = [u['Username'] for _, u in users_df.iterrows()] if not users_df.empty else []
        comp_list = comp_db["Company Name"].tolist() if not comp_db.empty else []

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
                new_task = {
                    "Employee": selected_u, "Company": company, "Task": desc.strip(),
                    "Limit_Mins": int(mins), "Assign_Time": get_now_ist().isoformat(),
                    "Status": "Pending", "Scheduled_Date": s_date.strftime("%Y-%m-%d"),
                    "Frequency": freq, "Total_Paused_Mins": "0.0", "Time_Variance": "00:00", "Flag": "WHITE"
                }
                supabase.table("tasks").insert(new_task).execute()
                st.cache_data.clear()
                st.success(f"Task assigned to {selected_u}!")
                st.rerun()

    elif menu == "Live Reports":
        st.title("📊 Live Monitoring")
        df = get_tasks()
        if not df.empty:
            target_day = st.date_input("Filter Date", get_now_ist())
            filtered_df = df[df['Scheduled_Date'] == target_day.strftime("%Y-%m-%d")]
            
            for _, row in filtered_df.iterrows():
                row_key = f"admin_{row['id']}"
                with st.expander(f"{row['Status']} | {row['Employee']} - {row['Company']}"):
                    if st.button("🗑️ Delete Task", key=f"del_{row_key}"):
                        supabase.table("tasks").delete().eq("id", row["id"]).execute()
                        st.cache_data.clear()
                        st.rerun()

    elif menu == "User Management":
        st.title("👥 User Management")
        # Logic to Add/Delete users using the 'users' table...
        # (Similar to your previous User Management section, targeting by Username)

    elif menu == "Companies":
        st.title("🏢 Companies")
        # Logic to manage companies using the 'companies' table...

# ==========================================
# 6. EMPLOYEE VIEW
# ==========================================
elif st.session_state.role == "Employee":
    tab1, tab2 = st.tabs(["🚀 Active Tasks", "📜 My Reports"])
    
    with tab1:
        st.title(f"👷 {st.session_state.user}'s Workspace")
        df = get_tasks()
        today_str = get_now_ist().strftime("%Y-%m-%d")
        
        if not df.empty:
            active_tasks = df[
                (df["Employee"] == st.session_state.user) & 
                (df["Status"] != "Finished") &
                (df["Scheduled_Date"] <= today_str)
            ].copy()
            
            if active_tasks.empty:
                st.info("No active tasks for today.")
            else:
                for idx, row in active_tasks.iterrows():
                    btn_id = f"task_{row['id']}"
                    
                    with st.container(border=True):
                        st.subheader(f"🏢 {row['Company']}")
                        st.write(f"**Task:** {row['Task']}")
                        
                        if row["Status"] == "Pending":
                            if st.button("▶️ START", key=f"start_{btn_id}", use_container_width=True, type="primary"):
                                deadline = get_now_ist() + timedelta(minutes=int(row['Limit_Mins']))
                                supabase.table("tasks").update({
                                    "Start_Time": get_now_ist().isoformat(),
                                    "Deadline": deadline.isoformat(),
                                    "Status": "Running"
                                }).eq("id", row["id"]).execute()
                                st.cache_data.clear()
                                st.rerun()

                        elif row["Status"] == "Running":
                            render_timer(row["Deadline"])
                            c1, c2 = st.columns(2)
                            if c1.button("Pause", key=f"pause_{btn_id}", use_container_width=True):
                                supabase.table("tasks").update({
                                    "Pause_Start": get_now_ist().isoformat(),
                                    "Status": "Paused",
                                    "Pause_Count": int(row.get("Pause_Count", 0) or 0) + 1
                                }).eq("id", row["id"]).execute()
                                st.cache_data.clear()
                                st.rerun()
                            
                            if c2.button("Finish", key=f"fin_{btn_id}", use_container_width=True):
                                st.session_state[f"finish_mode_{btn_id}"] = True
                                st.rerun()

                        elif row["Status"] == "Paused":
                            if st.button("Resume", key=f"res_{btn_id}", use_container_width=True, type="primary"):
                                # Calculate time difference and update Deadline using row['id']
                                # ... (Resume logic as shown in previous versions) ...
                                st.cache_data.clear()
                                st.rerun()

                        if st.session_state.get(f"finish_mode_{btn_id}", False):
                            with st.form(key=f"form_{btn_id}"):
                                rem = st.text_area("Remarks")
                                if st.form_submit_button("Submit"):
                                    supabase.table("tasks").update({
                                        "Status": "Finished",
                                        "Submit_Time": get_now_ist().isoformat(),
                                        "Remarks": rem
                                    }).eq("id", row["id"]).execute()
                                    if row["Frequency"] != "Once":
                                        handle_recurring_tasks(row)
                                    st.session_state[f"finish_mode_{btn_id}"] = False
                                    st.cache_data.clear()
                                    st.rerun()
