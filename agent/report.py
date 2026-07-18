"""Build the structured decision report (JSON) from aggregated verdicts.

The report is the single artifact consumed by the Streamlit demo and (optionally)
enriched with LLM narrative + paper-qa citations. It always carries the mandatory
lab-confirmation disclaimer and an explicit coverage statement.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

DISCLAIMER = ("Research prototype — every result must be confirmed by standard "
              "laboratory testing. Decision support only; not a medical device. "
              "Predicts and explains existing resistance only.")

EVIDENCE_LABEL = {
    "i": "known resistance gene / DNA change detected",
    "ii": "statistical association only (not proof of biological cause)",
    "iii": "no known resistance signal found",
}
VERDICT_LABEL = {
    "likely_to_fail": "Likely to FAIL (resistant)",
    "likely_to_work": "Likely to WORK (susceptible)",
    "no_call": "NO-CALL (uncertain)",
}


def build_report(sample_id, species, verdicts_df, features=None,
                 models_used=None, literature=None, clinical_context=None,
                 timestamp=None):
    """verdicts_df: output of aggregate.aggregate(). Returns a JSON-able dict."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    drugs = []
    for _, r in verdicts_df.iterrows():
        drug = r["drug"]
        drugs.append({
            "drug": drug,
            "verdict": r["verdict"],
            "verdict_label": VERDICT_LABEL.get(r["verdict"], r["verdict"]),
            "evidence_category": r["evidence_category"],
            "evidence_label": EVIDENCE_LABEL.get(r["evidence_category"], ""),
            "confidence": r["confidence"],
            "supporting_genes": r["genes"],
            "target_present": r["target_present"],
            "target_note": r["target_note"],
            "reason": r["reason"],
            "model_votes": r["votes"],
            "literature": (literature or {}).get(drug, []),
        })
    counts = verdicts_df["verdict"].value_counts().to_dict()
    return {
        "sample_id": sample_id,
        "species": species,
        "generated_utc": ts,
        "disclaimer": DISCLAIMER,
        "summary": {
            "n_drugs": len(drugs),
            "n_likely_to_fail": counts.get("likely_to_fail", 0),
            "n_likely_to_work": counts.get("likely_to_work", 0),
            "n_no_call": counts.get("no_call", 0),
        },
        "models_used": models_used or [],
        "genome_features": (features.as_dict() if features is not None else {}),
        "clinical_context": clinical_context or {},
        "coverage": {
            "species_covered": [species],
            "not_covered": ["other species", "antibiotics outside the panel",
                            "sample→genome steps", "polymicrobial samples"],
        },
        "drugs": drugs,
    }


def save_report(report: dict, path: str):
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    return path
