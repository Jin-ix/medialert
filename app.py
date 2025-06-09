import streamlit as st
from streamlit_lottie import st_lottie
import requests
from twilio.rest import Client

# === Twilio setup - replace with your real credentials ===
ACCOUNT_SID = "your_account_sid"
AUTH_TOKEN = "your_auth_token"
TWILIO_NUMBER = "+1234567890"

twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)

# === Helper functions ===

def load_lottie_url(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def send_sms(to_number: str, message: str):
    message = twilio_client.messages.create(
        body=message,
        from_=TWILIO_NUMBER,
        to=to_number
    )
    return message.sid

# === Initialize session state ===

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "front"

# === Page functions ===

def front_page():
    st.title("Welcome to My App")

    lottie_animation = load_lottie_url("https://assets10.lottiefiles.com/packages/lf20_touohxv0.json")
    if lottie_animation:
        st_lottie(lottie_animation, height=300)

    if st.button("Get Started"):
        st.session_state.page = "login"

def login_page():
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Dummy validation — replace with your own auth logic
        if username == "user" and password == "pass":
            st.session_state.logged_in = True
            st.session_state.page = "sms_sender"
            st.success("Logged in successfully!")
        else:
            st.error("Invalid username or password")

    if st.button("Register"):
        st.session_state.page = "register"

def register_page():
    st.title("Register")

    new_user = st.text_input("Choose Username")
    new_pass = st.text_input("Choose Password", type="password")
    confirm_pass = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if new_pass != confirm_pass:
            st.error("Passwords do not match")
        elif new_user == "" or new_pass == "":
            st.error("Username and password cannot be empty")
        else:
            # Add your user saving logic here
            st.success(f"User '{new_user}' registered successfully!")
            st.session_state.page = "login"

    if st.button("Back to Login"):
        st.session_state.page = "login"

def sms_sender_page():
    st.title("Twilio SMS Sender")

    to_number = st.text_input("Recipient Phone Number (with country code, e.g. +1234567890)")
    message = st.text_area("Message")

    if st.button("Send SMS"):
        if to_number and message:
            try:
                sid = send_sms(to_number, message)
                st.success(f"Message sent successfully! SID: {sid}")
                # Optionally clear inputs
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error sending message: {e}")
        else:
            st.warning("Please enter both phone number and message.")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.page = "front"

# === Main app router ===

if st.session_state.page == "front":
    front_page()

elif st.session_state.page == "login":
    if not st.session_state.logged_in:
        login_page()
    else:
        sms_sender_page()

elif st.session_state.page == "register":
    if not st.session_state.logged_in:
        register_page()
    else:
        sms_sender_page()

elif st.session_state.page == "sms_sender":
    if st.session_state.logged_in:
        sms_sender_page()
    else:
        st.session_state.page = "login"
        login_page()
