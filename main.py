import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_gsheets import GSheetsConnection
import pytz
import io

# ==========================================
# 1. DATABASE SETUP & HELPERS
# ==========================================
ADMIN_PASSWORD = "admin123" 

# IMPORTANT: Replace these with your ACTUAL Google Sheet URLs
TASKS_SHEET_URL = "REPLACE_WITH_YOUR_ACTUAL_TASKS_SHEET_URL"
USERS_SHEET_URL = "REPLACE_WITH_YOUR_ACTUAL_USERS_SHEET_URL"
COMPANIES_SHEET_URL = "REPLACE_WITH_YOUR_ACTUAL_COMPANIES_SHEET_URL"

# Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Full company list provided in source
COMPANY_LIST = ["Pearl Hospitality LLC", "Shri Guru Om Inc", "276 Old Country Road LLC", "Impact Wireless LLC", "Deluxe Services USA Inc", "SM Auto Tech Inc", "Venus Auto Parts Inc", "Venus Realty Group LLC", "Krishs Indian Bistro Corp", "Lisas Crown Fried Chicken", "Bns Industries Inc", "S&S Sports Inc", "Gip Industries Inc", "Hottest Footwear Com Inc", "Hicksville Chaap LLC", "Giapreet LLC", "Giorgio West LLC", "Ikta Lifestyle LLC", "Singh Management LLC", "As Sports 46 Inc", "Scratch Sports Inc", "Ss Coffee Farmingdale Inc", "Mad Kicks LLC", "BVS Inc", "Fresh Food Group LLC", "Royal Blue Property 15 LLC", "Royal Blue Property 7 LLC", "905 Waverly Realty LLC", "Gadgets LLC", "Zupple LLC", "Guru Nanak'S Kitchen Inc.", "145 Main Patterson LLC", "229 Broadhollow Realty LLC", "Amritapriya LLC", "101 Chaap LLC", "741 Motor Cars LLC", "Crimson Nova Inc", "Silver Ember Inc", "Velvet Horizon Inc", "1467 Annandale Realty LLC", "Air America Drones LLC", "Dab Clean LLC", "Pgi Technologies LLC", "Safeguard Singh Management", "Realty G", "Sidanas Inc", "749 Farmingdale Realty LLC", "Royal Blue Property 19 LLC", "19962 Franz Rd Realty LLC", "905 Land Realty LLC", "Hillside Chaap LLC", "65 Mahan Realty LLC", "Starbucks", "S&S Sports Inc (Ny)", "S&S Sports Inc (Ny) (Whoesale)", "Cafe Di Mondo Inc", "Francescos Cafe & BakeryInc", "Moonbucks Inc", "P&F Bakers Inc", "South Broadway Realty Enterprises", "AGRO BUSINEES GROUP", "The Barkary Bakery Corp", "The Barkary Corp", "The Barking Bakery Corp", "Cafe Di Sole Inc", "Grand Cafe Bakery Inc", "Farmington Hari LLC", "New Shs Properties LLC", "Shs Properties Inc", "Sky Hari LLC", "St Hari Apartments LLC", "St Hari Properties Inc", "Us Hari Properties Inc", "Shs Auto Parts Inc", "831 Building LLC", "Caprio & Caprio LLC", "NI Mobile Inc", "Avis Property LLC", "Sugar Cell Inc", "Avin Builders Inc", "Dove Street LLC", "New Land Estate Inc", "Om Paving Corp", "New York Cardiovascular Care PC", "TRJRes Inc", "LI Investors LLC", "TRJ Associates Group LLC", "Tammy Management Inc", "Blue Coral NY Inc", "Pooja Fashion & Style Inc", "Pooja Stitch Craft Inc", "609 Fulton Pediatrics PC", "Fulton Avenue Realty LLC", "Charan Electrical Enterprises", "Minesh Properties Inc", "New Generation Development LLC", "Astoria Delancy Hotel Corp", "Central NY Hospitality LLC", "Crown City Hospitality LLC", "Anastasio Landscaping Inc", "Anshima Homes LLC", "Horizon Star Services LLC", "Eesha Inc", "Addvanced Carpentry Inc", "Deep Distributors Greator Ny Inc", "Golden Touch Ice Cream Inc", "Guru Fashions Inc", "John Auto Center Inc", "M&M Builders & Developers Inc", "Om Paving Inc", "Paramount Wireless LLC", "SHS Auto Parts Inc", "Andrew Maintance Inc", "4Th Avenue Real Estate Inc", "7508 Chicken Corp", "Fourth Avenue Merchant Inc", "Futurewise Insurance Brokerage Corp", "Liu Electric LLC", "Royal Star Insurance Brokerage Corp", "Scott Group Insurance Brokerage Corp", "Futurewise Business Inc", "Total Wireless Of New England Inc", "Brewer Hotel LLC", "Pinnacle Mobility LLC", "Pinnacle Mobility Retail Inc", "Stellar Wireless Retail Ny Inc", "Superior Victory Hotel LLC", "Cafe Dolce Vita Corp", "Green Keeper Landscaping LLC", "Gyan Malhotra LLC", "Kama Hospitality Inc", "Vita Food Corp", "Frienldy Star Fuel Inc", "Cute Cuts Inc", "Home Improvment By George Corp", "Jackson Plumbing & Hvac Supplies Corp", "Prime Construction Usa Inc", "Belleville Oil Inc", "Jamaica Fuel Inc", "Jersey Mart Inc", "Ks Fuel Inc", "Remsen Fuel Inc", "Rt Fuel Inc", "Tatla Gas Inc", "Tatla Petroleum Inc", "Wallington Gas Inc", "Yuvi Gas Inc", "Sai Express Inc", "On Balance Search Consultants LLC", "Minesh Properties LLC", "Hudson View Films & Tv Inc", "Sai Restaurant Enterprise Inc", "The Pearl Hospitality LLC", "Avleen Food Group LLC", "MG Elite Group LLC", "Hickville Jewelry Traders Inc", "Advantage Pro Training Inc", "AG Parts USA Inc", "Gizmotech LLC", "Js Sethi Inc", "Shree BhadraKali Inc", "Singh Sethi Inc", "Glamour Usa Inc", "Indian Street Food LLC", "Law Office Of Abe George", "Ramos Consulting Inc", "Reliance Fashion Group Inc", "Shawarma Paradise LLC", "Superride Suspension Inc", "Rajdeep Enterprises LLC", "Good Faith Restaurant Incorporated", "A & P Auto Body & Repair Inc", "Azhar Construction Inc", "120 Osborn Holding LLC", "BWI 827 LLC", "Sunraise Equity Group LLC", "Thatford Lodging LLC", "Best Management Solutions Inc", "Xtreme Realty Holding LLC", "Xtreme Solutioons Services Corp", "Osborn Operating Hospitality Corp", "Thatford Operating Hospitality Corp", "ABM Electric Inc", "Blue Falcon Realty & Management Corp", "Jot Realty Inc", "Maryland Hospitality LLC", "BWI-NY Builders LLC", "Jackson Plumbing & HVAC Supplies Co", "144 Investors LLC", "165 Investors LLC", "Umbrella Investors LLC", "262 Investors LLC", "33 Investors LLC", "38th Avenue Hotels LLC", "39th Avenue Hospitality LLC", "Deep Distibutors Greater NY Inc", "Green Ready Mixx LLC", "78 Investors LLC", "Supreme Builders Inc", "Hunts Point Petroleum LLC", "Dala Builders Corp", "3290 Realty LLC", "Sunny Developers LLC", "Anthonys Insulation Corp", "Dynamic Capital LLC", "261-09 Hillside Avenue LLC", "261-11 Hillside Avenue LLC", "A And N Hospitality LLC", "Langdale Realty LLC", "Braddock Investors LLC", "Fourth Avenue Merchants Inc", "LIU Electric LLC", "Glen Oaks Liquor Inc", "Dynamic Builders Us Inc", "Dynamic Cellular Inc", "LI Investors Group", "TRJ Associates Group", "TRJ Developers", "Direct Source Solutions", "10 Dix Hills LLC", "11 Bethpage LLC 47", "10 East Isllip LLC", "10 Westbury LLC", "10 East Meadow LLC", "1073 Westminster LLC", "10 Huntington LLC", "68 Harrison LLC New", "Balen CGA", "10 Floral Ave LLC", "10 Lakeville Drive LLC", "1010 Jerusalem Ave LLC", "10 Miami NY LLC", "68 Dryden ST LLC", "118 Ryder Avenue LLC", "28 Parkway BLVD LLC", "460 Jefferson LLC", "76 Abey LLC", "120 - 06 135th ST LLC", "10 N Babylon - 160 Kime", "36 Sycamore LLC", "Trj Hospitality Group Inc", "Dress Your Home LLC", "26 Parkway LLC", "JR Property Group LLC", "Jordan 3 LLC", "Hicks 37 LLC", "141 MYERS AVENUE LLC", "Bay Shore 10 LLC", "Hunter 8 LLC", "Bay 39 LLC", "Brooker 37 LLC", "Central 10 LLC", "Amityville Gn LLC", "Coram Westfield LLC", "Central 12 LLC", "Central 14 LLC", "Central 13 LLC", "Islip 10 LLC", "Copiague 10 LLC", "Amityville 10 LLC", "Law office of Abe George, PC", "TVM Group LLC", "IL Fornaretto II LLC", "IL Fornaretto III LLC", "Les Fine Wine & Spirit LLC", "Universal Hotel LLC", "Guru Fashion Inc", "Sai Restaurant Enterprises Inc", "Sai Enterprises Inc", "Milos & Milson Inc", "Juno Development LLC", "Insurance Professional Agency Inc", "Delphis Equipment and Trucking Inc", "Insurance Pros Agency Inc (Florida)", "Hudson View Film & TV Inc", "Home Improvement By George Corp", "Ramos Consulting Services Inc", "Cute Cuts 2 Inc", "Deluxe Service USA Inc", "148 Meriline Ave LLC", "2004 Caddo Street LLC", "United Group Retail LLC", "World Realty LLC", "Lisa's Crown Fried Chicken Inc", "Krish's Indian Bistro Corp", "NBS Distribuiton LLC", "On Balance Search Consultant LLC", "NS Consulting Group LLC", "NS Hospitality LLC", "NS Realty 294 LLC", "Metro Management Solutions NY LLC", "Pinnacle Mobility NY Inc", "Sabharwal Properties 2 LLC", "Star Connect Group LLC", "Total Wireless of FL Inc", "NS Mobility Inc", "Tottallink Florida Inc", "Mobile USA Inc", "Singhsethi Inc(Noor)", "Kama Hospitality LLC", "23 Fire Place LLC", "Cinnamon Kitchen LLC", "Dawn Staffing Solution Inc", "Garnet Shipping Inc", "Carlux Limo Inc", "Carlux Limo Worldwide Inc", "Venus 1919 Deer Park Ave LLC", "Entreprenaari LLC", "Kayaan Services Inc", "Kriti Services Inc", "Aurum By Teesha", "US Executive Limo Inc", "Preet Construction Group LTD", "Bala Fitness of Jerome", "Bala Fitness of Third Avenue LLC", "New York Masonry & Renovation Inc", "Troy Installer Inc", "Green World Distribution Inc", "Axis My America Inc", "Virk US Limo Inc", "Harsh Multani Limo Inc", "Online Shoppers World LLC", "ConnectQuo LLC", "Fatma Shamsi Inc", "Kaftech GI Construction Inc", "Kafetech Inc", "Jewel Junction Inc", "JCR Fitness LLC", "KNK Distributors Inc", "Sunlab Contractor Inc", "United City Contracting Inc", "Empyrean Global Limited Company", "A&P Auto Body & Repair Inc", "Andrew Maintenance Inc", "Arvat Services Inc", "Brand Sales Network Inc", "Swami Contracting Inc", "Hillside Avenue 23504 LLC", "Bony Car Services Corp", "Arkon Builders LLC", "Divine Craft By Himalayas Inc", "Accounting Tax and Business Solution Inc", "Deepreet LLC", "IT Palace", "Ezetop Inc", "BAC Express Incorporated", "Farmingdale Partner LLC", "At Play Amusements Inc", "Farmingdale Food Court Inc", "Maribella LLC", "Oak Knowledge LLC", "Nest Group LLC", "Apollo Telecom Inc", "Ascan Street Inc", "A&H Equity Partners Inc", "Turingtech LLC", "Just Code Inc", "Mila Ventures Corp", "MY Own Brew LLC", "Pelican Restaurant Inc", "Voguish Couture Inc", "Blissful Aesthetics Inc", "Profusion Solar LLC", "Green Keepar Landscaping LLC", "Eric Harris Art Inc", "Bulldozer Hospitality Group Inc", "Rockwell 77 LLC", "Prime Ten LLC", "Prime Twelve LLC", "American Standard Hospitality Group", "Imani Express Inc", "Rock 51 LLC", "Prime 107 Inc", "Bulldozer Nyc LLC", "Hari Dev Inc", "Hari Ram Inc", "Coco & Maui Corp", "Hare Krishna Wappingers LLC", "Kunj Bihari LLC", "A&N Food Group LLC", "Good Faith Restaurants Inc", "Loroda LLC", "Bruzz LLC", "Myra Group Inc", "All Season Contractors Corp", "Restore & Elevate Nutrition Corp", "Superior Van Wyck Hotel LLC", "Horizon Star Fuel Inc", "New Generation Astoria LLC", "Get My Rugs LLC", "Kika Home Collections Inc", "BBH Homes LLC", "1028 Capital LLC", "Jackson Jewelry Group Inc", "Hicksville Jewelry Traders Inc"] [cite: 1-18]

