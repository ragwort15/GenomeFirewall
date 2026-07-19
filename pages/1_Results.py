import sys
from pathlib import Path

import streamlit as st
from style import inject_global_css, render_signed_in_header, render_patient_card, VERDICT_META

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.report_loader import load_report  # noqa: E402

st.set_page_config(page_title="Genome Firewall — Results", page_icon="🧬", layout="centered")

inject_global_css()

if not st.session_state.get("authed") or not st.session_state.get("uploaded_filename"):
    st.switch_page("app.py")

filename = st.session_state.uploaded_filename
DATA = load_report(filename)

antibiotics = DATA["antibiotics"]
coverage = DATA["coverage"]

source_badge = "pill-green" if DATA.get("source") == "backend" else "pill-cyan"
source_pill = f"<span class='pill {source_badge}'>{DATA.get('source_label', '')}</span>"
status_pill = f"<span class='pill pill-green'>{filename} — Quality-checked ✓</span>"
render_signed_in_header(
    st.session_state.user,
    right_content=f"<div style='margin-top:0.5rem; display:flex; flex-direction:column; gap:0.35rem; align-items:flex-end;'>{status_pill}{source_pill}</div>",
)

back_col, _ = st.columns([1, 5])
with back_col:
    if st.button("← Back to upload"):
        st.switch_page("app.py")

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

# ---- Genome features (real reports) ----
gf = DATA.get("genome_features") or {}
if gf.get("genes") or gf.get("point_mutations"):
    genes_html = "".join(f"<span class='chip'>{g}</span>" for g in gf.get("genes", []))
    muts_html = "".join(f"<span class='chip'>{m}</span>" for m in gf.get("point_mutations", []))
    models_html = " · ".join(DATA.get("models_used", [])) or "—"
    st.markdown(f"""
    <div class="section-title">Genome features detected</div>
    <div class="section-sub">Signals extracted by the annotation stack ({models_html}).</div>
    <div class="drug-card">
      <div class="drug-meta-row"><div class="drug-meta">AMR elements: <b>{gf.get('n_amr_elements', len(gf.get('genes', [])))}</b></div></div>
      <div style="margin-top:0.4rem;">{genes_html or "<i>none</i>"}</div>
      {f"<div style='margin-top:0.5rem;'><div class='drug-meta'>Point mutations</div>{muts_html}</div>" if muts_html else ""}
    </div>
    """, unsafe_allow_html=True)

# ---- Literature narrative (real reports) ----
lit_block = DATA.get("literature_block")
if lit_block:
    st.markdown(f"""
    <div class="section-title">Literature evidence</div>
    <div class="section-sub">paper-qa synthesis for <b>{lit_block.get('query', '')}</b> · {lit_block.get('n_pdfs', 0)} sources.</div>
    """, unsafe_allow_html=True)
    with st.expander("View synthesized answer & citations", expanded=False):
        st.markdown(
            "<div class='lit-note'><b>Question:</b> " + lit_block.get("question", "") + "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='drug-detail' style='margin:0.75rem 0 1rem 0;'>"
            + lit_block.get("answer", "").replace("\n", "<br/>")
            + "</div>",
            unsafe_allow_html=True,
        )
        for c in lit_block.get("citations", []):
            doi_url = f"https://doi.org/{c.get('doi')}" if c.get("doi") else "#"
            st.markdown(f"""
            <div class="lit-ref">
              <div class="lit-ref-title">{c.get('title', '')}<span class="lit-tag">score {c.get('score', '—')}</span></div>
              <div class="lit-meta">{c.get('citation', '')}</div>
              <div class="lit-quote">&ldquo;{c.get('excerpt', '')}&rdquo;</div>
              <a class="lit-link" href="{doi_url}" target="_blank" rel="noopener">View source ↗</a>
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
