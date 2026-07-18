import streamlit as st

GLOBAL_CSS = """
<style>
  .stApp {
    background: radial-gradient(ellipse at top left, #0f2027 0%, #203a43 45%, #2c5364 100%);
  }
  #MainMenu, footer, header {visibility: hidden;}
  [data-testid="stSidebarNav"] {display: none;}
  section[data-testid="stSidebar"] {display: none;}
  .block-container {
    padding-top: 3rem; max-width: 900px;
    padding-left: 1rem !important; padding-right: 1rem !important;
    margin-left: auto !important; margin-right: auto !important;
  }
  .hero * { text-align: center; }

  .hero {
    text-align: center; padding: 2rem 1rem 1.5rem 1rem;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
  }
  .hero-badge {
    display: inline-block; padding: 0.4rem 1rem;
    border: 1px solid rgba(0,229,255,0.4); border-radius: 999px;
    color: #7fdcff; font-size: 0.75rem;
    letter-spacing: 0.2em; text-transform: uppercase;
    margin-bottom: 1.25rem; background: rgba(0,229,255,0.05);
  }
  .hero-title {
    font-size: 3.5rem; font-weight: 800;
    background: linear-gradient(90deg,#00e5ff 0%,#7fdcff 40%,#ffffff 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin: 0 0 1rem 0;
    line-height: 1.1; letter-spacing: -0.02em;
  }
  .hero-sub {
    font-size: 1.1rem; color: #b8d4e3;
    max-width: 620px; margin-left: auto; margin-right: auto;
    margin-bottom: 1.5rem; line-height: 1.6;
    text-align: center; padding: 0 1rem;
  }
  .dna {
    font-size: 2.5rem;
    filter: drop-shadow(0 0 20px rgba(0,229,255,0.6));
    animation: float 3s ease-in-out infinite;
  }
  @keyframes float { 0%,100%{transform:translateY(0);} 50%{transform:translateY(-8px);} }

  .login-wrap {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(127,220,255,0.2);
    border-radius: 16px; padding: 1.5rem 1.75rem 0.5rem 1.75rem;
    backdrop-filter: blur(10px);
    max-width: 420px; margin: 1rem auto 1rem auto;
  }
  .login-title {
    color:#ffffff; text-align:center; font-weight:600;
    font-size:1.05rem; margin-bottom:0.25rem;
  }
  .login-note {
    color:#7fdcff; text-align:center; font-size:0.78rem;
    letter-spacing:0.15em; text-transform:uppercase; margin-bottom:1rem;
  }
  .stTextInput label {
    color:#b8d4e3 !important; font-size:0.85rem !important;
    width:100%; text-align:center; display:block;
  }
  .stTextInput input { text-align:center; }
  div[data-testid="stForm"] { text-align:center; }
  .stTextInput input {
    background: rgba(0,0,0,0.25) !important;
    color:#ffffff !important;
    border:1px solid rgba(127,220,255,0.25) !important;
  }
  .stButton button {
    width:100%; background: linear-gradient(90deg,#00e5ff,#0088cc);
    color:#001018; font-weight:700; border:none; border-radius:8px;
    padding:0.6rem 1rem;
  }
  .stButton button:hover { filter: brightness(1.1); }
  .stButton button:disabled { opacity: 0.5; }

  .disclaimer {
    text-align:center; color:#6b8a99; font-size:0.78rem;
    padding:1.5rem 1rem 0 1rem; max-width:640px; margin:1rem auto 0 auto;
  }

  /* ---- shared pill / card system (results dashboard) ---- */
  .pill {
    display: inline-block; padding: 0.3rem 0.85rem;
    border-radius: 999px; font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase; white-space: nowrap;
  }
  .pill-green { color:#6ffcbe; background:rgba(0,230,150,0.10); border:1px solid rgba(0,230,150,0.45); }
  .pill-red   { color:#ff9d94; background:rgba(255,90,90,0.10); border:1px solid rgba(255,90,90,0.45); }
  .pill-amber { color:#ffd479; background:rgba(255,180,60,0.10); border:1px solid rgba(255,180,60,0.45); }
  .pill-cyan  { color:#7fdcff; background:rgba(0,229,255,0.08); border:1px solid rgba(0,229,255,0.4); }

  .stat-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(127,220,255,0.18);
    border-radius: 14px; padding: 1rem 0.75rem;
    text-align: center; backdrop-filter: blur(10px); height: 100%;
  }
  .stat-card .stat-value { font-size: 1.9rem; font-weight: 800; color:#ffffff; line-height:1.1; }
  .stat-card .stat-label { font-size: 0.72rem; color:#8fb3c4; text-transform:uppercase; letter-spacing:0.08em; margin-top:0.4rem; }

  .drug-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(127,220,255,0.2);
    border-radius: 16px; padding: 1.25rem 1.5rem;
    backdrop-filter: blur(10px); margin-bottom: 1rem;
  }
  .drug-card-top { display:flex; align-items:center; justify-content:space-between; gap:0.75rem; margin-bottom:0.7rem; }
  .drug-name { color:#ffffff; font-size:1.15rem; font-weight:700; }
  .drug-meta-row { display:flex; flex-wrap:wrap; gap:0.5rem 1.25rem; margin: 0.35rem 0 0.6rem 0; }
  .drug-meta { color:#8fb3c4; font-size:0.8rem; }
  .drug-meta b { color:#b8d4e3; font-weight:600; }
  .drug-detail { color:#b8d4e3; font-size:0.88rem; margin-top:0.55rem; line-height:1.5; }

  .conf-row { display:flex; align-items:center; gap:0.6rem; margin: 0.3rem 0 0.1rem 0; }
  .conf-track { flex:1; height:8px; border-radius:999px; background: rgba(255,255,255,0.08); overflow:hidden; }
  .conf-fill { height:100%; border-radius:999px; }
  .conf-fill-green { background: linear-gradient(90deg,#00c98a,#6ffcbe); }
  .conf-fill-red   { background: linear-gradient(90deg,#ff5a5a,#ff9d94); }
  .conf-fill-amber { background: linear-gradient(90deg,#ffb43c,#ffd479); }
  .conf-value { color:#ffffff; font-weight:700; font-size:0.82rem; min-width:2.8rem; text-align:right; }

  .warning-banner {
    background: rgba(255,180,60,0.07);
    border: 1px solid rgba(255,180,60,0.35);
    border-radius: 14px; padding: 0.9rem 1.25rem;
    color:#ffd479; font-size:0.85rem; text-align:center;
    margin: 1rem auto 1.75rem auto; line-height:1.55;
  }

  .section-title {
    color:#ffffff; font-weight:700; font-size:1.3rem;
    margin: 2rem 0 0.25rem 0;
  }
  .section-sub { color:#8fb3c4; font-size:0.85rem; margin-bottom:1.1rem; }

  .coverage-footer {
    text-align:center; color:#5c7a89; font-size:0.75rem;
    padding: 2rem 1rem 1rem 1rem; line-height:1.7;
  }

  .perf-metric { text-align:center; padding: 0.4rem; }
  .perf-metric .val { color:#a8c8d8; font-size:1.05rem; font-weight:700; }
  .perf-metric .lbl { color:#5c7a89; font-size:0.65rem; text-transform:uppercase; letter-spacing:0.06em; margin-top:0.25rem; }

  div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(127,220,255,0.15);
    border-radius: 14px;
  }
  div[data-testid="stExpander"] summary { color:#8fb3c4 !important; font-size:0.88rem; }
</style>
"""

VERDICT_META = {
    "work":   {"pill_class": "pill-green", "fill_class": "conf-fill-green", "label": "Likely to work"},
    "fail":   {"pill_class": "pill-red",   "fill_class": "conf-fill-red",   "label": "Likely to fail"},
    "nocall": {"pill_class": "pill-amber", "fill_class": "conf-fill-amber", "label": "No-call"},
}


def inject_global_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_signed_in_header(user, on_sign_out_page="app.py", right_content=None):
    """Reusable 'Signed in as ... / Sign out' row, optionally with extra content on the left."""
    left, right = st.columns([4, 1])
    with left:
        st.markdown(
            f"<div style='color:#7fdcff;font-size:0.85rem;'>Signed in as <b>{user}</b></div>",
            unsafe_allow_html=True,
        )
        if right_content:
            st.markdown(right_content, unsafe_allow_html=True)
    with right:
        if st.button("Sign out"):
            st.session_state.authed = False
            st.session_state.pop("uploaded_filename", None)
            st.switch_page(on_sign_out_page)
