import streamlit as st

st.set_page_config(page_title="Genome Firewall", page_icon="🧬", layout="centered")

# Demo credentials — doctors only. Replace with real auth for production.
DOCTORS = {
    "dr.smith": "genome123",
    "dr.patel": "firewall456",
    "demo":     "demo",
}

st.markdown("""
<style>
  .stApp {
    background: radial-gradient(ellipse at top left, #0f2027 0%, #203a43 45%, #2c5364 100%);
  }
  #MainMenu, footer, header {visibility: hidden;}
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

  .disclaimer {
    text-align:center; color:#6b8a99; font-size:0.78rem;
    padding:1.5rem 1rem 0 1rem; max-width:640px; margin:1rem auto 0 auto;
  }
</style>

<div class="hero">
  <div class="dna">🧬</div>
  <div class="hero-badge">AI · Biosecurity · Defensive</div>
  <h1 class="hero-title">Welcome to the<br/>Genome Firewall</h1>
  <p class="hero-sub">
    Predict which antibiotics will work — from a bacterial genome, in minutes.
    An AI defense system against the rise of superbugs.
  </p>
</div>
""", unsafe_allow_html=True)

if "authed" not in st.session_state:
    st.session_state.authed = False

if not st.session_state.authed:
    st.markdown("""
    <div class="login-wrap">
      <div class="login-note">Restricted Access</div>
      <div class="login-title">Clinician Sign-In</div>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid.form("login", clear_on_submit=False):
        user = st.text_input("Medical ID / Username")
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            if DOCTORS.get(user) == pwd:
                st.session_state.authed = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid credentials. This portal is restricted to verified clinicians.")

    st.markdown("""
    <div class="disclaimer">
      Access limited to licensed healthcare professionals. All activity is logged.
      Research prototype — every antibiotic-response report must be confirmed by standard laboratory testing.
    </div>
    """, unsafe_allow_html=True)
else:
    top_l, top_r = st.columns([4, 1])
    with top_l:
        st.markdown(f"<div style='color:#7fdcff;font-size:0.85rem;'>Signed in as <b>{st.session_state.user}</b></div>", unsafe_allow_html=True)
    with top_r:
        if st.button("Sign out"):
            st.session_state.authed = False
            st.rerun()

    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
      <h2 style="color:#ffffff; margin-bottom:0.25rem;">Upload Bacterial Genome</h2>
      <p style="color:#b8d4e3; margin:0;">Provide a quality-checked assembly in FASTA format (<code style="color:#7fdcff;">.fna</code>, .fa, .fasta).</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drag & drop or browse",
        type=["fna", "fa", "fasta"],
        accept_multiple_files=False,
        label_visibility="collapsed",
    )

    if uploaded is not None:
        size_kb = len(uploaded.getbuffer()) / 1024
        st.success(f"Received **{uploaded.name}** ({size_kb:,.1f} KB)")
        st.markdown("<p style='text-align:center;color:#b8d4e3;'>Ready to run the Genome Firewall pipeline.</p>", unsafe_allow_html=True)
        st.button("Analyze genome →", type="primary", disabled=True, help="Pipeline coming next")
    else:
        st.markdown("<p style='text-align:center;color:#6b8a99;font-size:0.85rem;'>All uploads are processed locally for this prototype.</p>", unsafe_allow_html=True)