def get_now_ist():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None) [cite: 18]

# --- G-SHEETS DATABASE ADAPTERS ---

def get_companies():
    try:
        df = conn.read(spreadsheet=COMPANIES_SHEET_URL, ttl="0")
        if df.empty: raise ValueError
        return df
    except:
        df = pd.DataFrame({"Company Name": COMPANY_LIST, "Hourly Rate": [0.0]*len(COMPANY_LIST)})
        # This will create initial data if sheet is empty
        conn.update(spreadsheet=COMPANIES_SHEET_URL, data=df)
        return df

def get_tasks(): 
    try:
        df = conn.read(spreadsheet=TASKS_SHEET_URL, ttl="0").fillna("N/A").astype(str)
        if "Remarks" not in df.columns: df["Remarks"] = ""
        df['Assign_DT'] = pd.to_datetime(df['Assign_Time'], errors='coerce')
        return df
    except:
        cols = ["Employee", "Company", "Task", "Limit_Mins", "Assign_Time", "Start_Time", 
                "Deadline", "Submit_Time", "Time_Variance", "Status", "Flag", "Pause_Start", 
                "Scheduled_Date", "Frequency", "Total_Paused_Mins", "Pause_Count", "Remarks"]
        return pd.DataFrame(columns=cols)

def save_tasks(df): 
    if 'Assign_DT' in df.columns: df = df.drop(columns=['Assign_DT'])
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
            st.metric("Time Overdue", f"{abs(secs)//60}m {abs(secs)%60}s") [cite: 22]

