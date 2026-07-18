import json
from pathlib import Path

import streamlit as st
from style import inject_global_css, render_signed_in_header, render_patient_card, VERDICT_META

st.set_page_config(page_title="Genome Firewall — Results", page_icon="🧬", layout="centered")

inject_global_css()

if not st.session_state.get("authed") or not st.session_state.get("uploaded_filename"):
    st.switch_page("app.py")

DATA_PATH = Path(__file__).parent.parent / "data" / "mock_results.json"
with open(DATA_PATH, encoding="utf-8") as f:
    DATA = json.load(f)

antibiotics = DATA["antibiotics"]
coverage = DATA["coverage"]

filename = st.session_state.uploaded_filename
status_pill = f"<span class='pill pill-green'>{filename} — Quality-checked ✓</span>"
render_signed_in_header(st.session_state.user, right_content=f"<div style='margin-top:0.5rem;'>{status_pill}</div>")

st.markdown("""
<div class="hero" style="padding: 1rem 1rem 0.5rem 1rem;">
  <div class="hero-badge">AI · Biosecurity · Defensive</div>
  <h1 class="hero-title" style="font-size: 2.4rem;">Antibiotic-Response Report</h1>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="warning-banner">
  ⚠️ Research prototype. Every result below must be confirmed with standard laboratory testing before any treatment decision.
</div>
""", unsafe_allow_html=True)

# ---- Summary stat row ----
total = len(antibiotics)
n_work = sum(1 for a in antibiotics if a["verdict"] == "work")
n_fail = sum(1 for a in antibiotics if a["verdict"] == "fail")
n_nocall = sum(1 for a in antibiotics if a["verdict"] == "nocall")

stats = [
    ("Antibiotics assessed", total),
    ("Likely to work", n_work),
    ("Likely to fail", n_fail),
    ("No-call", n_nocall),
]
cols = st.columns(4)
for col, (label, value) in zip(cols, stats):
    with col:
        st.markdown(f"""
        <div class="stat-card">
          <div class="stat-value">{value}</div>
          <div class="stat-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

# ---- Antibiotic report cards ----
st.markdown("""
<div class="section-title">Per-Antibiotic Predictions</div>
<div class="section-sub">One card per antibiotic assessed against the uploaded assembly.</div>
""", unsafe_allow_html=True)

for a in antibiotics:
    meta = VERDICT_META[a["verdict"]]
    confidence_pct = round(a["confidence"] * 100)
    lit_entries = a.get("literature", [])
    st.markdown(f"""
    <div class="drug-card">
      <div class="drug-card-top">
        <div class="drug-name">{a['drug']}</div>
        <span class="pill {meta['pill_class']}">{meta['label']}</span>
      </div>
      <div class="conf-row">
        <div class="conf-track"><div class="conf-fill {meta['fill_class']}" style="width:{confidence_pct}%;"></div></div>
        <div class="conf-value">{confidence_pct}%</div>
      </div>
      <div class="drug-meta-row">
        <div class="drug-meta">Confidence: <b>calibrated score</b></div>
        <div class="drug-meta">Evidence: <b>{a['evidence']}</b></div>
      </div>
      <div class="drug-detail">{a['detail']}</div>
    </div>
    """, unsafe_allow_html=True)

    lit_label = f"📖  View literature & clinical research ({len(lit_entries)})" if lit_entries else "📖  No literature attached"
    with st.expander(lit_label, expanded=False):
        if not lit_entries:
            st.markdown(
                "<div class='lit-empty'>No literature retrieved for this determinant in this mock dataset.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='lit-note'>Evidence retrieved by paper-qa for the detected determinant × drug. Citations are illustrative in this mock.</div>",
                unsafe_allow_html=True,
            )
            for ref in lit_entries:
                st.markdown(f"""
                <div class="lit-ref">
                  <div class="lit-ref-title">{ref['title']}<span class="lit-tag">{ref['tag']}</span></div>
                  <div class="lit-meta">{ref['source']} · {ref['year']} · PMID {ref['pmid']}</div>
                  <div class="lit-quote">&ldquo;{ref['quote']}&rdquo;</div>
                  <a class="lit-link" href="{ref['url']}" target="_blank" rel="noopener">View source ↗</a>
                </div>
                """, unsafe_allow_html=True)

# ---- Patient / clinical context ----
patient_data = st.session_state.get("patient") or DATA.get("patient")
if patient_data:
    render_patient_card(patient_data, section_number=4)

# ---- Coverage footer ----
st.markdown(f"""
<div class="coverage-footer">
  Coverage: {coverage['species']} only · Antibiotics: {', '.join(coverage['antibiotics'])}.
</div>
""", unsafe_allow_html=True)
