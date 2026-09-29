import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
from hashlib import pbkdf2_hmac
from secrets import token_hex

st.set_page_config(page_title="Air Quality Index")

# ---------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    return conn

# ---------------------------------------------------------------------
# Password hashing
#
# FIX: the original used bare sha256(password) with no salt. That means
# two users with the same password get the exact same hash, which makes
# a leaked database trivial to crack with a rainbow table. This version
# uses PBKDF2 with a random per-user salt and 200,000 iterations, which
# is a standard, safe way to store passwords.
# ---------------------------------------------------------------------

PBKDF2_ITERATIONS = 200_000

def hash_password(password, salt=None):
    if salt is None:
        salt = token_hex(16)
    derived = pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return salt, derived.hex()

# Add a New User to the Database
def add_user(conn, email, username, name, password):
    salt, password_hash = hash_password(password)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, username, name, salt, password_hash) VALUES (?, ?, ?, ?, ?)",
            (email, username, name, salt, password_hash)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        # FIX: the original closed `conn` here — the same connection the
        # rest of the app reuses for logins. That meant every login
        # attempt after any signup failed with "Cannot operate on a
        # closed database". Close only the cursor, not the connection.
        cursor.close()

# Authenticate a User
def authenticate_user(conn, email, password):
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT name, email, salt, password_hash FROM users WHERE email = ?",
            (email,)
        )
        result = cursor.fetchone()
        if not result:
            return None
        name, email, salt, stored_hash = result
        _, candidate_hash = hash_password(password, salt=salt)
        if candidate_hash == stored_hash:
            return {"name": name, "email": email}
        return None
    finally:
        cursor.close()

# Initialize the database
conn = init_db()

# Content - Description
def description():
    st.subheader(":black_nib: About the Project", anchor=False)
    st.write(
        """
        The "Air Quality Index Visualization" project is designed to 
        provide an intuitive and interactive tool for monitoring and 
        analyzing air quality data across various Indian Cities. The 
        primary objective is to enable users to analyze air quality 
        trends over time, track changes, and compare AQI levels 
        regionally, empowering users to make informed decisions about 
        environmental health. By providing actionable insights through 
        clear visualizations, the application aims to raise awareness and 
        assist in environmental decision-making.
        """
    )
    st.subheader(":zap: Significance", anchor=False)
    st.write(
        """
        \n**Promoting Awareness:** Helping individuals understand pollution levels and their impact.
        \n**Supporting Decision-Making:** Empowering policymakers and urban planners with data-driven insights.
        \n**Encouraging Action:** Driving initiatives for pollution control and healthier environments.
        """
    )
    st.subheader("👨‍💻 Who can Use?", anchor=False)
    st.write(
        """
        \n**Environmental Analysts**: To assess and interpret AQI data.
        \n**Policymakers and Urban Planners**: For formulating effective strategies.
        \n**Public Health Advocates**: To address health concerns related to air pollution.
        \n**General Public**: To stay informed and take protective measures when needed.
        """
    )
    st.subheader(":chart: Potential Use Cases", anchor=False)
    st.write(
        """
        \n**Urban Planning**: Assisting in the identification of high-pollution areas for targeted interventions.
        \n**Environmental Research**: Providing historical AQI data for trend analysis and forecasting.
        \n**Public Health Campaigns**: Offering visual aids to educate communities about air quality risks.
        \n**Policy Formation**: Guiding government policies on emissions control and sustainability initiatives.
        """
    )

# Content - Dashboard 
def dashboard():
    powerbi_embed_url = "https://app.fabric.microsoft.com/reportEmbed?reportId=a777c063-c287-48b1-8d07-af0746897f80&autoAuth=true&ctid=29d6b2c1-5a07-49dc-ad3b-a84fe545e6d9"
    st.subheader(":bar_chart: Dashboard")
    components.html(
        f"""
        <iframe 
            title="AQI Visualization - Home"
            width="875" 
            height="550" 
            src="{powerbi_embed_url}" 
            frameborder="0" 
            allowFullScreen="true">
        </iframe>
        """,
        width=850, height=600,
    )

# Display Selectbox for Login and Sign Up 
st.title("Air Quality Index Visualization :night_with_stars:")
st.write("---")

if 'authentication_status' not in st.session_state or not st.session_state['authentication_status']:
    option = st.selectbox('Choose an action:', ('Login', 'Sign Up'))

    if option == 'Sign Up':
        st.subheader("Create a New Account")
        with st.form("register_form"):
            new_email = st.text_input("Email")
            new_username = st.text_input("Username")
            new_name = st.text_input("Full Name")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Sign Up")

        if submitted:
            if new_password != confirm_password:
                st.error("Passwords do not match!")
            else:
                success = add_user(conn, new_email, new_username, new_name, new_password)
                if success:
                    st.success(f"User {new_name} successfully registered! Please Login to get started ")
                else:
                    st.error("Email already exists. Please try a different E-mail id.")

    elif option == 'Login':
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            user_data = authenticate_user(conn, email, password)
            if user_data:
                st.session_state['authentication_status'] = True
                st.session_state['name'] = user_data['name']
                st.session_state['email'] = user_data['email']
                st.success(f"{st.session_state['name']}, You are successfully logged in!")
            else:
                st.error("Invalid email or password.")

# After successful login, display website content
if 'authentication_status' in st.session_state and st.session_state['authentication_status']:
    description()
    st.write("---")
    dashboard()
    data = pd.read_csv("aqi_data.csv")
    left, middle, right = st.columns(3)
    left.link_button("Expand Dashboard", 
                   "https://app.fabric.microsoft.com/reportEmbed?reportId=a777c063-c287-48b1-8d07-af0746897f80&autoAuth=true&ctid=29d6b2c1-5a07-49dc-ad3b-a84fe545e6d9", 
                   icon=":material/zoom_out_map:")

    with open("AQI_Dashboard.pdf", "rb") as file1:
        middle.download_button(label="Download as pdf",
                        data=file1,
                        file_name="AQI_Dashboard.pdf",
                        mime="application/pdf",
                        icon=":material/analytics:")

    with open("AQI_Visualization.pbix", "rb") as file2:
        right.download_button(label="Download as pbix",
                        data=file2,
                        file_name="AQI_Visualization.pbix",
                        mime="application/octet-stream",
                        icon=":material/analytics:")

    st.write("---")

    # Filters to Download the dataset
    st.subheader("🔍Filters")
    data["Year"] = pd.to_datetime(data["DATE"], format="%d-%m-%Y").dt.year
    city, year, aqi = st.columns(3)
    city_filter = city.multiselect(label="Select City", options=data["CITY"].unique())
    year_filter = year.multiselect(label="Select Year", options=data["Year"].unique())
    aqi_filter = aqi.multiselect(label="Select AQI", options=data["AQI"].unique())
    if city_filter or year_filter or aqi_filter:
        filtered_data = data[
            (data["CITY"].isin(city_filter) if city_filter else True) &
            (data["Year"].isin(year_filter) if year_filter else True) &
            (data["AQI"].isin(aqi_filter) if aqi_filter else True)
        ]
    else:
        filtered_data = data
    filtered_data = filtered_data.drop(columns=["Year"])
    st.dataframe(filtered_data, hide_index=True, width=800, use_container_width=True)

    # Logout from the app
    if st.button("Logout"):
        st.session_state['authentication_status'] = False
        st.rerun()
