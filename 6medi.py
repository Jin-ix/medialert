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
    if isinstance(password_hash, str):
        password_hash = password_hash.encode('utf-8')
    return bcrypt.checkpw(password.encode(), password_hash)

def get_user(username):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    return user

def create_user(username, password):
    db = SessionLocal()
    password_hash = hash_password(password)
    user = User(username=username, password_hash=password_hash.decode('utf-8'))
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

# --- CSS for styling & hover effect ---
st.markdown("""
<style>
/* GENERAL */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f5faff;
    color: #0a3d62;
}

/* BUTTON STYLE */
button, .stButton > button {
    background: #1e90ff;
    color: white;
    border-radius: 8px;
    border: none;
    padding: 10px 24px;
    font-size: 18px;
    font-weight: 600;
    transition: background-color 0.3s ease, transform 0.3s ease;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(30, 144, 255, 0.3);
}
button:hover, .stButton > button:hover {
    background: #0073e6;
    transform: scale(1.05);
    box-shadow: 0 6px 16px rgba(0, 115, 230, 0.5);
}

/* HEADERS */
h1, h2, h3, h4 {
    color: #054a91;
}

/* FORM INPUTS */
input[type="text"], input[type="password"], input[type="number"], textarea {
    padding: 10px;
    border: 1.8px solid #1e90ff;
    border-radius: 6px;
    width: 100%;
    font-size: 16px;
    color: #054a91;
    background: #e9f1ff;
    transition: border-color 0.3s ease;
}

input[type="text"]:focus, input[type="password"]:focus, input[type="number"]:focus, textarea:focus {
    border-color: #0073e6;
    outline: none;
}

/* CONTAINER STYLING */
.stForm {
    background: white;
    padding: 25px 30px;
    border-radius: 15px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    max-width: 550px;
    margin: auto;
}

/* CENTER CONTENT */
.center {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

/* FOOTER */
.footer {
    margin-top: 50px;
    text-align: center;
    font-size: 0.85rem;
    color: #888;
}

</style>
""", unsafe_allow_html=True)

# --- Pages ---

def front_page():
    st.markdown('<div class="center">', unsafe_allow_html=True)
    st.markdown('<h1>Welcome to <span style="color:#1e90ff;">MedAlert Pro</span></h1>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:1.3rem; color:#054a91;">Your professional medical alert and patient management system</p>', unsafe_allow_html=True)

    lottie_animation = load_lottie_url("https://assets7.lottiefiles.com/packages/lf20_jcikwtux.json")
    if lottie_animation:
        st_lottie(lottie_animation, height=350)

    st.markdown('<br>', unsafe_allow_html=True)
    if st.button("Get Started"):
        st.session_state.page = "login"
    st.markdown('</div>', unsafe_allow_html=True)

def login_page():
    st.markdown('<div class="stForm">', unsafe_allow_html=True)
    st.header("Login to MedAlert Pro")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = get_user(username)
        if user and verify_password(password, user.password_hash):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.page = "dashboard"
            st.success(f"Welcome back, {username}!")
        else:
            st.error("Invalid username or password.")

    if st.button("Register"):
        st.session_state.page = "register"
    st.markdown('</div>', unsafe_allow_html=True)

def register_page():
    st.markdown('<div class="stForm">', unsafe_allow_html=True)
    st.header("Register for MedAlert Pro")

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
    st.markdown('</div>', unsafe_allow_html=True)

def dashboard_page():
    st.markdown('<div class="stForm">', unsafe_allow_html=True)
    st.title(f"Dashboard - Logged in as {st.session_state.username}")
    st.markdown("### Patient Alert System")

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
                # Save patient data to DB or file here (optional)
                st.success(f"Alert submitted for patient {name}.")

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
    st.markdown('</div>', unsafe_allow_html=True)

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
