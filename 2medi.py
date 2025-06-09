# MediPredict – Streamlit Medication Reminder & Adherence Prediction App

import streamlit as st
import pandas as pd
import numpy as np
import datetime
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt
import seaborn as sns

# UI EXTRAS
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.colored_header import colored_header
from streamlit_extras.badges import badge

st.set_page_config(page_title="MediPredict", page_icon="💊", layout="wide")

# --------------------- Sample Backend (Simulated DB) ---------------------
if "patients" not in st.session_state:
    st.session_state.patients = []
if "reminders" not in st.session_state:
    st.session_state.reminders = []
if "doctors" not in st.session_state:
    st.session_state.doctors = []

# --------------------- Helper Functions ---------------------
def add_patient(name, age, contact):
    st.session_state.patients.append({"name": name, "age": age, "contact": contact})

def add_doctor(name, dept):
    st.session_state.doctors.append({"name": name, "dept": dept})

def add_reminder(patient_name, medicine, time, doctor):
    st.session_state.reminders.append({
        "patient": patient_name,
        "medicine": medicine,
        "time": time,
        "doctor": doctor,
        "taken": np.random.choice([0, 1], p=[0.3, 0.7])  # simulate adherence
    })

# --------------------- UI Layout ---------------------
st.title("💊 MediPredict: Smart Medication Reminder & Adherence Predictor")

tab1, tab2, tab3, tab4 = st.tabs(["📋 Patient Registration", "🧑‍⚕️ Doctor Panel", "⏰ Reminders", "📊 Analytics & ML"])

# --------------------- Tab 1: Patient Registration ---------------------
with tab1:
    colored_header("Patient Registration", description="Register new patients into the system.", color_name="violet-70")

    with st.form("add_patient_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            pname = st.text_input("Patient Name")
        with col2:
            page = st.number_input("Age", min_value=1, step=1)
        with col3:
            pcontact = st.text_input("Contact Number")

        submitted = st.form_submit_button("Add Patient")
        if submitted and pname and pcontact:
            add_patient(pname, page, pcontact)
            st.success(f"✅ Patient {pname} added.")

    st.write("### Registered Patients")
    st.dataframe(pd.DataFrame(st.session_state.patients))

# --------------------- Tab 2: Doctor Panel ---------------------
with tab2:
    colored_header("Doctor Panel", description="Add doctors and assign prescriptions to patients.", color_name="green-70")

    with st.form("add_doc_form", clear_on_submit=True):
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            dname = st.text_input("Doctor Name")
        with dcol2:
            ddept = st.text_input("Department")

        doc_submit = st.form_submit_button("Add Doctor")
        if doc_submit and dname:
            add_doctor(dname, ddept)
            st.success(f"👨‍⚕️ Dr. {dname} added to system.")

    st.write("### Doctors List")
    st.dataframe(pd.DataFrame(st.session_state.doctors))

# --------------------- Tab 3: Reminders ---------------------
with tab3:
    colored_header("Medication Reminders", description="Set up reminders for patients by doctors.", color_name="blue-70")

    with st.form("reminder_form", clear_on_submit=True):
        rcol1, rcol2, rcol3, rcol4 = st.columns(4)
        with rcol1:
            selected_patient = st.selectbox("Select Patient", [p["name"] for p in st.session_state.patients])
        with rcol2:
            selected_doctor = st.selectbox("Doctor", [d["name"] for d in st.session_state.doctors])
        with rcol3:
            medicine = st.text_input("Medicine")
        with rcol4:
            time = st.time_input("Time to Take")

        reminder_submit = st.form_submit_button("Add Reminder")
        if reminder_submit and selected_patient:
            add_reminder(selected_patient, medicine, time, selected_doctor)
            st.success(f"⏰ Reminder for {selected_patient} added.")

    st.write("### Current Reminders")
    st.dataframe(pd.DataFrame(st.session_state.reminders))

# --------------------- Tab 4: Analytics & ML ---------------------
with tab4:
    colored_header("📊 Analytics & Adherence Prediction", "Visual insights and ML-based prediction", color_name="red-70")

    if st.session_state.reminders:
        df = pd.DataFrame(st.session_state.reminders)
        df['hour'] = pd.to_datetime(df['time'].astype(str)).dt.hour
        st.write("### Medication Adherence Overview")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Reminders", len(df))
        col2.metric("Adherence Rate (%)", round(df["taken"].mean()*100, 2))
        col3.metric("Missed Doses", (df["taken"] == 0).sum())
        style_metric_cards(background_color="#f5f5f5", border_left_color="#6c6")

        # Heatmap by hour
        st.write("#### 📈 Heatmap of Doses by Hour")
        heat_df = df.groupby("hour")["taken"].mean().reset_index()
        fig, ax = plt.subplots()
        sns.heatmap(heat_df.pivot_table(values="taken", index="hour"), cmap="YlGnBu", annot=True, ax=ax)
        st.pyplot(fig)

        # ML: Predict missed dose
        st.write("#### 🤖 ML Prediction: Will a dose be missed?")
        X = df[['hour']]
        y = df['taken']
        X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)
        model = LogisticRegression()
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        st.code(classification_report(y_test, preds, target_names=["Missed", "Taken"]))

        input_hour = st.slider("Pick hour to predict missed dose", 0, 23, 9)
        prediction = model.predict([[input_hour]])
        st.info(f"💡 Prediction at {input_hour}:00 → {'Will Take' if prediction[0] else 'Will Miss'}")
    else:
        st.warning("📭 No reminders available yet to generate analytics.")
