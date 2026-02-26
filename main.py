import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh
import os
# ==========================================
# 1. DATABASE SETUP & HELPERS
# ==========================================
ADMIN_PASSWORD = "admin123" 
TASK_DB = "task_system_final.csv"
USER_DB = "users_db_final.csv"
COMPANY_LIST = ["Pearl Hospitality LLC", "Shri Guru Om Inc", "276 Old Country Road LLC", "Impact Wireless LLC",
    "Deluxe Services USA Inc", "SM Auto Tech Inc", "Venus Auto Parts Inc", "Venus Realty Group LLC",
    "Krishs Indian Bistro Corp", "Lisas Crown Fried Chicken", "Bns Industries Inc", "S&S Sports Inc",
    "Gip Industries Inc", "Hottest Footwear Com Inc", "Hicksville Chaap LLC", "Giapreet LLC",
    "Giorgio West LLC", "Ikta Lifestyle LLC", "Singh Management LLC", "As Sports 46 Inc",
    "Scratch Sports Inc", "Ss Coffee Farmingdale Inc", "Mad Kicks LLC", "BVS Inc",
    "Fresh Food Group LLC", "Royal Blue Property 15 LLC", "Royal Blue Property 7 LLC", "905 Waverly Realty LLC",
    "Gadgets LLC", "Zupple LLC", "Guru Nanak'S Kitchen Inc.", "145 Main Patterson LLC",
    "229 Broadhollow Realty LLC", "Amritapriya LLC", "101 Chaap LLC", "741 Motor Cars LLC",
    "Crimson Nova Inc", "Silver Ember Inc", "Velvet Horizon Inc", "1467 Annandale Realty LLC",
    "Air America Drones LLC", "Dab Clean LLC", "Pgi Technologies LLC", "Safeguard Singh Management",
    "Realty G", "Sidanas Inc", "749 Farmingdale Realty LLC", "Royal Blue Property 19 LLC",
    "19962 Franz Rd Realty LLC", "905 Land Realty LLC", "Hillside Chaap LLC", "65 Mahan Realty LLC",
    "Starbucks", "S&S Sports Inc (Ny)", "S&S Sports Inc (Ny) (Whoesale)", "Cafe Di Mondo Inc",
    "Francescos Cafe & BakeryInc", "Moonbucks Inc", "P&F Bakers Inc", "South Broadway Realty Enterprises",
    "AGRO BUSINEES GROUP", "The Barkary Bakery Corp", "The Barkary Corp", "The Barking Bakery Corp",
    "Cafe Di Sole Inc", "Grand Cafe Bakery Inc", "Farmington Hari LLC", "New Shs Properties LLC",
    "Shs Properties Inc", "Sky Hari LLC", "St Hari Apartments LLC", "St Hari Properties Inc",
    "Us Hari Properties Inc", "Shs Auto Parts Inc", "831 Building LLC", "Caprio & Caprio LLC",
    "NI Mobile Inc", "Avis Property LLC", "Sugar Cell Inc", "Avin Builders Inc",
    "Dove Street LLC", "New Land Estate Inc", "Om Paving Corp", "New York Cardiovascular Care PC",
    "TRJRes Inc", "LI Investors LLC", "TRJ Associates Group LLC", "Tammy Management Inc",
    "Blue Coral NY Inc", "Pooja Fashion & Style Inc", "Pooja Stitch Craft Inc", "609 Fulton Pediatrics PC",
    "Fulton Avenue Realty LLC", "Charan Electrical Enterprises", "Minesh Properties Inc", "New Generation Development LLC",
    "Astoria Delancy Hotel Corp", "Central NY Hospitality LLC", "Crown City Hospitality LLC", "Anastasio Landscaping Inc",
    "Anshima Homes LLC", "Horizon Star Services LLC", "Eesha Inc", "Addvanced Carpentry Inc",
    "Deep Distributors Greator Ny Inc", "Golden Touch Ice Cream Inc", "Guru Fashions Inc", "John Auto Center Inc",
    "M&M Builders & Developers Inc", "Om Paving Inc", "Paramount Wireless LLC", "SHS Auto Parts Inc",
    "Andrew Maintance Inc", "4Th Avenue Real Estate Inc", "7508 Chicken Corp", "Fourth Avenue Merchant Inc",
    "Futurewise Insurance Brokerage Corp", "Liu Electric LLC", "Royal Star Insurance Brokerage Corp", "Scott Group Insurance Brokerage Corp",
    "Futurewise Business Inc", "Total Wireless Of New England Inc", "Brewer Hotel LLC", "Pinnacle Mobility LLC",
    "Pinnacle Mobility Retail Inc", "Stellar Wireless Retail Ny Inc", "Superior Victory Hotel LLC", "Cafe Dolce Vita Corp",
    "Green Keeper Landscaping LLC", "Gyan Malhotra LLC", "Kama Hospitality Inc", "Vita Food Corp",
    "Frienldy Star Fuel Inc", "Cute Cuts Inc", "Home Improvment By George Corp", "Jackson Plumbing & Hvac Supplies Corp",
    "Prime Construction Usa Inc", "Belleville Oil Inc", "Jamaica Fuel Inc", "Jersey Mart Inc",
    "Ks Fuel Inc", "Remsen Fuel Inc", "Rt Fuel Inc", "Tatla Gas Inc",
    "Tatla Petroleum Inc", "Wallington Gas Inc", "Yuvi Gas Inc", "Sai Express Inc",
    "On Balance Search Consultants LLC", "Minesh Properties LLC", "Hudson View Films & Tv Inc", "Sai Restaurant Enterprise Inc",
    "The Pearl Hospitality LLC", "Avleen Food Group LLC", "MG Elite Group LLC", "Hickville Jewelry Traders Inc",
    "Advantage Pro Training Inc", "AG Parts USA Inc", "Gizmotech LLC", "Js Sethi Inc",
    "Shree BhadraKali Inc", "Singh Sethi Inc", "Glamour Usa Inc", "Indian Street Food LLC",
    "Law Office Of Abe George", "Ramos Consulting Inc", "Reliance Fashion Group Inc", "Shawarma Paradise LLC",
    "Superride Suspension Inc", "Rajdeep Enterprises LLC", "Good Faith Restaurant Incorporated", "A & P Auto Body & Repair Inc",
    "Azhar Construction Inc", "120 Osborn Holding LLC", "BWI 827 LLC", "Sunraise Equity Group LLC",
    "Thatford Lodging LLC", "Best Management Solutions Inc", "Xtreme Realty Holding LLC", "Xtreme Solutioons Services Corp",
    "Osborn Operating Hospitality Corp", "Thatford Operating Hospitality Corp", "ABM Electric Inc", "Blue Falcon Realty & Management Corp",
    "Jot Realty Inc", "Maryland Hospitality LLC", "BWI-NY Builders LLC", "Jackson Plumbing & HVAC Supplies Co",
    "144 Investors LLC", "165 Investors LLC", "Umbrella Investors LLC", "262 Investors LLC",
    "33 Investors LLC", "38th Avenue Hotels LLC", "39th Avenue Hospitality LLC", "Deep Distibutors Greater NY Inc",
    "Green Ready Mixx LLC", "78 Investors LLC", "Supreme Builders Inc", "Hunts Point Petroleum LLC",
    "Dala Builders Corp", "3290 Realty LLC", "Sunny Developers LLC", "Anthonys Insulation Corp",
    "Dynamic Capital LLC", "261-09 Hillside Avenue LLC", "261-11 Hillside Avenue LLC", "A And N Hospitality LLC",
    "Langdale Realty LLC", "Braddock Investors LLC", "Fourth Avenue Merchants Inc", "LIU Electric LLC",
    "Glen Oaks Liquor Inc", "Dynamic Builders Us Inc", "Dynamic Cellular Inc", "LI Investors Group",
    "TRJ Associates Group", "TRJ Developers", "Direct Source Solutions", "10 Dix Hills LLC",
    "11 Bethpage LLC 47", "10 East Isllip LLC", "10 Westbury LLC", "10 East Meadow LLC",
    "1073 Westminster LLC", "10 Huntington LLC", "68 Harrison LLC New", "Balen CGA",
    "10 Floral Ave LLC", "10 Lakeville Drive LLC", "1010 Jerusalem Ave LLC", "10 Miami NY LLC",
    "68 Dryden ST LLC", "118 Ryder Avenue LLC", "28 Parkway BLVD LLC", "460 Jefferson LLC",
    "76 Abey LLC", "120 - 06 135th ST LLC", "10 N Babylon - 160 Kime", "36 Sycamore LLC",
    "Trj Hospitality Group Inc", "Dress Your Home LLC", "26 Parkway LLC", "JR Property Group LLC",
    "Jordan 3 LLC", "Hicks 37 LLC", "141 MYERS AVENUE LLC", "Bay Shore 10 LLC",
    "Hunter 8 LLC", "Bay 39 LLC", "Brooker 37 LLC", "Central 10 LLC",
    "Amityville Gn LLC", "Coram Westfield LLC", "Central 12 LLC", "Central 14 LLC",
    "Central 13 LLC", "Islip 10 LLC", "Copiague 10 LLC", "Amityville 10 LLC",
    "Law office of Abe George, PC", "TVM Group LLC", "IL Fornaretto II LLC", "IL Fornaretto III LLC",
    "Les Fine Wine & Spirit LLC", "Universal Hotel LLC", "Guru Fashion Inc", "Sai Restaurant Enterprises Inc",
    "Sai Enterprises Inc", "Milos & Milson Inc", "Juno Development LLC", "Insurance Professional Agency Inc",
    "Delphis Equipment and Trucking Inc", "Insurance Pros Agency Inc (Florida)", "Hudson View Film & TV Inc", "Home Improvement By George Corp",
    "Ramos Consulting Services Inc", "Cute Cuts 2 Inc", "Deluxe Service USA Inc", "148 Meriline Ave LLC",
    "2004 Caddo Street LLC", "United Group Retail LLC", "World Realty LLC", "Lisa's Crown Fried Chicken Inc",
    "Krish's Indian Bistro Corp", "NBS Distribuiton LLC", "On Balance Search Consultant LLC", "NS Consulting Group LLC",
    "NS Hospitality LLC", "NS Realty 294 LLC", "Metro Management Solutions NY LLC", "Pinnacle Mobility NY Inc",
    "Sabharwal Properties 2 LLC", "Star Connect Group LLC", "Total Wireless of FL Inc", "NS Mobility Inc",
    "Tottallink Florida Inc", "Mobile USA Inc", "Singhsethi Inc(Noor)", "Kama Hospitality LLC",
    "23 Fire Place LLC", "Cinnamon Kitchen LLC", "Dawn Staffing Solution Inc", "Garnet Shipping Inc",
    "Carlux Limo Inc", "Carlux Limo Worldwide Inc", "Venus 1919 Deer Park Ave LLC", "Entreprenaari LLC",
    "Kayaan Services Inc", "Kriti Services Inc", "Aurum By Teesha", "US Executive Limo Inc",
    "Preet Construction Group LTD", "Bala Fitness of Jerome", "Bala Fitness of Third Avenue LLC", "New York Masonry & Renovation Inc",
    "Troy Installer Inc", "Green World Distribution Inc", "Axis My America Inc", "Virk US Limo Inc",
    "Harsh Multani Limo Inc", "Online Shoppers World LLC", "ConnectQuo LLC", "Fatma Shamsi Inc",
    "Kaftech GI Construction Inc", "Kafetech Inc", "Jewel Junction Inc", "JCR Fitness LLC",
    "KNK Distributors Inc", "Sunlab Contractor Inc", "United City Contracting Inc", "Empyrean Global Limited Company",
    "A&P Auto Body & Repair Inc", "Andrew Maintenance Inc", "Arvat Services Inc", "Brand Sales Network Inc",
    "Swami Contracting Inc", "Hillside Avenue 23504 LLC", "Bony Car Services Corp", "Arkon Builders LLC",
    "Divine Craft By Himalayas Inc", "Accounting Tax and Business Solution Inc", "Deepreet LLC", "IT Palace",
    "Ezetop Inc", "BAC Express Incorporated", "Farmingdale Partner LLC", "At Play Amusements Inc",
    "Farmingdale Food Court Inc", "Maribella LLC", "Oak Knowledge LLC", "Nest Group LLC",
    "Apollo Telecom Inc", "Ascan Street Inc", "A&H Equity Partners Inc", "Turingtech LLC",
    "Just Code Inc", "Mila Ventures Corp", "MY Own Brew LLC", "Pelican Restaurant Inc",
    "Voguish Couture Inc", "Blissful Aesthetics Inc", "Profusion Solar LLC", "Green Keepar Landscaping LLC",
    "Eric Harris Art Inc", "Bulldozer Hospitality Group Inc", "Rockwell 77 LLC", "Prime Ten LLC",
    "Prime Twelve LLC", "American Standard Hospitality Group", "Imani Express Inc", "Rock 51 LLC",
    "Prime 107 Inc", "Bulldozer Nyc LLC", "Hari Dev Inc", "Hari Ram Inc",
    "Coco & Maui Corp", "Hare Krishna Wappingers LLC", "Kunj Bihari LLC", "A&N Food Group LLC",
    "Good Faith Restaurants Inc", "Loroda LLC", "Bruzz LLC", "Myra Group Inc",
    "All Season Contractors Corp", "Restore & Elevate Nutrition Corp", "Superior Van Wyck Hotel LLC", "Horizon Star Fuel Inc",
    "New Generation Astoria LLC", "Get My Rugs LLC", "Kika Home Collections Inc", "BBH Homes LLC",
    "1028 Capital LLC", "Jackson Jewelry Group Inc", "Hicksville Jewelry Traders Inc"]

