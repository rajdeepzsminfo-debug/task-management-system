import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh
from streamlit_gsheets import GSheetsConnection
import os
import pytz

# ==========================================
# 1. DATABASE SETUP & HELPERS (GOOGLE SHEETS)
# ==========================================
ADMIN_PASSWORD = "admin123" 

# Replace these with your actual Google Sheet URLs
TASKS_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_TASKS_SHEET_URL"
USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_USERS_SHEET_URL"
COMPANIES_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_COMPANIES_SHEET_URL"

# Establishing Connection
conn = st.connection("gsheets", type=GSheetsConnection)

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

def get_now_ist():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)

# --- DATABASE HELPERS REDEFINED FOR GSHEETS ---

def get_companies():
    try:
        df = conn.read(spreadsheet=COMPANIES_SHEET_URL, ttl="0")
        if df.empty:
            raise ValueError
        return df
    except:
        df = pd.DataFrame({"Company Name": COMPANY_LIST, "Hourly Rate": [0.0]*len(COMPANY_LIST)})
        conn.update(spreadsheet=COMPANIES_SHEET_URL, data=df)
        return df

def save_companies(df):
    conn.update(spreadsheet=COMPANIES_SHEET_URL, data=df)

def get_tasks(): 
    df = conn.read(spreadsheet=TASKS_SHEET_URL, ttl="0").fillna("N/A").astype(str)
    if "Remarks" not in df.columns:
        df["Remarks"] = ""
    df['Assign_DT'] = pd.to_datetime(df['Assign_Time'], errors='coerce')
    return df

def save_tasks(df): 
    if 'Assign_DT' in df.columns: 
        df = df.drop(columns=['Assign_DT'])
    conn.update(spreadsheet=TASKS_SHEET_URL, data=df)

def get_users(): 
    return conn.read(spreadsheet=USERS_SHEET_URL, ttl="0").astype(str)

def save_users(df): 
    conn.update(spreadsheet=USERS_SHEET_URL, data=df)

def to_dt(str_val):
    if str_val == "N/A" or not isinstance(str_val, str) or str_val == "":
        return None
    try:
        return datetime.strptime(str_val, "%Y-%m-%d %I:%M:%S %p")
    except:
        try:
            return datetime.strptime(str_val, "%Y-%m-%d %H:%M:%S")
        except:
            return None


# ==========================================
# RECURRING TASK LOGIC
# ==========================================
def handle_recurring_tasks(finished_row):
    if finished_row['Frequency'] == "Once":
        return
    
    try:
        current_sched = datetime.strptime(finished_row['Scheduled_Date'], "%Y-%m-%d")
    except:
        return 

    if finished_row['Frequency'] == "Daily":
        next_date = current_sched + timedelta(days=1)
    elif finished_row['Frequency'] == "Weekly":
        next_date = current_sched + timedelta(weeks=1)
    elif finished_row['Frequency'] == "Semi-Monthly":
        next_date = current_sched + timedelta(days=15)
    elif finished_row['Frequency'] == "Monthly":
        next_date = current_sched + timedelta(days=30)
    
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
    
    updated_df = pd.concat([df, pd.DataFrame([new_task])], ignore_index=True)
    save_tasks(updated_df)

# ==========================================
# 2. LOGIN PAGE VS DASHBOARD CONTROL
# ==========================================
st.set_page_config(page_title="Corp-Task Pro", layout="wide")

if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None

if st.session_state.role is None:
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
    st.stop() 

# ==========================================
# 3. DASHBOARD UI
# ==========================================
st.sidebar.title(f"Logged in as: {st.session_state.role}")
if st.session_state.user:
    st.sidebar.write(f"User: {st.session_state.user}")

if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.session_state.user = None
    st.rerun()

