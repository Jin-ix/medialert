"""
MediPredict – Streamlit v2
Modern redesign + safe rerun logic
Author : Jinix Chacko | 10 Jun 2025
"""

# ──────────────────────────────────────────────────────────────
# Imports & Config
# ──────────────────────────────────────────────────────────────
import os, sqlite3, hashlib
from datetime import datetime
import pandas as pd
import altair as alt
import streamlit as st
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

st.set_page_config(page_title="MediPredict", page_icon="💊", layout="wide")

# ──────────────────────────────────────────────────────────────
# Global styling (CSS)
# ──────────────────────────────────────────────────────────────
PRIMARY = "#344cfd"        # slate-blue
ACCENT  = "#00c6ff"        # cyan gradient end
LIGHT   = "#f4f6fb"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
html, body {{
  font-family:'Inter',sans-serif;
  background:{LIGHT};
}}
/* Glass cards */
.block-container > div > div:nth-child(1) {{
  background:rgba(255,255,255,.8);
  backdrop-filter:blur(10px);
  border-radius:14px;
  padding:2.2rem 2.5rem;
  box-shadow:0 8px 25px rgba(0,0,0,.08);
}}
/* Header bar */
header {{
  background:linear-gradient(90deg,{PRIMARY} 0%,{ACCENT} 100%);
  height:64px;
}}
header h1 {{
  color:#fff!important; font-size:1.3rem!important;
}}
/* Hide default Streamlit menu & footer */
#MainMenu, footer {{visibility:hidden;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# DB utils
# ──────────────────────────────────────────────────────────────
DB = "medipredict.db"
def hash_pw(pw:str)->str:
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    if not os.path.exists(DB):
        open(DB,"w").close()
    with sqlite3.connect(DB) as c:
        cur = c.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE,
          password TEXT,
          age INTEGER, gender TEXT );
        CREATE TABLE IF NOT EXISTS meds (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER,
          med_name TEXT, dosage TEXT, schedule TEXT );
        CREATE TABLE IF NOT EXISTS doses (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER, med_id INTEGER,
          timestamp TEXT, status TEXT CHECK(status IN ('Taken','Missed')) );
        """)
init_db()

# ──────────────────────────────────────────────────────────────
# Session defaults
# ──────────────────────────────────────────────────────────────
if "uid" not in st.session_state:
    st.session_state.update({
        "uid":None,          # logged-in user id
        "page":"home",       # router
        "rerun":False,       # safe-rerun flag
    })

# ──────────────────────────────────────────────────────────────
# Components
# ──────────────────────────────────────────────────────────────
def nav_link(label,page_key):
    if st.button(label,use_container_width=True):
        st.session_state.page=page_key

def sidebar():
    with st.sidebar:
        st.markdown("## 💊 MediPredict")
        if st.session_state.uid:
            nav_link("🏠 Home"      ,"home")
            nav_link("📋 Dashboard","dash")
            nav_link("🚪 Logout"   ,"logout")
        else:
            nav_link("🏠 Home"     ,"home")
            nav_link("🔐 Login"    ,"login")
            nav_link("🆕 Register" ,"reg")

def page_home():
    st.header("Welcome to MediPredict")
    st.write("""
    A smart medicine-adherence companion that reminds patients,
    visualises habits, and predicts the risk of skipping doses.
    """)
    st.info("Use the sidebar to navigate.")

def page_register():
    st.header("Create Account")
    with st.form("reg"):
        u = st.text_input("Username")
        p = st.text_input("Password",type="password")
        age = st.number_input("Age",0,120)
        gender = st.selectbox("Gender",["Male","Female","Other"])
        ok = st.form_submit_button("Register")
    if ok:
        if not u or not p:
            st.error("Username & password required.")
        else:
            try:
                with sqlite3.connect(DB) as c:
                    c.execute("INSERT INTO users (username,password,age,gender) VALUES (?,?,?,?)",
                              (u,hash_pw(p),age,gender))
                st.success("Account created ✔️")
                st.session_state.page="login"
                st.session_state.rerun=True
                st.stop()
            except sqlite3.IntegrityError:
                st.error("Username taken.")

def page_login():
    st.header("Log In")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password",type="password")
        ok = st.form_submit_button("Login")
    if ok:
        with sqlite3.connect(DB) as c:
            cur=c.execute("SELECT id FROM users WHERE username=? AND password=?",
                          (u,hash_pw(p))).fetchone()
        if cur:
            st.session_state.uid=cur[0]
            st.success("Logged in ✔️")
            st.session_state.page="dash"
            st.session_state.rerun=True
            st.stop()
        else:
            st.error("Invalid credentials.")

def page_logout():
    st.session_state.uid=None
    st.session_state.page="home"
    st.success("Logged out.")
    st.session_state.rerun=True
    st.stop()

def page_dashboard():
    st.header("Dashboard")
    tabs=st.tabs(["💊 Medicines","📝 Log Dose","📊 Insights"])
    uid=st.session_state.uid

    # ─── Medicines tab ─────────────────────────────────────
    with tabs[0]:
        st.subheader("Your medicines")
        with sqlite3.connect(DB) as c:
            meds=pd.read_sql("SELECT * FROM meds WHERE user_id=?",c,params=(uid,))
        st.dataframe(meds.drop(columns=["user_id","id"]) if not meds.empty else meds)
        st.markdown("#### Add / Update")
        with st.form("medform"):
            name,dose,sched=st.columns(3)
            with name:  m=st.text_input("Name")
            with dose:  d=st.text_input("Dosage")
            with sched: s=st.text_input("Schedule")
            ok=st.form_submit_button("Save")
        if ok and m:
            with sqlite3.connect(DB) as c:
                c.execute("INSERT INTO meds (user_id,med_name,dosage,schedule) VALUES (?,?,?,?)",
                          (uid,m,d,s))
            st.success("Saved")
            st.session_state.rerun=True
            st.stop()

    # ─── Log Dose tab ─────────────────────────────────────
    with tabs[1]:
        st.subheader("Log a dose")
        with sqlite3.connect(DB) as c:
            meds=pd.read_sql("SELECT id,med_name FROM meds WHERE user_id=?",c,params=(uid,))
        if meds.empty:
            st.info("Add a medicine first.")
        else:
            med=st.selectbox("Medicine",meds.med_name)
            status=st.radio("Status",["Taken","Missed"],horizontal=True)
            if st.button("Save"):
                mid=int(meds.loc[meds.med_name==med,"id"].values[0])
                with sqlite3.connect(DB) as c:
                    c.execute("INSERT INTO doses (user_id,med_id,timestamp,status) VALUES (?,?,?,?)",
                              (uid,mid,datetime.now().isoformat(),status))
                st.success("Logged.")
                st.session_state.rerun=True
                st.stop()

    # ─── Insights tab ─────────────────────────────────────
    with tabs[2]:
        st.subheader("Adherence heat-map & predictor")
        with sqlite3.connect(DB) as c:
            df=pd.read_sql("SELECT * FROM doses WHERE user_id=?",c,params=(uid,))
        if df.empty:
            st.info("No logs yet.")
        else:
            df["timestamp"]=pd.to_datetime(df.timestamp)
            df["hour"]=df.timestamp.dt.hour
            df["day"]=df.timestamp.dt.day_name()
            heat=df.groupby(["day","hour","status"]).size().reset_index(name="count")
            chart=alt.Chart(heat).mark_rect().encode(
                x=alt.X("hour:O"), y=alt.Y("day:O"),
                color=alt.Color("count:Q",scale=alt.Scale(scheme="blues")),
                tooltip=["status","count"]).properties(height=400)
            st.altair_chart(chart,use_container_width=True)

            # quick model
            df["miss"]=df.status=="Missed"
            X=df[["hour","day"]]; y=df["miss"]
            pipe=Pipeline([
                ("pre",ColumnTransformer([("ohe",OneHotEncoder(),["day"])],remainder="passthrough")),
                ("clf",LogisticRegression())
            ]).fit(X,y)
            h=st.slider("Hour",0,23,8)
            d=st.selectbox("Day",sorted(df.day.unique()))
            prob=pipe.predict_proba(pd.DataFrame([[h,d]],columns=["hour","day"]))[0][1]
            st.metric("Risk of missing",f"{prob*100:.1f}%")

# ──────────────────────────────────────────────────────────────
# Router & layout
# ──────────────────────────────────────────────────────────────
sidebar()
page = st.session_state.page

if page=="home":      page_home()
elif page=="reg":     page_register()
elif page=="login":   page_login()
elif page=="dash":    page_dashboard() if st.session_state.uid else page_login()
elif page=="logout":  page_logout()

# ──────────────────────────────────────────────────────────────
# Deferred safe rerun
# ──────────────────────────────────────────────────────────────
if st.session_state.rerun:
    st.session_state.rerun=False
    st.experimental_rerun()
