"""
CerviScan — Main Entry Point
Run: py -3.11 -m streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="CerviScan | Cervical Cancer Screening",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #fce4ec !important;
  }
  .block-container { padding-top: 1rem !important; background-color: transparent !important; }
  hr { display: none !important; }

  /* Hide the top multipage nav links that streamlit auto-generates */
  [data-testid="stSidebarNav"] { display: none !important; }
  header[data-testid="stHeader"] { display: none !important; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #c2185b 0%, #e91e8c 100%) !important;
  }
  section[data-testid="stSidebar"] * { color: white !important; }

  /* Buttons */
  .stButton > button {
    background: linear-gradient(135deg, #c2185b, #e91e8c) !important;
    color: white !important; border: none !important;
    border-radius: 30px !important; padding: 0.55rem 2rem !important;
    font-weight: 500 !important; box-shadow: 0 4px 15px rgba(194,24,91,0.3) !important;
    transition: all 0.3s ease !important; cursor: pointer !important;
  }
  .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(194,24,91,0.45) !important;
  }
  .stDownloadButton > button {
    background: linear-gradient(135deg, #c2185b, #e91e8c) !important;
    color: white !important; border: none !important;
    border-radius: 30px !important; cursor: pointer !important;
  }

  /* ALL inputs */
  .stTextInput input, .stNumberInput input, .stTextArea textarea {
    background-color: #ffffff !important; color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    caret-color: #c2185b !important; cursor: text !important;
    border: 2px solid #f8bbd0 !important; border-radius: 10px !important;
    font-size: 0.95rem !important;
  }
  .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
    background-color: #ffffff !important; color: #000000 !important;
    -webkit-text-fill-color: #000000 !important; caret-color: #c2185b !important;
    border-color: #e91e8c !important;
    box-shadow: 0 0 0 3px rgba(233,30,140,0.15) !important; outline: none !important;
  }
  .stTextInput input::placeholder, .stNumberInput input::placeholder,
  .stTextArea textarea::placeholder {
    color: #aaaaaa !important; -webkit-text-fill-color: #aaaaaa !important; opacity: 1 !important;
  }
  .stTextInput label, .stNumberInput label, .stTextArea label {
    color: #5c3d5e !important; font-weight: 600 !important; font-size: 0.92rem !important;
  }
  .stNumberInput > div, .stNumberInput > div > div { background-color: #ffffff !important; }

  /* Cards */
  .card {
    background: white; border-radius: 20px; padding: 2rem;
    box-shadow: 0 4px 30px rgba(194,24,91,0.08);
    border: 1px solid #f8bbd0; margin-bottom: 1.5rem;
  }
  h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #c2185b !important; }
</style>
""", unsafe_allow_html=True)

for key, val in {
    "logged_in": False, "username": "", "current_page": "login",
    "patient_data": {}, "prediction_result": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── NOT LOGGED IN — hide sidebar completely ───────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("""
    <style>
      section[data-testid="stSidebar"]      { display: none !important; }
      button[data-testid="collapsedControl"] { display: none !important; }
      [data-testid="collapsedControl"]       { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.current_page == "signup":
        from pages.signup import show_signup
        show_signup()
    else:
        from pages.login import show_login
        show_login()

# ── LOGGED IN ─────────────────────────────────────────────────────────────────
else:
    with st.sidebar:
        # Hide the auto-generated page nav at the top of sidebar
        st.markdown("""
        <style>
          [data-testid="stSidebarNav"] { display: none !important; }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style='text-align:center; padding:1.2rem 0 0.5rem;'>
          <div style='font-size:2.8rem;'>🌸</div>
          <div style='font-family:Playfair Display,serif; font-size:1.3rem;
                      font-weight:700; margin-top:4px;'>CerviScan</div>
          <div style='font-size:0.78rem; opacity:0.85; margin-top:2px;'>
            Cervical Cancer Screening
          </div>
        </div>
        <div style='border-top:1px solid rgba(255,255,255,0.3); margin:0.8rem 0;'></div>
        <div style='padding:0 0.5rem 0.6rem;'>
          <div style='font-size:0.72rem; opacity:0.72; letter-spacing:1px;
                      text-transform:uppercase;'>Logged in as</div>
          <div style='font-weight:700; font-size:1rem; margin-top:3px;'>
             &nbsp;{st.session_state.username}
          </div>
        </div>
        <div style='border-top:1px solid rgba(255,255,255,0.3); margin:0.3rem 0 0.8rem;'></div>
        <div style='font-size:0.72rem; opacity:0.72; letter-spacing:1.5px;
                    text-transform:uppercase; padding-left:0.3rem; margin-bottom:0.5rem;'>
           &nbsp;Navigation Menu
        </div>
        """, unsafe_allow_html=True)

        page = st.radio(
            "Navigation",
            ["  Dashboard", "  Home — Patient Form", "  Prediction", "  Report"],
            label_visibility="collapsed"
        )
        page_map = {
            "  Dashboard":           "dashboard",
            "  Home — Patient Form":  "home",
            "  Prediction":           "prediction",
            "  Report":               "report",
        }
        st.session_state.current_page = page_map.get(page, "dashboard")

        st.markdown(
            "<div style='border-top:1px solid rgba(255,255,255,0.3); margin:1rem 0;'></div>",
            unsafe_allow_html=True
        )
        if st.button("  Logout", use_container_width=True):
            for k, v in {
                "logged_in": False, "username": "", "current_page": "login",
                "patient_data": {}, "prediction_result": None,
            }.items():
                st.session_state[k] = v
            st.rerun()

    current = st.session_state.current_page
    if current == "dashboard":
        from pages.dashboard import show_dashboard; show_dashboard()
    elif current == "home":
        from pages.home import show_home; show_home()
    elif current == "prediction":
        from pages.prediction import show_prediction; show_prediction()
    elif current == "report":
        from pages.report import show_report; show_report()