def to_dt(str_val):
    if str_val == "N/A" or not isinstance(str_val, str) or str_val == "":
        return None
    try:
        return datetime.strptime(str_val, "%Y-%m-%d %H:%M:%S")
    except:
        return None
@st.fragment(run_every="1s")
def render_timer(deadline_str):
    deadline_dt = to_dt(deadline_str)
    if deadline_dt:
        diff = deadline_dt - datetime.now()
        secs = int(diff.total_seconds())
        if secs > 0:
            st.metric("⏳ Time Remaining", f"{secs//60}m {secs%60}s")
        else:
            st.error("⚠️ OVERDUE")
            st.metric("Time Overdue", f"{abs(secs)//60}m {abs(secs)%60}s")

TASK_COLS = ["Employee", "Company", "Task", "Limit_Mins", "Assign_Time", "Start_Time", 
             "Deadline", "Submit_Time", "Time_Variance", "Status", "Flag", "Pause_Start", 
             "Scheduled_Date", "Frequency"]
USER_COLS = ["Username", "Password", "Department"]

for db, cols in {TASK_DB: TASK_COLS, USER_DB: USER_COLS}.items():
    if not os.path.exists(db):
        pd.DataFrame(columns=cols).to_csv(db, index=False)

def get_tasks(): 
    df = pd.read_csv(TASK_DB).fillna("N/A").astype(str)
    if "Remarks" not in df.columns:
        df["Remarks"] = ""
    df['Assign_DT'] = pd.to_datetime(df['Assign_Time'], errors='coerce')
    return df