# ==========================================
# 2. LOGIN & AUTH
# ==========================================
st.set_page_config(page_title="Corp-Task Pro", layout="wide")

if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None

if st.session_state.role is None:
    st.title("🚩 ZSM Task Control Center") [cite: 27-28]
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Admin Login")
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login as Admin"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.role = "Admin"; st.rerun()
            else: st.error("Invalid Admin Password")
    with c2:
        st.subheader("Employee Login")
        u_name = st.text_input("Username").strip()
        u_pwd = st.text_input("Password", type="password").strip()
        if st.button("Login as Employee"):
            users = get_users()
            match = users[(users['Username'] == u_name) & (users['Password'] == u_pwd)]
            if not match.empty:
                st.session_state.role = "Employee"; st.session_state.user = u_name; st.rerun()
            else: st.error("Invalid Credentials")
    st.stop() 

# --- SIDEBAR LOGOUT ---
if st.sidebar.button("Logout"):
    st.session_state.role = None; st.session_state.user = None; st.rerun()

# ==========================================
# 3. ADMIN DASHBOARD
# ==========================================
if st.session_state.role == "Admin":
    menu = st.sidebar.radio("Menu", ["Dashboard", "Reports", "Users", "Companies"])
    
    if menu == "Dashboard":
        st.title("👨‍💼 Task Assignment") [cite: 32]
        u_df = get_users()
        u_list = u_df.apply(lambda x: f"{x['Username']} ({x.get('Department', 'N/A')})", axis=1).tolist() if not u_df.empty else ["No Users"]
        
        with st.form("assign_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: emp_sel = st.selectbox("Assign To", u_list)
            with c2: 
                comp_db = get_companies()
                comp_sel = st.selectbox("Company", comp_db["Company Name"].tolist())
            with c3: mins = st.number_input("Minutes", 1, 1440, 15)
            
            task_desc = st.text_area("Task Description")
            # FIX: Adding the required submit button
            if st.form_submit_button("🚀 ASSIGN TASK"):
                df = get_tasks()
                new_row = {
                    "Employee": emp_sel.split(" (")[0], "Company": comp_sel, "Task": task_desc,
                    "Limit_Mins": str(mins), "Assign_Time": get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p"),
                    "Status": "Pending", "Scheduled_Date": get_now_ist().strftime("%Y-%m-%d"),
                    "Frequency": "Once", "Total_Paused_Mins": 0, "Pause_Count": 0, "Flag": "⚪"
                }
                save_tasks(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                st.success("Task Assigned!"); time.sleep(1); st.rerun()

    elif menu == "Reports":
        st.title("📊 Global Reports")
        df = get_tasks()
        st.dataframe(df, use_container_width=True) [cite: 44]

    elif menu == "Users":
        st.title("👥 User Management")
        u_df = get_users()
        with st.form("add_user_form"):
            nu, np = st.text_input("New Username"), st.text_input("New Password")
            dept = st.selectbox("Dept", ["Tax", "Audit", "Payroll", "Admin"])
            if st.form_submit_button("Add User"):
                save_users(pd.concat([u_df, pd.DataFrame([{"Username": nu, "Password": np, "Department": dept}])], ignore_index=True))
                st.rerun()
        st.dataframe(u_df, use_container_width=True)

    elif menu == "Companies":
        st.title("🏢 Company Management")
        c_df = get_companies()
        st.dataframe(c_df, use_container_width=True) [cite: 85]

# ==========================================
# 4. EMPLOYEE VIEW
# ==========================================
elif st.session_state.role == "Employee":
    st.title(f"👷 {st.session_state.user}'s Workspace") [cite: 92]
    df = get_tasks()
    my_tasks = df[(df["Employee"] == st.session_state.user) & (df["Status"] != "Finished")]
    
    for idx, row in my_tasks.iterrows():
        with st.container(border=True):
            st.subheader(f"🏢 {row['Company']}")
            st.write(f"Task: {row['Task']}")
            
            if row["Status"] == "Pending" and st.button("▶️ START", key=f"s_{idx}"):
                df.at[idx, "Start_Time"] = get_now_ist().strftime("%Y-%m-%d %I:%M:%S %p")
                df.at[idx, "Deadline"] = (get_now_ist() + timedelta(minutes=int(float(row["Limit_Mins"])))).strftime("%Y-%m-%d %I:%M:%S %p")
                df.at[idx, "Status"] = "Running"
                save_tasks(df); st.rerun()
            
           # ==========================================
# 3. ADMIN: REPORTS, USERS, & COMPANIES (CONTINUED)
# ==========================================

elif menu == "Reports & Overrides":
    st.title("📊 Global Performance Reports & Overrides")
    df = get_tasks()
    
    # Filtering Section
    f1, f2, f3 = st.columns(3)
    with f1:
        c_filt = st.multiselect("Filter by Company", COMPANY_LIST)
    with f2:
        u_df = get_users()
        e_filt = st.multiselect("Filter by Employee", u_df['Username'].tolist() if not u_df.empty else [])
    with f3:
        s_filt = st.multiselect("Filter by Status", ["Pending", "Running", "Paused", "Finished"])
    
    if c_filt: df = df[df['Company'].isin(c_filt)]
    if e_filt: df = df[df['Employee'].isin(e_filt)]
    if s_filt: df = df[df['Status'].isin(s_filt)]

    if not df.empty:
        st.write("---")
        # Excel Export Logic
        buffer = io.BytesIO()
        export_df = df.copy()
        if 'Assign_DT' in export_df.columns:
            export_df = export_df.drop(columns=['Assign_DT'])
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='TaskReport')
        
        st.download_button(
            label="📥 Download Report as Excel",
            data=buffer.getvalue(),
            file_name=f"Task_Report_{get_now_ist().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # Displaying and Managing Tasks
        st.write("---")
        for idx, row in df.iterrows():
            with st.expander(f"Task for {row['Company']} by {row['Employee']} ({row['Status']})"):
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.write(f"**Description:** {row['Task']}")
                c2.write(f"**Limit:** {row['Limit_Mins']} mins")
                c2.write(f"**Flag:** {row.get('Flag', '⚪')}")
                
                if c3.button("🗑️ Delete Task", key=f"admin_del_{idx}"):
                    full_tasks = get_tasks().drop(idx)
                    save_tasks(full_tasks)
                    st.toast("Task Deleted")
                    st.rerun()

elif menu == "User Management":
    st.title("👥 User Management")
    u_df = get_users()
    
    with st.form("add_user_form", clear_on_submit=True):
        st.subheader("Add New Employee")
        c1, c2, c3 = st.columns(3)
        nu = c1.text_input("New Username")
        np = c2.text_input("New Password", type="password")
        dept = c3.selectbox("Department", ["Accountant", "Tax", "Audit", "Payroll", "Admin Support", "Notices", "Sales Tax", "Book Keeping"])
        if st.form_submit_button("➕ Save User"):
            if nu and np:
                if nu in u_df['Username'].values:
                    st.error("User already exists!")
                else:
                    new_u = pd.DataFrame([{"Username": nu, "Password": np, "Department": dept}])
                    save_users(pd.concat([u_df, new_u], ignore_index=True))
                    st.success(f"Added {nu}!")
                    st.rerun()

    st.subheader("Current Employees")
    st.dataframe(u_df, use_container_width=True)
    for i, r in u_df.iterrows():
        if st.button(f"🗑️ Delete {r['Username']}", key=f"del_u_{i}"):
            save_users(u_df.drop(i))
            st.rerun()

elif menu == "Company Management":
    st.title("🏢 Company Management")
    comp_df = get_companies()
    
    with st.form("add_company_form", clear_on_submit=True):
        c_name = st.text_input("Company Name")
        c_rate = st.number_input("Hourly Billing Rate ($)", min_value=0.0)
        if st.form_submit_button("➕ Add Company"):
            new_row = pd.DataFrame([{"Company Name": c_name.strip(), "Hourly Rate": c_rate}])
            save_companies(pd.concat([comp_df, new_row], ignore_index=True))
            st.success("Company Added!")
            st.rerun()
    
    st.dataframe(comp_df, use_container_width=True)

# ==========================================
# 4. EMPLOYEE VIEW: HISTORY (TAB 2)
# ==========================================

elif st.session_state.role == "Employee":
# The Active Tasks logic was in Part 1. Here is the Work History logic.
# Note: Ensure you have the 'tabs' defined as per Part 1.
with tab2:
    st.title("📜 My Work History")
    df = get_tasks()
    my_history = df[df["Employee"] == st.session_state.user]
    
    rep_type = st.radio("View Period", ["Daily (Today)", "Monthly (30 Days)"], horizontal=True)
    today_start = get_now_ist().replace(hour=0, minute=0, second=0)
    since_date = today_start if "Daily" in rep_type else (get_now_ist() - timedelta(days=30))
    
    report_df = my_history[my_history["Assign_DT"] >= since_date].copy()
    
    if not report_df.empty:
        def get_work_hours(r):
            s, f = to_dt(r['Start_Time']), to_dt(r['Submit_Time'])
            return round((f - s).total_seconds() / 3600, 2) if s and f else 0.0

        report_df['Hours'] = report_df.apply(get_work_hours, axis=1)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Hours", f"{report_df['Hours'].sum():.2f} hrs")
        c2.metric("Tasks Done", len(report_df[report_df["Status"]=="Finished"]))
        
        st.dataframe(report_df[["Company", "Task", "Assign_Time", "Submit_Time", "Hours", "Flag", "Remarks"]], use_container_width=True)
    else:
        st.info("No records found for this period.")

# End of Script
