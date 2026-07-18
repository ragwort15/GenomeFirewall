"""Genome Firewall — Streamlit decision-report demo (Module 3).

    conda activate genomefirewall
    streamlit run app/streamlit_app.py

Upload a K. pneumoniae assembly FASTA (or load a precomputed report JSON) and
view the per-antibiotic decision report: verdict, calibrated confidence,
evidence category, supporting genes, per-model ensemble votes, literature, and
the mandatory "confirm with standard lab testing" banner.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

st.set_page_config(page_title="Genome Firewall", page_icon="🧬", layout="wide")

VC = {"likely_to_fail": "#c0392b", "likely_to_work": "#1e7e46", "no_call": "#8a6d00"}
VBG = {"likely_to_fail": "#fdecea", "likely_to_work": "#e9f7ef", "no_call": "#fbf4dd"}
CALL_TXT = {"R": "Resistant", "S": "Susceptible", "U": "Uncertain"}


def banner():
    st.markdown(
        "<div style='background:#fff3cd;border-left:6px solid #e0a800;padding:12px 16px;"
        "border-radius:8px;color:#5c4700'>⚠️ <b>Research prototype — every result must be "
        "confirmed by standard laboratory testing.</b> Decision support only; it does not "
        "replace culture-based susceptibility testing and must be reviewed by a clinician. "
        "Predicts and explains <i>existing</i> resistance only.</div>",
        unsafe_allow_html=True)


def render_report(report: dict):
    s = report["summary"]
    st.subheader(f"Sample {report['sample_id']} · *{report['species']}*")
    c = st.columns(4)
    c[0].metric("Antibiotics", s["n_drugs"])
    c[1].metric("Likely to FAIL", s["n_likely_to_fail"])
    c[2].metric("Likely to WORK", s["n_likely_to_work"])
    c[3].metric("NO-CALL", s["n_no_call"])
    st.caption("Models used: " + ", ".join(report.get("models_used", [])) +
               " · " + f"{report['genome_features'].get('n_amr_elements', 0)} AMR elements detected")

    # clinician summary pills
    buckets = {"likely_to_work": [], "no_call": [], "likely_to_fail": []}
    for d in report["drugs"]:
        buckets[d["verdict"]].append(d["drug"])
    st.markdown("#### Clinician summary")
    for v, label in [("likely_to_work", "Predicted effective"),
                     ("no_call", "Uncertain — no call"),
                     ("likely_to_fail", "Predicted to fail")]:
        if buckets[v]:
            pills = " ".join(
                f"<span style='background:{VBG[v]};color:{VC[v]};border:1px solid {VC[v]}44;"
                f"padding:3px 10px;border-radius:16px;font-size:13px;margin:2px;display:inline-block'>{d}</span>"
                for d in buckets[v])
            st.markdown(f"<b style='color:#6b7c8a'>{label}:</b> {pills}", unsafe_allow_html=True)

    st.markdown("#### Per-antibiotic prediction & evidence")
    for d in report["drugs"]:
        conf = f"{int(round(d['confidence']*100))}% confidence" if d["confidence"] is not None else "insufficient / conflicting"
        title = (f"{d['drug']}  —  {d['verdict_label']}  ·  {conf}  ·  evidence ({d['evidence_category']})")
        with st.expander(title):
            st.markdown(f"🎯 **Target gate:** {d['target_note']}")
            st.markdown(f"**Reason:** {d['reason']}  \n"
                        f"**Evidence category ({d['evidence_category']}):** {d['evidence_label']}")
            if d["supporting_genes"]:
                st.markdown("**Supporting determinants:** " +
                            ", ".join(f"`{g}`" for g in d["supporting_genes"]))
            votes = d["model_votes"]
            if votes:
                import pandas as pd
                vdf = pd.DataFrame(votes)
                vdf["call"] = vdf["call"].map(lambda x: CALL_TXT.get(x, x))
                vdf = vdf.rename(columns={"model": "Model", "call": "Call",
                                          "prob": "P(resistant)", "evidence_type": "Type"})
                st.dataframe(vdf, hide_index=True, use_container_width=True)
            if d.get("literature"):
                st.markdown("**Literature:**")
                for ref in d["literature"]:
                    st.markdown(f"- {ref.get('title','')} — {ref.get('citation','')} "
                                f"({ref.get('doi','')})")

    with st.expander("Coverage & limitations / honest-explanation note"):
        cov = report["coverage"]
        st.markdown("**✔ Covered:** " + ", ".join(cov["species_covered"]) +
                    " · panel of " + str(s["n_drugs"]) + " antibiotics")
        st.markdown("**✘ Not covered:** " + ", ".join(cov["not_covered"]))
        st.caption("Evidence (i) = mechanistic (known gene/DNA change). (ii) = statistical "
                   "association only — a SHAP/importance value does not prove biological cause. "
                   "(iii) = no known resistance signal (gated on target presence).")
    st.caption(report["disclaimer"])


# ---------------- UI ----------------
st.markdown("## 🧬🛡️ Genome Firewall")
st.markdown("Genome-to-antibiotic-response decision support · *Klebsiella pneumoniae*")
banner()

tab_run, tab_load = st.tabs(["Analyze a FASTA", "Load a report JSON"])

with tab_run:
    from predictor import registry
    up = st.file_uploader("Quality-checked assembly FASTA", type=["fasta", "fa", "fna"])
    sid = st.text_input("Sample / isolate ID", "sample")
    avail = registry.available_models()
    chosen = st.multiselect("Models to run (pretrained)", avail, default=avail)
    if registry.TRAINING_REQUIRED:
        st.caption("Not available (need training on BV-BRC): "
                   + ", ".join(registry.TRAINING_REQUIRED))
    if st.button("Run analysis ▸", disabled=(up is None or not chosen)):
        with st.spinner("Annotating (AMRFinderPlus) and running selected models…"):
            from run_pipeline import run
            tmp = Path(tempfile.mkdtemp())
            fpath = tmp / up.name
            fpath.write_bytes(up.getbuffer())
            report = run(str(fpath), sid, workdir=str(tmp), models=chosen)
        st.success("Done.")
        render_report(report)

with tab_load:
    rj = st.file_uploader("report.json", type=["json"], key="rj")
    if rj is not None:
        render_report(json.load(rj))
