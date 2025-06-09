# MediPredict – Streamlit Medication Reminder & Adherence Prediction App
# -------------------------------------------------------------
# Author: Jinix Chacko (with ChatGPT assistance)
# Date: June 2025
# -------------------------------------------------------------
# HOW TO RUN:
# 1. Install the dependencies:
#    pip install streamlit pandas scikit-learn matplotlib seaborn
# 2. Run the app:
#    streamlit run app.py
# -------------------------------------------------------------
# WHY THIS APP WILL IMPRESS YOUR EXAMINERS:
# • Demonstrates full‑stack data science: data collection ➜ analytics ➜ ML prediction ➜ interactive UI
# • Uses an SQLite backend for persistence (production‑ready can swap for Postgres)
# • Generates interactive charts and live ML training within Streamlit
# -------------------------------------------------------------
pip install scikit-learn

import sqlite3
import json
from datetime import datetime, date, time, timedelta

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

DB_NAME = "medipredict.db"

# ---------------------- Database Utilities ---------------------- #

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            email TEXT,
            doctor_id INTEGER,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            name TEXT NOT NULL,
            dosage TEXT,
            schedule_times TEXT,    -- JSON list of times ("08:00", "14:00", ...)
            start_date TEXT,
            end_date TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            medication_id INTEGER,
            scheduled_time TEXT,
            status TEXT,            -- 'Taken' or 'Missed'
            timestamp TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (medication_id) REFERENCES medications(id)
        );
        """
    )
    conn.commit()
    conn.close()


# Call once at startup
init_db()

# ---------------------- Helper Functions ---------------------- #

def add_doctor(name: str, email: str):
    with get_connection() as conn:
        conn.execute("INSERT INTO doctors (name, email) VALUES (?, ?)", (name, email))
        conn.commit()


def get_doctors():
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM doctors", conn)


def add_patient(name: str, age: int, email: str, doctor_id: int):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO patients (name, age, email, doctor_id) VALUES (?, ?, ?, ?)",
            (name, age, email, doctor_id),
        )
        conn.commit()


def get_patients():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT p.*, d.name AS doctor_name FROM patients p LEFT JOIN doctors d ON p.doctor_id = d.id",
            conn,
        )


def add_medication(patient_id: int, name: str, dosage: str, schedule_times: list[str], start_date: date, end_date: date):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO medications (patient_id, name, dosage, schedule_times, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                name,
                dosage,
                json.dumps(schedule_times),
                start_date.isoformat(),
                end_date.isoformat(),
            ),
        )
        conn.commit()


def get_medications(patient_id: int | None = None):
    query = "SELECT * FROM medications"
    params = ()
    if patient_id is not None:
        query += " WHERE patient_id = ?"
        params = (patient_id,)
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def log_dose(patient_id: int, medication_id: int, scheduled_time: str, status: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO logs (patient_id, medication_id, scheduled_time, status, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                patient_id,
                medication_id,
                scheduled_time,
                status,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()


def get_logs(patient_id: int | None = None):
    query = "SELECT * FROM logs"
    params = ()
    if patient_id is not None:
        query += " WHERE patient_id = ?"
        params = (patient_id,)
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


# ---------------------- Streamlit UI ---------------------- #

st.set_page_config(page_title="MediPredict", layout="wide")
st.title("💊 MediPredict – Medication Reminder & Adherence Analytics")

menu = st.sidebar.radio("Navigation", [
    "Home",
    "Doctors",
    "Patients",
    "Prescriptions",
    "Reminders & Tracking",
    "Adherence Insights",
    "Risk Prediction",
])

# ------------- Home ------------- #
if menu == "Home":
    st.markdown(
        """
        ### Welcome to MediPredict
        This app helps **doctors** prescribe medicines, **patients** remember doses, and uses **machine learning** to predict the risk of missing a dose.
        """
    )
    st.info("Use the sidebar to navigate through the features.")

# ------------- Doctors ------------- #
elif menu == "Doctors":
    st.header("👨‍⚕️ Doctor Management")
    with st.expander("Add New Doctor"):
        d_name = st.text_input("Name")
        d_email = st.text_input("Email")
        if st.button("Add Doctor"):
            if d_name:
                add_doctor(d_name, d_email)
                st.success("Doctor added.")
            else:
                st.warning("Name required.")

    st.subheader("Registered Doctors")
    st.dataframe(get_doctors())

# ------------- Patients ------------- #
elif menu == "Patients":
    st.header("🧑‍🤝‍🧑 Patient Management")
    doctors_df = get_doctors()
    with st.expander("Add New Patient"):
        p_name = st.text_input("Patient Name")
        p_age = st.number_input("Age", 0, 120, 40)
        p_email = st.text_input("Email")
        doctor_choice = st.selectbox("Assign Doctor", doctors_df["name"])
        if st.button("Add Patient"):
            did = doctors_df[doctors_df["name"] == doctor_choice]["id"].iloc[0]
            add_patient(p_name, p_age, p_email, did)
            st.success("Patient added.")

    st.subheader("Patients List")
    st.dataframe(get_patients())

# ------------- Prescriptions ------------- #
elif menu == "Prescriptions":
    st.header("💊 Prescribe Medication")

    patients_df = get_patients()
    if patients_df.empty:
        st.warning("Add patients first.")
    else:
        pat_choice = st.selectbox("Select Patient", patients_df["name"])
        patient_id = patients_df[patients_df["name"] == pat_choice]["id"].iloc[0]

        med_name = st.text_input("Medicine Name")
        dosage = st.text_input("Dosage (e.g., 500mg)")
        times = st.multiselect(
            "Dose Times (24h format)",
            ["06:00", "08:00", "12:00", "14:00", "18:00", "20:00", "22:00"],
        )
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start Date", date.today())
        with col2:
            end = st.date_input("End Date", date.today() + timedelta(days=7))

        if st.button("Add Prescription") and med_name and times:
            add_medication(patient_id, med_name, dosage, times, start, end)
            st.success("Medication added.")

        st.subheader("Current Medications for " + pat_choice)
        st.dataframe(get_medications(patient_id))

# ------------- Reminders & Tracking ------------- #
elif menu == "Reminders & Tracking":
    st.header("🔔 Reminders & Dose Tracking")
    patients_df = get_patients()
    if patients_df.empty:
        st.warning("No patients available.")
    else:
        pat_choice = st.selectbox("Select Patient", patients_df["name"])
        patient_id = patients_df[patients_df["name"] == pat_choice]["id"].iloc[0]
        meds_df = get_medications(patient_id)
        if meds_df.empty:
            st.info("No prescriptions for this patient.")
        else:
            now = datetime.now()
            today_str = date.today().isoformat()
            st.write(f"### Simulated reminders for {today_str} (Current time: {now.strftime('%H:%M')})")
            due_df = []
            for _, row in meds_df.iterrows():
                schedule_list = json.loads(row["schedule_times"])
                for sched in schedule_list:
                    sched_dt = datetime.combine(date.today(), datetime.strptime(sched, "%H:%M").time())
                    # within ±30 minutes window
                    if abs((now - sched_dt).total_seconds()) <= 1800:
                        due_df.append(
                            {
                                "Medication": row["name"],
                                "Dosage": row["dosage"],
                                "Scheduled": sched,
                                "Medication_ID": row["id"],
                            }
                        )
            if due_df:
                due_df = pd.DataFrame(due_df)
                for idx, d in due_df.iterrows():
                    st.info(
                        f"{d['Medication']} ({d['Dosage']}) scheduled at {d['Scheduled']}",
                        icon="💡",
                    )
                    colA, colB = st.columns(2)
                    with colA:
                        if st.button(
                            f"Taken ✅ {idx}", key=f"taken{idx}"):
                            log_dose(patient_id, int(d["Medication_ID"]), d["Scheduled"], "Taken")
                            st.success("Logged as taken.")
                    with colB:
                        if st.button(
                            f"Missed ❌ {idx}", key=f"miss{idx}"):
                            log_dose(patient_id, int(d["Medication_ID"]), d["Scheduled"], "Missed")
                            st.error("Logged as missed.")
            else:
                st.success("No doses due in the next 30 minutes.")

            # Show recent logs
            st.subheader("Today’s Logs")
            logs = get_logs(patient_id)
            today_logs = logs[logs["timestamp"].str.startswith(today_str)]
            st.dataframe(today_logs)

# ------------- Adherence Insights ------------- #
elif menu == "Adherence Insights":
    st.header("📊 Adherence Insights")
    patients_df = get_patients()
    if patients_df.empty:
        st.warning("No patients available.")
    else:
        pat_choice = st.selectbox("Select Patient", patients_df["name"])
        patient_id = patients_df[patients_df["name"] == pat_choice]["id"].iloc[0]
        logs = get_logs(patient_id)
        if logs.empty:
            st.info("No log data yet.")
        else:
            logs["timestamp"] = pd.to_datetime(logs["timestamp"])
            logs["date"] = logs["timestamp"].dt.date
            logs["hour"] = logs["timestamp"].dt.hour
            taken_rate = logs[logs["status"] == "Taken"].shape[0] / logs.shape[0] * 100
            st.metric("Overall Adherence %", f"{taken_rate:.1f}%")

            # Heatmap day vs hour
            pivot = logs.pivot_table(
                index="hour", columns="date", values="status", aggfunc=lambda x: (x == "Missed").mean()
            )
            fig, ax = plt.subplots()
            sns.heatmap(pivot, cmap="YlOrRd", cbar_kws={"label": "Miss Ratio"}, ax=ax)
            ax.set_title("Missed Dose Heatmap")
            st.pyplot(fig)

            # Taken vs missed bar
            status_counts = logs["status"].value_counts()
            st.bar_chart(status_counts)

# ------------- Risk Prediction ------------- #
elif menu == "Risk Prediction":
    st.header("🔮 Non‑Adherence Risk Prediction")
    logs = get_logs()
    if logs.empty:
        st.info("Need log data to train prediction model.")
    else:
        # Prepare dataset
        logs["timestamp"] = pd.to_datetime(logs["timestamp"])
        logs["hour"] = logs["timestamp"].dt.hour
        logs["dayofweek"] = logs["timestamp"].dt.dayofweek
        logs["taken"] = logs["status"].apply(lambda s: 1 if s == "Taken" else 0)

        X = logs[["hour", "dayofweek"]]
        y = logs["taken"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

        clf = LogisticRegression()
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)
        acc = accuracy_score(y_test, preds)
        st.metric("Prediction Accuracy", f"{acc*100:.2f}%")

        st.text("\nClassification Report:\n" + classification_report(y_test, preds))

        st.subheader("Predict Risk for Next Dose")
        col1, col2 = st.columns(2)
        with col1:
            hour_inp = st.slider("Hour of Day (0‑23)", 0, 23, datetime.now().hour)
        with col2:
            dow_inp = st.selectbox("Day of Week (Mon=0)", list(range(7)))

        proba_miss = clf.predict_proba([[hour_inp, dow_inp]])[0][0]
        st.warning(f"Estimated chance of MISSING the dose: **{proba_miss*100:.1f}%**")

        st.caption("Model trained using Logistic Regression on historical adherence logs.")
