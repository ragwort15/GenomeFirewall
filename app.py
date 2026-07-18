import streamlit as st
from style import inject_global_css

st.set_page_config(page_title="Genome Firewall", page_icon="🧬", layout="centered")

# Demo credentials — doctors only. Replace with real auth for production.
DOCTORS = {
    "dr.smith": "genome123",
    "dr.patel": "firewall456",
    "demo":     "demo",
}

inject_global_css()

st.markdown("""
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
            st.session_state.pop("uploaded_filename", None)
            st.session_state.pop("patient", None)
            st.rerun()

    # ---- Step 1: patient intake ----
    if "patient" not in st.session_state:
        st.markdown("""
        <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
          <h2 style="color:#ffffff; margin-bottom:0.25rem;">Patient / Clinical Context</h2>
          <p style="color:#b8d4e3; margin:0;">Enter the patient details for this isolate. Context aids interpretation — it does <b>not</b> change the genomic probabilities.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("patient_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                age = st.number_input("Age", min_value=0, max_value=120, value=58, step=1)
            with c2:
                sex = st.selectbox("Sex", ["Female", "Male", "Other / prefer not to say"])

            c3, c4 = st.columns(2)
            with c3:
                setting = st.text_input("Care setting", value="ICU, day 6",
                                        help="e.g. ICU day 6, general ward, outpatient")
            with c4:
                egfr = st.number_input("eGFR (mL/min/1.73m²)", min_value=0, max_value=200, value=44, step=1)

            source = st.text_input("Suspected infection source",
                                   value="Catheter-associated UTI → bacteremia")
            prior_abx = st.text_input("Prior antibiotics (last 30 days)",
                                      value="Ceftriaxone (5 d), meropenem (2 d)")
            allergies = st.text_input("Known drug allergies",
                                      value="Penicillin (rash)")

            submitted_patient = st.form_submit_button("Continue to genome upload →", type="primary")
            if submitted_patient:
                st.session_state.patient = {
                    "age_sex": f"{age} · {sex}",
                    "setting": setting,
                    "suspected_source": source,
                    "prior_antibiotics": prior_abx,
                    "allergies": allergies,
                    "renal_function": f"eGFR {egfr}" + (" (dose-adjust aminoglycosides)" if egfr < 60 else ""),
                }
                st.rerun()

    # ---- Step 2: FASTA upload ----
    else:
        patient_summary = f"{st.session_state.patient['age_sex']} · {st.session_state.patient['setting']}"
        edit_col1, edit_col2 = st.columns([4, 1])
        with edit_col1:
            st.markdown(f"""
            <div class="patient-summary-bar">
              <span class="ps-label">Patient:</span>
              <span class="ps-value">{patient_summary}</span>
            </div>
            """, unsafe_allow_html=True)
        with edit_col2:
            if st.button("Edit"):
                st.session_state.pop("patient", None)
                st.session_state.pop("uploaded_filename", None)
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
            st.session_state.uploaded_filename = uploaded.name
            size_kb = len(uploaded.getbuffer()) / 1024
            st.success(f"Received **{uploaded.name}** ({size_kb:,.1f} KB)")
            st.markdown("<p style='text-align:center;color:#b8d4e3;'>Ready to run the Genome Firewall pipeline.</p>", unsafe_allow_html=True)
            if st.button("Analyze genome →", type="primary"):
                st.switch_page("pages/1_Results.py")
        else:
            st.markdown("<p style='text-align:center;color:#6b8a99;font-size:0.85rem;'>All uploads are processed locally for this prototype.</p>", unsafe_allow_html=True)
