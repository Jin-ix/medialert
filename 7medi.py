import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import bcrypt

# Database setup
DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

# Helper functions

def get_user(db_session, username):
    return db_session.query(User).filter(User.username == username).first()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# App Pages

def register_page():
    st.title("Register")
    username = st.text_input("Choose a username")
    password = st.text_input("Choose a password", type="password")
    password_confirm = st.text_input("Confirm password", type="password")
    if st.button("Register"):
        if not username or not password or not password_confirm:
            st.error("Please fill all fields")
            return
        if password != password_confirm:
            st.error("Passwords do not match")
            return

        db = SessionLocal()
        existing_user = get_user(db, username)
        if existing_user:
            st.error("Username already taken")
            db.close()
            return
        
        # Hash and store password
        hashed = hash_password(password)
        new_user = User(username=username, password_hash=hashed)
        db.add(new_user)
        db.commit()
        db.close()
        st.success("Registration successful! Please login.")
        st.experimental_rerun()  # Refresh page to show login

def login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if not username or not password:
            st.error("Please enter username and password")
            return

        db = SessionLocal()
        user = get_user(db, username)
        db.close()
        if user and verify_password(password, user.password_hash):
            st.success(f"Welcome, {username}!")
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

def logout():
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""
    st.experimental_rerun()

def main_app():
    st.title(f"Welcome to MediAlert, {st.session_state['username']}!")
    st.write("This is a simple medical-themed dashboard. Customize it as you want.")
    if st.button("Logout"):
        logout()

# Main app flow control

def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""

    st.markdown(
        """
        <style>
        .stButton>button:hover {
            background-color: #4CAF50;
            color: white;
            transition: 0.3s ease;
        }
        </style>
        """, unsafe_allow_html=True)

    if not st.session_state['logged_in']:
        # Show login and register toggle
        page = st.sidebar.selectbox("Choose", ["Login", "Register"])
        if page == "Login":
            login_page()
        else:
            register_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
