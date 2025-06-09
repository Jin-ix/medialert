import streamlit as st
from streamlit_lottie import st_lottie
import requests
from twilio.rest import Client
import bcrypt
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Database Setup ---
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)

engine = create_engine("sqlite:///users.db")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# --- Twilio Setup ---
ACCOUNT_SID = "your_account_sid"
AUTH_TOKEN = "your_auth_token"
TWILIO_NUMBER = "+1234567890"
twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)

# --- Utils ---
def load_lottie_url(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def send_sms(to_number, message):
    message = twilio_client.messages.create(
        body=message,
        from_=TWILIO_NUMBER,
        to=to_number
    )
    return message.sid

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode(), password_hash)

def get_user(username):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    return user

def create_user(username, password):
    db = SessionLocal()
    password_hash = hash_password(password)
    user = User(username=username, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.close()

# --- Session State ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "page" not in st.session_state:
    st.session_state.page = "front"

# --- Pages ---

def front_page():
    st.markdown(
        """
        <style>
        .title {
            color: #0a75ad;
            font-family: 'Arial', sans-serif;
            font-size: 3rem;
            text-align: center;
            margin-top: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<h1 class="title">Welcome to MedAlert Pro</h1>', unsafe_allow_html=True)

    lottie_animation = load_lottie_url("https://assets7.lottiefiles.com/packages/lf20_jcikwtux.json")
    if lottie_animation:
        st_lottie(lottie_animation, height=300)

    st.markdown("<p style='text-align:center; font-size: 1.2rem; color:#555;'>Your professional medical alert system</p>", unsafe_allow_html=True)

    if st.button("Get Started"):
        st.session_state.page = "login"

def login_page():
    st.subheader("Login to MedAlert Pro")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = get_user(username)
        if user and verify_password(password, user.password_hash.encode('utf-8')):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.page = "dashboard"
            st.success(f"Welcome back, {username}!")
        else:
            st.error("Invalid username or password.")

    if st.button("Register"):
        st.session_state.page = "register"

def register_page():
    st.subheader("Register for MedAlert Pro")
    new_username = st.text_input("Choose a username")
    new_password = st.text_input("Choose a password", type="password")
    confirm_password = st.text_input("Confirm password", type="password")

    if st.button("Register"):
        if new_password != confirm_password:
            st.error("Passwords do not match.")
        elif get_user(new_username):
            st.error("Username already exists.")
        elif new_username == "" or new_password == "":
            st.error("Please fill all fields.")
        else:
            create_user(new_username, new_password)
            st.success("Registration successful! Please log in.")
            st.session_state.page = "login"

    if st.button("Back to Login"):
        st.session_state.page = "login"

def dashboard_page():
    st.title(f"Dashboard - Logged in as {st.session_state.username}")
    st.markdown("### Patient Alert System")

    # Collect patient data
    with st.form("patient_form"):
        name = st.text_input("Patient Name")
        age = st.number_input("Age", min_value=0, max_value=120, step=1)
        contact = st.text_input("Contact Phone Number (+country code)")
        symptoms = st.text_area("Symptoms Description")

        submitted = st.form_submit_button("Submit Alert")

        if submitted:
            if not name or not contact or not symptoms:
                st.error("Please fill all required fields.")
            else:
                # Here you can add logic to save patient data to a DB
                st.success(f"Alert submitted for patient {name}.")

                # Send SMS alert
                try:
                    msg = f"Alert for patient {name}, age {age}.\nSymptoms: {symptoms}"
                    sid = send_sms(contact, msg)
                    st.success(f"SMS alert sent successfully! SID: {sid}")
                except Exception as e:
                    st.error(f"Failed to send SMS: {e}")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.page = "front"

# --- Router ---

if st.session_state.page == "front":
    front_page()

elif st.session_state.page == "login":
    if not st.session_state.logged_in:
        login_page()
    else:
        dashboard_page()

elif st.session_state.page == "register":
    if not st.session_state.logged_in:
        register_page()
    else:
        dashboard_page()

elif st.session_state.page == "dashboard":
    if st.session_state.logged_in:
        dashboard_page()
    else:
        st.session_state.page = "login"
        login_page()
