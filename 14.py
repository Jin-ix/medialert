"""
MediPredict – Smart Medicine Adherence & Risk Prediction
--------------------------------------------------------
Streamlit single-file app, styled in the spirit of “One Medical”
Author : Jinix Chacko  |  Updated : 9 June 2025
"""

# ──────────────────────────────────────────────────────────────
# Imports & Config
# ──────────────────────────────────────────────────────────────
import os, sqlite3, hashlib, base64
from datetime import datetime
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

st.set_page_config(
    page_title="MediPredict",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────
# Constants & Styling
# ──────────────────────────────────────────────────────────────
DB_PATH = "medipredict.db"
PRIMARY = "#0b615e"          # One Medical-ish teal
ACCENT  = "#009f78"
LIGHT_BG = "#f5f7fa"

# tiny teal capsule logo (SVG → Base-64)
_LOGO = """
PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCAyNTYgMjU2IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDov
L3d3dy53My5vcmcvMjAwMC9zdmciPjxyZWN0IHg9IjM5IiB5PSIxMCIgd2lkdGg9IjE3OCIgaGVpZ2h0PSIyMzYiIHJ4PSIxMTgi
IGZpbGw9IiMwYjYxNWUiLz48L3N2Zz4=
""".strip()

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600&display=swap');

html, body, [class*="st-"] {{
    font-family: 'Source Sans Pro', sans-serif;
}}
body {{
    background-color:{LIGHT_BG};
}}
/* Top Nav */
.navbar {{
    position:fixed; top:0; left:0; right:0; height:60px;
    background:{PRIMARY}; color:white; z-index:100;
    display:flex; align-items:center; padding:0 1.5rem;
    box-shadow:0 2px 6px rgba(0,0,0,.1);
}}
.navbar img {{ height:36px; margin-right:.75rem; }}
.navbar a {{
    color:white; margin-left:1.25rem; text-decoration:none;
    font-weight:600; font-size:0.95rem;
}}
/* Card look for main containers */
div[data-testid="stVerticalBlock"] > div:first-child {{
    background:white; padding:2rem 2.5rem; border-radius:12px;
    box-shadow:0 2px 12px rgba(0,0,0,.05);
}}
/* Center hero text */
.center {{
    text-align:center;
}}
/* Remove Streamlit default padding up top (compensated by navbar) */
.block-container {{
    padding-top:4rem;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Top Navigation Bar (HTML)
nav_html = f"""
<div class="navbar">
    <img src="data:image/svg+xml;base64,{_LOGO}">
    <a href="#home">Home</a>
    <a href="#features">Features</a>
    {'<a href="#dashboard">Dashboard</a>' if st.session_state.get("logged_in") else ''}
    <span style="flex:1"></span>
    {'<a href="#logout">Logout</a>' if st.session_state.get("logged_in")
      else '<a href="#login">Login</a>'}
</div>
"""
st.markdown(nav_html, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# DB Helpers
# ──────────────────────────────────────────────────────────────
def hash_pw(pw:str)->str:
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    if not os.path.exists(DB_PATH):
        open(DB_PATH, "w").close()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users
          (id INTEGER PRIMARY KEY AUTOINCREMENT,
           username TEXT UNIQUE, password TEXT,
           age INTEGER, gender TEXT);
        CREATE TABLE IF NOT EXISTS meds
          (id INTEGER PRIMARY KEY AUTOINCREMENT,
           user_id INTEGER, med_name TEXT,
           dosage TEXT, schedule TEXT);
        CREATE TABLE IF NOT EXISTS doses
          (id INTEGER PRIMARY KEY AUTOINCREMENT,
           user_id INTEGER, med_id INTEGER,
           timestamp TEXT, status TEXT CHECK(status IN ('Taken','Missed')));
        """)
        conn.commit()

init_db()

# ──────────────────────────────────────────────────────────────
# Session Defaults
# ──────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in=False
    st.session_state.user_id=None
    st.session_state.rerun=False

# ──────────────────────────────────────────────────────────────
# UI Pages
# ──────────────────────────────────────────────────────────────
def page_home():
    st.markdown("<div class='center'>", unsafe_allow_html=True)
    st.image("https://images.unsplash.com/photo-1603398938378-035ad1604fd4?auto=format&fit=crop&w=1200&q=60",
             caption="", use_column_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.header("Welcome to MediPredict")
    st.write(
        """
        **MediPredict** helps patients remember doses, doctors track adherence,
        and uses machine learning to predict risk of missing future doses.
        """)
    st.write("⬅️ Use the links in the top bar to explore.")

def page_register():
    st.header("Create Account")
    with st.form("reg"):
        uname = st.text_input("Username", key="reg_user")
        pw = st.text_input("Password", type="password", key="reg_pass")
        age = st.number_input("Age", 0, 120)
        gender = st.selectbox("Gender", ["Male","Female","Other"])
        submit = st.form_submit_button("Register")
    if submit:
        if not uname or not pw:
            st.error("Username and password required.")
        else:
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    conn.execute("INSERT INTO users (username,password,age,gender) VALUES (?,?,?,?)",
                                 (uname, hash_pw(pw), age, gender))
                    st.success("Account created. Please log in.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists.")

def page_login():
    st.header("Log In")
    with st.form("login"):
        uname = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
    if submit:
        with sqlite3.connect(DB_PATH) as conn:
            cur=conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=? AND password=?",
                        (uname, hash_pw(pw)))
            row=cur.fetchone()
            if row:
                st.session_state.logged_in=True
                st.session_state.user_id=row[0]
                st.success("Logged in ✔️")
                st.session_state.rerun=True   # trigger safe rerun
                st.stop()
            else:
                st.error("Invalid credentials.")

def page_dashboard():
    st.header("Dashboard")
    tabs = st.tabs(["💊 Medications","📝 Log Dose","📊 Insights"])
    uid = st.session_state.user_id

    # ─── Meds Tab ─────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Your Medication List")
        with sqlite3.connect(DB_PATH) as conn:
            meds = pd.read_sql_query("SELECT * FROM meds WHERE user_id=?", conn, params=(uid,))
            if meds.empty:
                st.info("No medicines yet. Add below.")
            else:
                st.dataframe(meds.drop(columns=["user_id","id"]), hide_index=True)

            with st.form("add_med"):
                c1,c2,c3 = st.columns(3)
                with c1: name = st.text_input("Medicine Name")
                with c2: dose = st.text_input("Dosage")
                with c3: sched = st.text_input("Schedule (e.g. Morning)")
                if st.form_submit_button("Add"):
                    if name:
                        conn.execute("INSERT INTO meds (user_id,med_name,dosage,schedule) VALUES (?,?,?,?)",
                                     (uid,name,dose,sched))
                        conn.commit()
                        st.experimental_rerun()

    # ─── Log Tab ─────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Log a Dose")
        with sqlite3.connect(DB_PATH) as conn:
            med_df = pd.read_sql_query("SELECT id,med_name FROM meds WHERE user_id=?", conn, params=(uid,))
        if med_df.empty:
            st.info("Add a medicine first.")
        else:
            med_name = st.selectbox("Medicine", med_df["med_name"])
            status = st.radio("Status", ["Taken","Missed"], horizontal=True)
            if st.button("Save log"):
                med_id = int(med_df.loc[med_df.med_name==med_name,"id"].values[0])
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute("INSERT INTO doses (user_id,med_id,timestamp,status) VALUES (?,?,?,?)",
                                 (uid,med_id,datetime.now().isoformat(),status))
                    conn.commit()
                st.success("Logged.")
                st.experimental_rerun()

    # ─── Insights Tab ────────────────────────────────────────
    with tabs[2]:
        st.subheader("Adherence Heat-Map & Predictor")
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("SELECT * FROM doses WHERE user_id=?", conn, params=(uid,))
        if df.empty:
            st.info("No logs yet.")
        else:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["hour"] = df["timestamp"].dt.hour
            df["day"]  = df["timestamp"].dt.day_name()
            heat = df.groupby(["day","hour","status"]).size().reset_index(name="count")

            chart = alt.Chart(heat).mark_rect().encode(
                x=alt.X("hour:O", title="Hour of Day"),
                y=alt.Y("day:O", title="Day"),
                color=alt.Color("count:Q", scale=alt.Scale(scheme="greens")),
                tooltip=["status","count"]
            ).properties(height=400)
            st.altair_chart(chart, use_container_width=True)

            # Toy predictive model
            df["missed"] = df["status"]=="Missed"
            X = df[["hour","day"]]
            y = df["missed"]
            pipe = Pipeline([
                ("pre", ColumnTransformer([("cat",OneHotEncoder(),["day"])], remainder="passthrough")),
                ("clf", LogisticRegression())
            ])
            pipe.fit(X,y)
            c1,c2 = st.columns(2)
            with c1:
                hour_test = st.slider("Hour",0,23,8)
            with c2:
                day_test  = st.selectbox("Day", df["day"].unique())
            prob = pipe.predict_proba(pd.DataFrame([[hour_test,day_test]], columns=["hour","day"]))[0][1]
            st.metric("Risk of Missing", f"{prob*100:.1f} %")

def page_logout():
    st.session_state.logged_in=False
    st.session_state.user_id=None
    st.success("Logged out.")
    st.session_state.rerun=True
    st.stop()

# ──────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────
query_params = st.experimental_get_query_params()
route = (query_params.get("page") or ["home"])[0]

if route=="home":           page_home()
elif route=="register":     page_register()
elif route=="login":        page_login()
elif route=="dashboard":    page_dashboard() if st.session_state.logged_in else page_login()
elif route=="logout":       page_logout()
else:                       page_home()

# ──────────────────────────────────────────────────────────────
# Safe rerun handler
# ──────────────────────────────────────────────────────────────
if st.session_state.get("rerun"):
    st.session_state.rerun=False
    st.experimental_rerun()
