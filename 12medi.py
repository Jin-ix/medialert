 """
MediPredict – Smart Medicine Adherence & Risk‑Prediction System
----------------------------------------------------------------
Streamlit single‑file prototype
Built June 9 2025 for Jinix Chacko 🇮🇳

Key screens
~~~~~~~~~~~
• Start / Home                – project intro & demo video placeholder
• Register                    – create account & basic profile
• Login                       – authenticate user session
• Dashboard (post‑login)      –
    ├─ Medication Schedule     – view / add medicines
    ├─ Log Dose                – mark Taken / Missed (writes to DB)
    └─ Insights                – adherence heat‑map & missed‑dose predictor

Tech stack
~~~~~~~~~~
• Streamlit 1.34
• SQLite3 (file‑based) via sqlite3 stdlib
• Pandas / NumPy for data wrangling
• Altair for charts
• Scikit‑learn placeholder model (Logistic Regression)

Notes
~~~~~
• The predictive model is retrained on every login for demo simplicity.
• Password hashes use SHA‑256 (⚠️ simplified; use bcrypt/argon2id in prod).
• Scheduler / alert sending (e.g., Twilio, CRON) is **not** included here – focus is on core UI + analytics; hook your preferred task queue later.
• For quick play, a synthetic user + sample meds are auto‑seeded the first run.

# User Question (Jun 9 2025): “give me code for this with start page login and registration widgets effects”
"""

import hashlib
import os
import sqlite3
import time
from datetime import datetime, timedelta

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

##############################################################################
# 👾 DB HELPERS
##############################################################################

DB_PATH = "medipredict.db"


def create_connection(path: str = DB_PATH):
    return sqlite3.connect(path, check_same_thread=False)


def init_db():
    conn = create_connection()
    cur = conn.cursor()

    # USERS
    cur.execute(
        """CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                email TEXT,
                pwd_hash TEXT,
                age INT,
                doctor_name TEXT,
                doctor_phone TEXT
        );"""
    )

    # MEDICATION SCHEDULE
    cur.execute(
        """CREATE TABLE IF NOT EXISTS meds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                med_name TEXT,
                dose TEXT,
                time_of_day TEXT,           -- e.g. "08:00", "21:00"
                FOREIGN KEY(username) REFERENCES users(username)
        );"""
    )

    # DOSE LOG
    cur.execute(
        """CREATE TABLE IF NOT EXISTS dose_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                med_id INT,
                ts DATETIME,
                taken INT,                  -- 1 taken, 0 missed
                FOREIGN KEY(username) REFERENCES users(username),
                FOREIGN KEY(med_id)  REFERENCES meds(id)
        );"""
    )

    conn.commit()
    cur.close()
    conn.close()

##############################################################################
# 🔐 AUTH HELPERS
##############################################################################


def hash_pwd(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_pwd(password: str, hashed: str) -> bool:
    return hash_pwd(password) == hashed


def create_user(username: str, email: str, password: str, age: int, doc_name: str, doc_phone: str):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, email, pwd_hash, age, doctor_name, doctor_phone) VALUES (?,?,?,?,?,?)",
        (username, email, hash_pwd(password), age, doc_name, doc_phone),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_user(username: str):
    conn = create_connection()
    user = pd.read_sql_query("SELECT * FROM users WHERE username=?", conn, params=(username,))
    conn.close()
    return user.iloc[0] if not user.empty else None

##############################################################################
# 💊 MED HELPERS
##############################################################################


def add_med(username: str, med_name: str, dose: str, time_of_day: str):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO meds (username, med_name, dose, time_of_day) VALUES (?,?,?,?)",
        (username, med_name, dose, time_of_day),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_user_meds(username: str) -> pd.DataFrame:
    conn = create_connection()
    df = pd.read_sql_query("SELECT * FROM meds WHERE username=?", conn, params=(username,))
    conn.close()
    return df


def log_dose(username: str, med_id: int, taken: int):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO dose_log (username, med_id, ts, taken) VALUES (?,?,?,?)",
        (username, med_id, datetime.now(), taken),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_logs(username: str) -> pd.DataFrame:
    conn = create_connection()
    df = pd.read_sql_query("SELECT * FROM dose_log WHERE username=?", conn, params=(username,))
    conn.close()
    return df

##############################################################################
# 🤖 MODEL HELPERS (simple placeholder)
##############################################################################

MODEL_FNAME = "adherence_clf.pkl"


def train_predictor(logs: pd.DataFrame, meds: pd.DataFrame):
    if logs.empty:
        st.info("Need dose logs to train the missed‑dose predictor 🧪")
        return None

    # Feature engineering
    df = logs.copy()
    df = df.merge(meds[["id", "time_of_day"]], left_on="med_id", right_on="id", how="left")

    df["hour"] = pd.to_datetime(df["ts"]).dt.hour
    df["dayofweek"] = pd.to_datetime(df["ts"]).dt.dayofweek
    X = df[["hour", "dayofweek", "time_of_day"]]
    y = df["taken"]

    # Categorical encoder for time_of_day (HH:MM string)
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["time_of_day"])
    ], remainder="passthrough")

    clf = Pipeline([
        ("prep", pre),
        ("clf", LogisticRegression(max_iter=1000))
    ])

    clf.fit(X, y)
    return clf


