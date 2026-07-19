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
    color:#7fdcff; text-align:center; font-size:0.82rem;
    font-weight:800;
    letter-spacing:0.18em; text-transform:uppercase; margin-bottom:1rem;
  }
  .stTextInput label {
    color:#b8d4e3 !important; font-size:0.85rem !important;
    width:100%; text-align:center; display:block;
  }
  div[data-testid="stForm"] { text-align:center; }
  .stTextInput input {
    background: #f5f7f9 !important;
    color: #12211C !important;
    border: 1px solid rgba(127,220,255,0.3) !important;
    text-align:left !important;
    padding-left:0.9rem !important;
  }
  .stTextInput input::placeholder {
    color: rgba(18,33,28,0.45) !important;
    text-align:left;
  }
  /* Hide Streamlit's "Press Enter to submit form" hint that overlaps the input */
  div[data-testid="InputInstructions"],
  .stTextInput [data-testid="InputInstructions"] {
    display: none !important;
  }

  /* ---- Selectbox, multiselect, number input, textarea — dark theme ---- */
  .stSelectbox label, .stMultiSelect label, .stNumberInput label, .stTextArea label,
  .stDateInput label, .stTimeInput label, .stRadio label {
    color: #b8d4e3 !important; font-size: 0.85rem !important; font-weight: 500;
  }

  /* Selectbox / multiselect base container — light bg, dark text */
  .stSelectbox div[data-baseweb="select"] > div,
  .stMultiSelect div[data-baseweb="select"] > div {
    background: #f5f7f9 !important;
    border: 1px solid rgba(127,220,255,0.3) !important;
    color: #12211C !important;
    min-height: 40px;
  }
  .stSelectbox div[data-baseweb="select"] span,
  .stMultiSelect div[data-baseweb="select"] span,
  .stSelectbox div[data-baseweb="select"] input,
  .stMultiSelect div[data-baseweb="select"] input {
    color: #12211C !important;
  }
  .stSelectbox div[data-baseweb="select"] [aria-hidden="true"],
  .stMultiSelect div[data-baseweb="select"] [aria-hidden="true"] {
    color: rgba(18,33,28,0.5) !important;
  }
  /* Multiselect chosen-tag pills — light with dark text */
  .stMultiSelect [data-baseweb="tag"] {
    background: #e6f4fa !important;
    border: 1px solid #7fdcff !important;
    color: #12211C !important;
  }
  .stMultiSelect [data-baseweb="tag"] span { color: #12211C !important; }
  .stMultiSelect [data-baseweb="tag"] svg { fill: #12211C !important; }

  /* Number input — light */
  .stNumberInput input {
    background: #f5f7f9 !important;
    color: #12211C !important;
    border: 1px solid rgba(127,220,255,0.3) !important;
  }
  .stNumberInput button {
    background: #eef2f5 !important;
    color: #12211C !important;
    border: 1px solid rgba(127,220,255,0.3) !important;
  }
  .stNumberInput button svg { fill: #12211C !important; }

  /* Dropdown chevron on selectbox */
  .stSelectbox div[data-baseweb="select"] svg,
  .stMultiSelect div[data-baseweb="select"] svg {
    fill: #12211C !important;
  }

  /* Dropdown popover — light background, dark text */
  div[data-baseweb="popover"],
  div[data-baseweb="popover"] * {
    background: #ffffff !important;
    background-color: #ffffff !important;
    color: #12211C !important;
    border-color: rgba(127,220,255,0.35) !important;
  }
  div[data-baseweb="popover"] {
    box-shadow: 0 10px 30px rgba(0,0,0,0.35) !important;
    border: 1px solid rgba(127,220,255,0.35) !important;
  }
  /* Hover / selected states — soft cyan */
  div[data-baseweb="popover"] [role="option"]:hover,
  div[data-baseweb="popover"] [role="option"]:hover *,
  div[data-baseweb="popover"] li:hover,
  div[data-baseweb="popover"] li:hover *,
  div[data-baseweb="popover"] [aria-selected="true"],
  div[data-baseweb="popover"] [aria-selected="true"] * {
    background: #e6f4fa !important;
    background-color: #e6f4fa !important;
    color: #0f4a63 !important;
  }

  /* Help tooltip icon */
  .stTooltipIcon svg { fill: #7fdcff !important; }
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

  .demo-creds {
    max-width: 320px; margin: 1.25rem auto 0 auto;
    padding: 0.9rem 1.1rem;
    background: rgba(255,180,60,0.06);
    border: 1px dashed rgba(255,180,60,0.4);
    border-radius: 10px;
  }
  .demo-creds-title {
    color: #ffd479; text-align:center;
    font-size:0.7rem; font-weight:800;
    letter-spacing:0.18em; text-transform:uppercase;
    margin-bottom:0.55rem;
  }
  .demo-creds-row {
    display:flex; justify-content:space-between; align-items:baseline;
    padding: 0.2rem 0.35rem;
    font-size:0.88rem;
  }
  .demo-creds-row .k { color:#8fb3c4; }
  .demo-creds-row .v { color:#ffffff; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-weight:700; }

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

  /* ---- patient summary bar (shown on upload step) ---- */
  .patient-summary-bar {
    background: rgba(0,229,255,0.05);
    border: 1px solid rgba(127,220,255,0.25);
    border-radius: 999px;
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
    color: #b8d4e3;
    margin: 0.5rem 0;
  }
  .patient-summary-bar .ps-label {
    color: #7fdcff; font-weight: 700; text-transform: uppercase;
    font-size: 0.7rem; letter-spacing: 0.15em; margin-right: 0.5rem;
  }
  .patient-summary-bar .ps-value { color: #ffffff; }

  /* ---- patient / clinical context card ---- */
  .patient-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(127,220,255,0.2);
    border-radius: 16px; padding: 1.5rem 1.75rem;
    backdrop-filter: blur(10px);
    margin: 1.25rem 0;
  }
  .patient-card .patient-title {
    color:#ffffff; font-weight:700; font-size:1.05rem;
    margin: 0 0 1rem 0;
  }
  .patient-card .patient-title .patient-num { color:#7fdcff; margin-right:0.35rem; }
  .patient-card .patient-name {
    color:#ffffff; font-size:1.6rem; font-weight:700;
    line-height:1.15; letter-spacing:-0.01em;
    margin: 0 0 1rem 0;
  }
  .patient-grid {
    display: grid;
    grid-template-columns: 170px 1fr;
    row-gap: 0.55rem; column-gap: 1rem;
    font-size: 0.92rem; line-height: 1.4;
  }
  .patient-grid .k { color:#8fb3c4; }
  .patient-grid .v { color:#ffffff; }
  .patient-note {
    color:#8fb3c4; font-size:0.82rem; line-height:1.55;
    margin-top: 1rem; padding-top: 0.9rem;
    border-top: 1px solid rgba(127,220,255,0.12);
  }
  .patient-note b { color:#ffd479; font-weight:700; }

  div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(127,220,255,0.2);
    border-radius: 14px;
    margin-top: -0.7rem;
    margin-bottom: 1.1rem;
  }
  div[data-testid="stExpander"] summary {
    background-color: transparent !important;
    color:#7fdcff !important;
    font-weight: 600;
    font-size: 0.82rem;
    letter-spacing: 0.02em;
  }
  div[data-testid="stExpander"] summary:hover {
    background-color: rgba(0,229,255,0.05) !important;
  }
  div[data-testid="stExpander"] summary p {
    color:#7fdcff !important;
  }
  div[data-testid="stExpander"] details {
    background-color: transparent !important;
  }
  .lit-note {
    color:#6b8a99; font-size:0.78rem; margin: 0 0 0.85rem 0; line-height:1.5;
  }
  .lit-ref {
    background: rgba(0,229,255,0.03);
    border: 1px solid rgba(127,220,255,0.15);
    border-left: 3px solid rgba(0,229,255,0.5);
    border-radius: 0 10px 10px 0;
    padding: 0.75rem 1rem;
    margin-bottom: 0.75rem;
  }
  .lit-ref:last-child { margin-bottom: 0; }
  .lit-ref-title { color:#e8f6ff; font-weight:600; font-size:0.92rem; line-height:1.4; }
  .lit-tag {
    display: inline-block; margin-left: 0.5rem; margin-top: 0.15rem;
    font-size: 0.63rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
    color:#7fdcff; background: rgba(0,229,255,0.08); border: 1px solid rgba(0,229,255,0.3);
    border-radius: 6px; padding: 0.15rem 0.5rem; vertical-align: middle; white-space: nowrap;
  }
  .lit-meta { color:#8fb3c4; font-size:0.76rem; margin: 0.3rem 0 0.5rem 0; }
  .lit-quote { color:#b8d4e3; font-size:0.85rem; font-style: italic; line-height:1.55; margin-bottom:0.5rem; }
  .lit-link { color:#7fdcff; font-size:0.8rem; text-decoration:none; font-weight:600; }
  .lit-link:hover { text-decoration: underline; }
  .lit-empty { color:#6b8a99; font-size:0.85rem; padding: 0.25rem 0; }
</style>
"""

VERDICT_META = {
    "work":   {"pill_class": "pill-green", "fill_class": "conf-fill-green", "label": "Likely to work"},
    "fail":   {"pill_class": "pill-red",   "fill_class": "conf-fill-red",   "label": "Likely to fail"},
    "nocall": {"pill_class": "pill-amber", "fill_class": "conf-fill-amber", "label": "No-call"},
}


def inject_global_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_patient_card(patient: dict, section_number: int = 4):
    """Render a patient / clinical-context card. `patient` dict keys are optional."""
    rows = [
        ("Age / sex",          patient.get("age_sex")),
        ("Setting",             patient.get("setting")),
        ("Body site infected", patient.get("body_site")),
        ("Suspected source",   patient.get("suspected_source")),
        ("Symptom onset",      patient.get("onset")),
        ("Comorbidities",      patient.get("comorbidities")),
        ("Prior antibiotics",  patient.get("prior_antibiotics")),
        ("Allergies",          patient.get("allergies")),
        ("Renal function",     patient.get("renal_function")),
    ]
    grid_html = "".join(
        f"<div class='k'>{k}</div><div class='v'>{v}</div>"
        for k, v in rows if v
    )
    name = patient.get("name") or "Unnamed patient"
    st.markdown(f"""
    <div class="patient-card">
      <div class="patient-title"><span class="patient-num">{section_number} ·</span>Patient details</div>
      <div class="patient-name">{name}</div>
      <div class="patient-grid">{grid_html}</div>
      <div class="patient-note">
        Clinical context is shown to aid interpretation and prioritization. It is
        <b>not</b> used to compute the genomic probabilities and does not change model output.
      </div>
    </div>
    """, unsafe_allow_html=True)


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
