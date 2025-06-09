import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
import bcrypt
import requests
from streamlit_lottie import st_lottie

# -------- DATABASE SETUP --------
DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    doctor_name = Column(String(100), nullable=True)
    doctor_phone = Column(String(20), nullable=True)
    emergency_contact = Column(String(50), nullable=True)
    medical_notes = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

# --------- UTILS ---------

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def get_user(db, username):
    return db.query(User).filter(User.username == username).first()

def create_user(db, username, password):
    hashed_pw = get_password_hash(password)
    db_user = User(username=username, password_hash=hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_profile(db, user, doctor_name, doctor_phone, emergency_contact, medical_notes):
    user.doctor_name = doctor_name
    user.doctor_phone = doctor_phone
    user.emergency_contact = emergency_contact
    user.medical_notes = medical_notes
    db.commit()
    db.refresh(user)

# --------- LOTTIE ANIMATION ---------
def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# --------- APP PAGES ---------
def front_page():
    st.title("Welcome to MedAlert App")
    st_lottie(load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_jcikwtux.json"), height=300)
    if st.button("Get Started"):
        st.session_state.page = "login"

def register_page():
    st.header("Register New Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    password2 = st.text_input("Confirm Password", type="password")
    if st.button("Register"):
        if not username or not password:
            st.error("Please fill all fields")
            return
        if password != password2:
            st.error("Passwords do not match")
            return
        db = SessionLocal()
        user = get_user(db, username)
        if user:
            st.error("Username already exists")
            return
        create_user(db, username, password)
        st.success("Account created! Go to login.")
        st.session_state.page = "login"

def login_page():
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        db = SessionLocal()
        user = get_user(db, username)
        if user and verify_password(password, user.password_hash):
            st.success(f"Welcome back, {username}!")
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.page = "main"
        else:
            st.error("Invalid username or password")

    st.write("Don't have an account? [Register here](#)")
    if st.button("Go to Register"):
        st.session_state.page = "register"

def profile_page():
    db = SessionLocal()
    user = get_user(db, st.session_state.username)

    st.title(f"Profile: {user.username}")

    with st.form("profile_form"):
        doctor_name = st.text_input("Doctor's Name", value=user.doctor_name or "")
        doctor_phone = st.text_input("Doctor's Phone Number", value=user.doctor_phone or "")
        emergency_contact = st.text_input("Emergency Contact", value=user.emergency_contact or "")
        medical_notes = st.text_area("Medical Notes / Conditions", value=user.medical_notes or "")

        submitted = st.form_submit_button("Save Profile")
        if submitted:
            update_profile(db, user, doctor_name, doctor_phone, emergency_contact, medical_notes)
            st.success("Profile updated successfully!")

    st.markdown("---")
    st.write("### Emergency Alert Details")
    st.write(f"**Doctor:** {user.doctor_name or 'Not set'}")
    st.write(f"**Doctor Phone:** {user.doctor_phone or 'Not set'}")
    st.write(f"**Emergency Contact:** {user.emergency_contact or 'Not set'}")
    st.write(f"**Medical Notes:** {user.medical_notes or 'Not set'}")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.page = "login"

# --------- MAIN ---------
def main():
    if "page" not in st.session_state:
        st.session_state.page = "front"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.page == "front":
        front_page()
    elif st.session_state.page == "login":
        if st.session_state.logged_in:
            st.session_state.page = "main"
            main()
        else:
            login_page()
    elif st.session_state.page == "register":
        if st.session_state.logged_in:
            st.session_state.page = "main"
            main()
        else:
            register_page()
    elif st.session_state.page == "main":
        if st.session_state.logged_in:
            profile_page()
        else:
            st.session_state.page = "login"
            main()

if __name__ == "__main__":
    main()