##############################################################################
# 🎨 UI SECTIONS
##############################################################################

def home_screen():
    st.title("💊 MediPredict – Smart Medicine Adherence")
    st.markdown(
        """
        **Take the right pill at the right time – and let your doctor know.**  
        MediPredict sends reminders, learns your habits, and helps clinicians spot risk early.
        """
    )
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", start_time=42)


def register_screen():
    st.header("Create your account")
    with st.form("reg_form"):
        col1, col2 = st.columns(2)
        username = col1.text_input("Username")
        email = col1.text_input("Email")
        password = col1.text_input("Password", type="password")
        age = col2.number_input("Age", min_value=0, max_value=120, value=30)
        doc_name = col2.text_input("Doctor's Name")
        doc_phone = col2.text_input("Doctor's Phone")
        agree = st.checkbox("I accept the terms & privacy policy.")
        submit = st.form_submit_button("Register ✨")

    if submit and agree:
        if get_user(username) is None:
            create_user(username, email, password, age, doc_name, doc_phone)
            st.success("Account created. You can now log in ✅")
        else:
            st.error("Username already exists")


def login_screen():
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login 🚀"):
        user = get_user(username)
        if user is not None and verify_pwd(password, user["pwd_hash"]):
            st.session_state["logged_in"] = True
            st.session_state["user"] = username
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")


def schedule_tab(username):
    st.subheader("Medication Schedule")
    meds = get_user_meds(username)
    st.table(meds[["med_name", "dose", "time_of_day"]])

    with st.form("add_med"):
        col1, col2, col3 = st.columns(3)
        med_name = col1.text_input("Medicine Name")
        dose = col2.text_input("Dosage (e.g., 500mg)")
        time_of_day = col3.time_input("Time of Day")
        add_btn = st.form_submit_button("Add Medicine")
    if add_btn:
        add_med(username, med_name, dose, time_of_day.strftime("%H:%M"))
        st.experimental_rerun()


def log_tab(username):
    st.subheader("Log a Dose")
    meds = get_user_meds(username)
    if meds.empty:
        st.warning("Add medicines first!")
        return

    med_dict = {f"{row.med_name} – {row.time_of_day}": row.id for row in meds.itertuples()}
    med_choice = st.selectbox("Select Medicine", list(med_dict.keys()))
    taken = st.radio("Status", ["Taken", "Missed"], horizontal=True)
    if st.button("Save Log 📝"):
        log_dose(username, med_dict[med_choice], 1 if taken == "Taken" else 0)
        st.success("Saved ✔️")


def insights_tab(username):
    st.subheader("Insights & Predictions")
    logs = get_logs(username)
    meds = get_user_meds(username)

    if logs.empty:
        st.info("No dose logs yet. Start logging to unlock insights 📊")
        return

    # Heatmap of missed doses
    df = logs.copy()
    df["date"] = pd.to_datetime(df["ts"]).dt.date
    df["hour"] = pd.to_datetime(df["ts"]).dt.hour
    missed = df[df["taken"] == 0]
    if not missed.empty:
        heat = (
            alt.Chart(missed)
            .mark_rect()
            .encode(
                x=alt.X("hour:O", title="Hour of Day"),
                y=alt.Y("date:T", title="Date"),
                color=alt.value("#e63946"),
            )
        )
        st.altair_chart(heat, use_container_width=True)
    else:
        st.success("Great! No missed doses logged yet 🎉")

    # Train predictor
    clf = train_predictor(logs, meds)
    if clf:
        # synthetic future prediction – next 24h
        future = pd.DataFrame({
            "hour": list(range(24)),
            "dayofweek": [(datetime.today().weekday())] * 24,
            "time_of_day": [f"{h:02d}:00" for h in range(24)]
        })
        probs = clf.predict_proba(future)[:, 0]  # prob. of miss (taken==0)
        future["miss_prob"] = probs
        worst = future.nlargest(3, "miss_prob")
        st.write("### Highest‑risk hours (next 24 h)")
        st.table(worst[["hour", "miss_prob"]].rename(columns={"hour": "Hour", "miss_prob": "Miss Prob."}))


def dashboard(username):
    tabs = st.tabs(["Schedule", "Log Dose", "Insights"])
    with tabs[0]:
        schedule_tab(username)
    with tabs[1]:
        log_tab(username)
    with tabs[2]:
        insights_tab(username)

##############################################################################
# 🚦 APP ENTRYPOINT
##############################################################################

def main():
    st.set_page_config(page_title="MediPredict", page_icon="💊", layout="centered")
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # Auto‑seed sample user on first boot
    if get_user("demo") is None:
        create_user("demo", "demo@med.com", "demo", 42, "Dr. Strange", "+91‑9999999999")
        add_med("demo", "Metformin", "500 mg", "08:00")
        add_med("demo", "Atorvastatin", "20 mg", "21:00")

    menu = ["Home", "Login", "Register"]
    if st.session_state["logged_in"]:
        menu.insert(0, "Dashboard")

    choice = st.sidebar.radio("Navigation", menu)

    if choice == "Home":
        home_screen()
    elif choice == "Register":
        register_screen()
    elif choice == "Login":
        login_screen()
    elif choice == "Dashboard":
        dashboard(st.session_state["user"])


if __name__ == "__main__":
    main()
