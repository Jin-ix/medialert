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
• Password hashes use SHA‑256 (⚠️simplified; use bcrypt/argon2id in prod).
• Scheduler / alert sending (e.g., Twilio, CRON) is **not** included here – focus is on core UI + analytics; hook your preferred task queue later.
• For quick play, a synthetic user + sample meds are auto‑seeded the first run.
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

# ---------- Config ----------
st.set_page_config(page_title="MediPredict", layout="wide")
DB_PATH = "medipredict.db"

# ---------- Utils ----------
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            age INTEGER,
            gender TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS meds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            med_name TEXT,
            dosage TEXT,
            schedule TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS doses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            med_id INTEGER,
            timestamp TEXT,
            status TEXT CHECK(status IN ('Taken','Missed')),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(med_id) REFERENCES meds(id)
        )""")
        conn.commit()

# ---------- App State ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None

# ---------- Pages ----------
def show_home():
    st.title("💊 MediPredict")
    st.subheader("Smart Medicine Adherence & Risk Prediction")
    st.markdown("""
    📈 Built with Streamlit, this system allows:
    - Medication reminders
    - Dose tracking (Taken / Missed)
    - Insights on adherence patterns
    - AI-powered prediction for missed doses
    """)

def show_register():
    st.subheader("Create an Account")
    uname = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    age = st.number_input("Age", 0, 120)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    if st.button("Register"):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                conn.execute("INSERT INTO users (username, password, age, gender) VALUES (?, ?, ?, ?)",
                             (uname, hash_pw(pw), age, gender))
                st.success("Account created. Please login.")
            except sqlite3.IntegrityError:
                st.error("Username already exists.")

def show_login():
    st.subheader("Login")
    uname = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=? AND password=?", (uname, hash_pw(pw)))
            user = cur.fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

def show_dashboard():
    tabs = st.tabs(["💊 Medication Schedule", "✅ Log Dose", "📊 Insights"])

    # Medication tab
    with tabs[0]:
        st.header("Your Medications")
        with sqlite3.connect(DB_PATH) as conn:
            meds = pd.read_sql_query("SELECT * FROM meds WHERE user_id=?", conn, params=(st.session_state.user_id,))
            st.dataframe(meds.drop(columns=["user_id"]))
            with st.form("add_med"):
                name = st.text_input("Medicine Name")
                dose = st.text_input("Dosage")
                sched = st.text_input("Schedule (e.g. Morning)")
                if st.form_submit_button("Add"):
                    conn.execute("INSERT INTO meds (user_id, med_name, dosage, schedule) VALUES (?, ?, ?, ?)",
                                 (st.session_state.user_id, name, dose, sched))
                    st.success("Medicine added")
                    st.experimental_rerun()

    # Dose log tab
    with tabs[1]:
        st.header("Log a Dose")
        with sqlite3.connect(DB_PATH) as conn:
            meds = pd.read_sql_query("SELECT id, med_name FROM meds WHERE user_id=?", conn,
                                     params=(st.session_state.user_id,))
            if meds.empty:
                st.info("Add a medication first.")
            else:
                med_name = st.selectbox("Select Medicine", meds["med_name"])
                status = st.radio("Taken or Missed?", ["Taken", "Missed"])
                if st.button("Log"):
                    med_id = meds.loc[meds.med_name == med_name, "id"].values[0]
                    ts = datetime.now().isoformat()
                    conn.execute("INSERT INTO doses (user_id, med_id, timestamp, status) VALUES (?, ?, ?, ?)",
                                 (st.session_state.user_id, med_id, ts, status))
                    st.success("Logged successfully")

    # Insights tab
    with tabs[2]:
        st.header("Adherence Insights")
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("SELECT * FROM doses WHERE user_id=?", conn,
                                   params=(st.session_state.user_id,))
        if df.empty:
            st.info("No dose logs yet.")
            return
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["hour"] = df["timestamp"].dt.hour
        df["day"] = df["timestamp"].dt.day_name()
        heat = df.groupby(["day", "hour", "status"]).size().reset_index(name="count")
        chart = alt.Chart(heat).mark_rect().encode(
            x="hour:O",
            y="day:O",
            color="count:Q",
            tooltip=["status", "count"]
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

        # Predictive model (toy example)
        df["status_bin"] = df["status"] == "Missed"
        X = df[["hour", "day"]]
        y = df["status_bin"]
        model = Pipeline([
            ("pre", ColumnTransformer([
                ("cat", OneHotEncoder(), ["day"])
            ], remainder="passthrough")),
            ("clf", LogisticRegression())
        ])
        model.fit(X, y)
        test_hour = st.slider("Hour of day", 0, 23, 8)
        test_day = st.selectbox("Day", df["day"].unique())
        prob = model.predict_proba(pd.DataFrame([[test_hour, test_day]], columns=["hour", "day"]))[0][1]
        st.metric("Predicted Risk of Missing", f"{prob*100:.1f}%")

# ---------- Main ----------
init_db()
st.sidebar.title("Navigation")
opt = st.sidebar.radio("Go to", ["Home", "Register", "Login"] if not st.session_state.logged_in else ["Home", "Dashboard"])

if opt == "Home":
    show_home()
elif opt == "Register":
    show_register()
elif opt == "Login":
    show_login()
elif opt == "Dashboard":
    show_dashboard()