if st.session_state.role == "Admin":
    menu = st.sidebar.radio("Main Menu", ["Dashboard", "Reports & Overrides", "User Management", "Company Management"])
    
    if menu == "Dashboard":
        st.title("👨‍💼 Task Assignment")
        users_df = get_users()
        if not users_df.empty:
            u_display_list = users_df.apply(lambda x: f"{x['Username']} ({x.get('Department', 'N/A')})", axis=1).tolist()
            user_map = dict(zip(u_display_list, users_df['Username']))
        else:
            u_display_list = ["No Users Available"]
            user_map = {}

        msg_spot = st.empty()
        with st.form("task_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: selected_display = st.selectbox("Assign To Employee", u_display_list)
            with c2: 
                comp_db = get_companies()
                comp = st.selectbox("Company Name", comp_db["Company Name"].tolist())
            with c3: mins = st.number_input("Minutes Allowed", min_value=1, value=15)
            
            c4, c5 = st.columns(2)
            with c4: sched_date = st.date_input("Schedule Date", get_now_ist())
            with c5: freq = st.selectbox("Repeat Frequency", ["Once", "Daily", "Weekly", "Semi-Monthly", "Monthly"])

            tsk = st.text_area("Task Description")
            if st.form_submit_button("🚀 SCHEDULE / ASSIGN TASK"):
                if not u_display_list or u_display_list == ["No Users Available"]:
                    st.error("Cannot assign task: No employees found.")
                elif tsk.strip() == "":
                    st.error("Please enter a task description.")
                else:
                    emp = user_map.get(selected_display, selected_display)
                    df = get_tasks()
                    new_row = {
                        "Employee": emp, "Company": comp, "Task": tsk, "Limit_Mins": str(mins), 
                        "Assign_Time": get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p"),
                        "Start_Time": "Waiting", "Deadline": "N/A", "Submit_Time": "N/A", 
                        "Time_Variance": "N/A", "Status": "Pending", "Flag": "⚪", "Pause_Start": "N/A",
                        "Scheduled_Date": sched_date.strftime("%Y-%m-%d"), "Frequency": freq,
                        "Total_Paused_Mins": 0, "Pause_Count": 0, "Remarks": ""
                    }
                    save_tasks(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                    st.toast(f"Task scheduled for {emp}!", icon='✅')
                    msg_spot.success(f"🎉 SUCCESS: Task for {comp} scheduled for {sched_date}!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()

# ... [Continuation of Script] ...

elif st.session_state.role == "Employee":
    tab1, tab2 = st.tabs(["🚀 Active Tasks", "📜 My Reports"])
    
    with tab1:
        st.title(f"👷 {st.session_state.user}'s Workspace")
        df = get_tasks()
        today_str = get_now_ist().strftime("%Y-%m-%d")
        
        active_tasks = df[(df["Employee"] == st.session_state.user) & (df["Status"] != "Finished") & (df["Scheduled_Date"] <= today_str)]
        
        if active_tasks.empty:
            st.info("No active tasks for today.")
        
        for idx, row in active_tasks.iterrows():
            with st.container(border=True):
                st.subheader(f"🏢 {row['Company']}")
                st.write(f"**Task:** {row['Task']}")
        
                if row["Status"] == "Pending":
                    if st.button("▶️ ACCEPT & START", key=f"s_{idx}"):
                        now = get_now_ist()
                        mins_val = int(float(str(row["Limit_Mins"])))
                        deadline = now + timedelta(minutes=mins_val)
                        df.at[idx, "Start_Time"] = now.strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Deadline"] = deadline.strftime("%Y-%m-%d %I:%M:%S %p")
                        df.at[idx, "Status"] = "Running"
                        save_tasks(df)
                        st.rerun()

                elif row["Status"] == "Running":
                    # (Implementation of Timer, Pause, and Finish logic same as CSV version)
                    # Use save_tasks(df) and st.rerun() after state changes
                    pass # Keep original logic here

    with tab2:
        # History logic using get_tasks()
        pass

# Final call to ensure script completion
if __name__ == "__main__":
    pass