def save_tasks(df): 
    if 'Assign_DT' in df.columns: 
        df = df.drop(columns=['Assign_DT'])
    df.to_csv(TASK_DB, index=False)

def get_users(): return pd.read_csv(USER_DB).astype(str)
def save_users(df): df.to_csv(USER_DB, index=False)
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
    new_task['Assign_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    menu = st.sidebar.radio("Main Menu", ["Dashboard", "Reports & Overrides", "User Management"])
    
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
                # Use the new display list here
                selected_display = st.selectbox("Assign To Employee", u_display_list)
            with c2: comp = st.selectbox("Company Name", COMPANY_LIST)
            with c3: mins = st.number_input("Minutes Allowed", min_value=1, value=15)
            
            # --- NEW SCHEDULING FIELDS ---
            c4, c5 = st.columns(2)
            with c4: sched_date = st.date_input("Schedule Date", datetime.now())
            with c5: freq = st.selectbox("Repeat Frequency", ["Once", "Daily", "Weekly", "Semi-Monthly", "Monthly"])

            tsk = st.text_area("Task Description")
            submitted = st.form_submit_button("🚀 SCHEDULE / ASSIGN TASK")
            
            if submitted:
                if not u_display_list or u_display_list == ["No Users Available"]:
                    st.error("Cannot assign task: No employees found.")
                elif tsk.strip() == "":
                    st.error("Please enter a task description.")
                else:
                    # --- PART 2: GET CLEAN USERNAME ---
                    emp = user_map.get(selected_display, selected_display)
                    
                    df = get_tasks()
                    new_row = {
                        "Employee": emp, "Company": comp, "Task": tsk, "Limit_Mins": str(mins), 
                        "Assign_Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Start_Time": "Waiting", "Deadline": "N/A", "Submit_Time": "N/A", 
                        "Time_Variance": "N/A", "Status": "Pending", "Flag": "⚪", "Pause_Start": "N/A",
                        "Scheduled_Date": sched_date.strftime("%Y-%m-%d"),
                        "Frequency": freq
                    }
                    save_tasks(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                    
                    # --- KEEPING ALL YOUR ICONS AND EFFECTS ---
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
                file_name=f"Task_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
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
            with c3: dept = st.selectbox("Department", ["Accountant", "Tax", "Audit", "Payroll", "Admin Support", "Book Keeping"])
            
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

# --- EMPLOYEE VIEW ---
elif st.session_state.role == "Employee":
    tab1, tab2 = st.tabs(["🚀 Active Tasks", "📜 My Reports"])
    
    with tab1:
        st.title(f"👷 {st.session_state.user}'s Workspace")
        df = get_tasks()
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
# --- STEP 5: FILTER BY DATE ---
        today_str = datetime.now().strftime("%Y-%m-%d")
        
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
                
                if st.button("▶️ ACCEPT & START", key=f"s_{idx}"):
                        now = datetime.now()
                        # --- FIX START ---
                        try:
                            mins_val = int(float(str(row["Limit_Mins"])))
                        except:
                            mins_val = 15 # Default fallback
                        
                        deadline = now + timedelta(minutes=mins_val)
                        # --- FIX END ---
                        df.at[idx, "Start_Time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                        df.at[idx, "Deadline"] = deadline.strftime("%Y-%m-%d %H:%M:%S")
                        df.at[idx, "Status"] = "Running"
                        save_tasks(df); st.rerun()

                elif row["Status"] == "Running":
                    # This calls the fragment to tick every second
                    if not st.session_state.get(f"finish_mode_{idx}", False):
                        render_timer(row["Deadline"])
                    else:
                        st.warning("⚠️ Timer stopped. Waiting for remarks.")  

                    # Indent these lines so they stay inside the 'elif'
                    c1, c2 = st.columns(2)
                    
                    if c1.button("⏸️ PAUSE", key=f"p_{idx}"):
                        df.at[idx, "Pause_Start"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        df.at[idx, "Status"] = "Paused"
                        save_tasks(df)
                        st.rerun()
                        
                    if c2.button("✅ FINISH", key=f"f_{idx}"):
                        st.session_state[f"finish_time_{idx}"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                        pause_dur = datetime.now() - p_start
                        new_deadline = to_dt(row["Deadline"]) + pause_dur
                        df.at[idx, "Deadline"] = new_deadline.strftime("%Y-%m-%d %H:%M:%S")
                        df.at[idx, "Status"] = "Running"
                        df.at[idx, "Pause_Start"] = "N/A"
                        save_tasks(df); st.rerun()

    with tab2:
        st.title("📊 Work History")
        df = get_tasks()
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        my_history = df[df["Employee"] == st.session_state.user]
        rep_type = st.radio("Period", ["Daily (Today)", "Monthly (30 Days)"], horizontal=True)
        since_date = today_start if "Daily" in rep_type else (datetime.now() - timedelta(days=30))
        report_df = my_history[my_history["Assign_DT"] >= since_date].copy()
        
        def get_work_hours(r):
            s, f = to_dt(r['Start_Time']), to_dt(r['Submit_Time'])
            return round((f - s).total_seconds() / 3600, 2) if s and f else 0.0

        if not report_df.empty:
            report_df['Hours'] = report_df.apply(get_work_hours, axis=1)
            st.metric(f"Total Hours", f"{report_df['Hours'].sum():.2f} hrs")
            st.dataframe(report_df[["Company", "Task", "Assign_Time", "Submit_Time", "Hours", "Flag"]], use_container_width=True)
            st.dataframe(report_df[["Company", "Task", "Assign_Time", "Submit_Time", "Hours", "Flag", "Remarks"]], use_container_width=True)
        else:
            st.info("No records found.")