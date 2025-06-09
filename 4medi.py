import os
import hashlib
import streamlit as st
from datetime import datetime, time as dtime
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from twilio.rest import Client

# Streamlit page config (must be first Streamlit command)
st.set_page_config(page_title="MediPredict", page_icon="💊", layout="wide")

# --- Twilio config ---
TWILIO_SID = os.getenv("TWILIO_SID", "YOUR_TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "YOUR_TWILIO_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER", "+1234567890")

# --- In-memory user & reminder data stores ---
if "users" not in st.session_state:
    # Users schema: username -> {role, pass_hash, phone}
    st.session_state.users = {
        "drsmith": {"role": "doctor", "pass": hashlib.sha256("doc123".encode()).hexdigest(), "phone": "+911234567890"}
    }

if "reminders" not in st.session_state:
    # List of reminders: dict with keys patient, doctor, medicine, time (HH:MM), taken (None|0|1)
    st.session_state.reminders = []

# --- Helper functions ---

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def send_sms(to_number: str, body: str) -> bool:
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(body=body, from_=TWILIO_NUMBER, to=to_number)
        return True
    except Exception as e:
        st.error(f"SMS sending failed: {e}")
        return False

def register_user(username, password, role, phone):
    if username in st.session_state.users:
        st.warning("Username already exists.")
        return False
    st.session_state.users[username] = {"role": role, "pass": hash_pw(password), "phone": phone}
    st.success("Registered successfully! Please login.")
    return True

def authenticate(username, password):
    user = st.session_state.users.get(username)
    if user and user["pass"] == hash_pw(password):
        return user["role"], user["phone"]
    return None, None

# --- Authentication UI ---
if "auth" not in st.session_state:
    st.session_state.auth = {"logged": False, "username": "", "role": "", "phone": ""}

auth = st.session_state.auth

if not auth["logged"]:
    col1, col2 = st.columns(2)

    with col1:
        st.header("🔐 Login")
        login_user = st.text_input("Username", key="login_user")
        login_pw = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            role, phone = authenticate(login_user, login_pw)
            if role:
                auth.update({"logged": True, "username": login_user, "role": role, "phone": phone})
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")

    with col2:
        st.header("📝 Register")
        reg_user = st.text_input("New Username", key="reg_user")
        reg_pw = st.text_input("New Password", type="password", key="reg_pw")
        reg_role = st.selectbox("Role", ["patient", "doctor"], key="reg_role")
        reg_phone = st.text_input("Phone (include country code, e.g. +91...)", key="reg_phone")
        if st.button("Register") and reg_user and reg_pw and reg_phone:
            register_user(reg_user, reg_pw, reg_role, reg_phone)
    st.stop()

# --- Logged in user dashboard ---
username = auth["username"]
role = auth["role"]
phone = auth["phone"]

st.sidebar.write(f"Logged in as: **{username}** ({role})")
if st.sidebar.button("Logout"):
    st.session_state.auth = {"logged": False, "username": "", "role": "", "phone": ""}
    st.experimental_rerun()

if role == "doctor":
    st.title("👨‍⚕️ Doctor Dashboard")
    st.subheader("Create Medication Reminder")
    patients = [u for u, data in st.session_state.users.items() if data["role"] == "patient"]
    if patients:
        selected_patient = st.selectbox("Select Patient", patients)
        medicine_name = st.text_input("Medicine Name")
        medicine_time = st.time_input("Time to take medicine", value=dtime(9, 0))
        if st.button("Add Reminder") and medicine_name:
            st.session_state.reminders.append({
                "patient": selected_patient,
                "doctor": username,
                "medicine": medicine_name,
                "time": medicine_time.strftime("%H:%M"),
                "taken": None
            })
            pat_phone = st.session_state.users[selected_patient]["phone"]
            sent = send_sms(pat_phone, f"Reminder: Take {medicine_name} at {medicine_time.strftime('%H:%M')}.")
            if sent:
                st.success("Reminder added and SMS sent!")
            else:
                st.warning("Reminder added but SMS failed.")
    else:
        st.info("No patients registered yet.")

    st.subheader("All Medication Reminders")
    st.dataframe(pd.DataFrame(st.session_state.reminders))

elif role == "patient":
    st.title("🏥 Patient Dashboard")
    my_reminders = [r for r in st.session_state.reminders if r["patient"] == username]

    if not my_reminders:
        st.info("No reminders assigned to you yet.")
    else:
        df = pd.DataFrame(my_reminders)
        st.write("### Your Medication Schedule")
        st.dataframe(df)

        now_str = datetime.now().strftime("%H:%M")
        due_now = [r for r in my_reminders if r["time"] == now_str and r["taken"] is None]

        for i, reminder in enumerate(due_now):
            st.warning(f"Time to take **{reminder['medicine']}** prescribed by Dr. {reminder['doctor']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Mark Taken ✅ {i}"):
                    reminder["taken"] = 1
                    st.experimental_rerun()
            with col2:
                if st.button(f"Mark Missed ❌ {i}"):
                    reminder["taken"] = 0
                    st.experimental_rerun()

        # Adherence Analytics & Prediction
        df_taken = df.dropna(subset=["taken"])
        if len(df_taken) >= 4:
            df_taken["hour"] = pd.to_datetime(df_taken["time"], format="%H:%M").dt.hour
            X = df_taken[["hour"]]
            y = df_taken["taken"]
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, random_state=42)

            model = LogisticRegression().fit(X_train, y_train)
            preds = model.predict(X_test)

            st.subheader("📊 Adherence Prediction Report")
            st.text(classification_report(y_test, preds, target_names=["Missed", "Taken"]))

            hour_to_predict = st.slider("Predict adherence for hour:", 0, 23, 9)
            pred = model.predict([[hour_to_predict]])[0]
            st.info(f"At {hour_to_predict}:00, predicted adherence → **{'Taken' if pred else 'Missed'}**")
        else:
            st.info("Log more medicine intake data to get adherence predictions.")

