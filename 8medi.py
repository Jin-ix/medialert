import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import bcrypt
import requests
from streamlit_lottie import st_lottie

# --- DATABASE SETUP ---
DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

# --- HELPERS ---

def get_user(db_session, username):
    return db_session.query(User).filter(User.username == username).first()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def load_lottie_url(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# --- PAGES ---

def front_page():
    st.title("Welcome to MediAlert")
    lottie_anim = load_lottie_url("https://assets9.lottiefiles.com/packages/lf20_btpv2zci.json")
    if lottie_anim:
        st_lottie(lottie_anim, height=300)
    else:
        st.write("Welcome to MediAlert - Your Medical Assistant")
    if st.button("Get Started"):
        st.session_state.page = "login"
        st.experimental_rerun()

def login_page():
    st.title("Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        if not username or not password:
            st.error("Please enter username and password.")
            return

        db = SessionLocal()
        user = get_user(db, username)
        db.close()

        if user and verify_password(password, user.password_hash):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Welcome back, {username}!")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password.")

    st.write("Don't have an account? [Register here](#)")
    if st.button("Go to Register"):
        st.session_state.page = "register"
        st.experimental_rerun()

def register_page():
    st.title("Register")
    username = st.text_input("Choose a username", key="reg_username")
    password = st.text_input("Choose a password", type="password", key="reg_password")
    password_confirm = st.text_input("Confirm password", type="password", key="reg_password_confirm")

    if st.button("Register"):
        if not username or not password or not password_confirm:
            st.error("Please fill in all fields.")
            return
        if password != password_confirm:
            st.error("Passwords do not match.")
            return

        db = SessionLocal()
        existing_user = get_user(db, username)
        if existing_user:
            st.error("Username already taken.")
            db.close()
            return
        
        hashed = hash_password(password)
        new_user = User(username=username, password_hash=hashed)
        db.add(new_user)
        db.commit()
        db.close()

        st.success("Registration successful! Please log in.")
        st.session_state.page = "login"
        st.experimental_rerun()

    if st.button("Go to Login"):
        st.session_state.page = "login"
        st.experimental_rerun()

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.page = "front"
    st.experimental_rerun()

# --- Your Core App Functionalities ---

def app_dashboard():
    st.title(f"MediAlert Dashboard - Welcome {st.session_state.username}!")
    
    # Example: Medical Alert Form
    st.subheader("Medical Alert Entry")
    patient_name = st.text_input("Patient Name")
    symptoms = st.text_area("Symptoms")
    severity = st.selectbox("Severity", ["Low", "Moderate", "High"])
    if st.button("Submit Alert"):
        # In real app: save to DB or send notification
        st.success(f"Alert submitted for {patient_name} with severity {severity}")

    # Add more medical features here: alerts, history, analytics, notifications, etc.

    if st.button("Logout"):
        logout()

# --- MAIN FLOW ---

def main():
    # Initialize session state variables
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "page" not in st.session_state:
        st.session_state.page = "front"

    # CSS for button hover effect
    st.markdown(
        """
        <style>
        .stButton>button:hover {
            background-color: #4CAF50 !important;
            color: white !important;
            transition: 0.3s ease;
            cursor: pointer;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.logged_in:
        if st.session_state.page == "front":
            front_page()
        elif st.session_state.page == "login":
            login_page()
        elif st.session_state.page == "register":
            register_page()
    else:
        app_dashboard()

if __name__ == "__main__":
    main()
