"""Load and shape antibiotic-response reports for the Streamlit UI.

Prefers real pipeline outputs (data/example/*.json) when the uploaded filename
matches a known example; falls back to the mock report otherwise.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DIR = ROOT / "data" / "example"
MOCK_PATH = ROOT / "data" / "mock_results.json"

# Map uploaded filename → (report JSON, literature JSON)
KNOWN_EXAMPLES: dict[str, tuple[Path, Path | None]] = {
    "573.12861.fna": (
        EXAMPLE_DIR / "report.json",
        EXAMPLE_DIR / "report_literature.json",
    ),
    "573.56205.fna": (
        EXAMPLE_DIR / "report_573.56205.json",
        EXAMPLE_DIR / "report_573.56205_literature.json",
    ),
    "kp_esbl_demo.fna": (
        EXAMPLE_DIR / "report_kp_esbl.json",
        None,
    ),
    "kp_carbapenem_demo.fna": (
        EXAMPLE_DIR / "report_kp_carbapenem.json",
        None,
    ),
}

VERDICT_MAP = {
    "likely_to_work": "work",
    "likely_to_fail": "fail",
    "no_call": "nocall",
    "nocall": "nocall",
}

EVIDENCE_MAP = {
    "i": "known resistance gene",
    "ii": "statistical association only",
    "iii": "no known resistance signal",
}


def _pick_example_paths(filename: str) -> tuple[Path, Path | None] | None:
    if filename in KNOWN_EXAMPLES:
        return KNOWN_EXAMPLES[filename]
    for key, paths in KNOWN_EXAMPLES.items():
        if key.split(".fna")[0] in filename:
            return paths
    default = KNOWN_EXAMPLES.get("573.12861.fna")
    return default if default and default[0].exists() else None


def _shape_drug(d: dict[str, Any]) -> dict[str, Any]:
    genes = d.get("supporting_genes") or []
    bits: list[str] = []
    if genes:
        bits.append(f"Detected: {', '.join(genes)}")
    reason = (d.get("reason") or "").strip()
    if reason:
        bits.append(reason[0].upper() + reason[1:])
    target_note = d.get("target_note")
    if target_note and not d.get("target_present", True):
        bits.append(f"Target absent — {target_note}")

    return {
        "drug": d["drug"].capitalize(),
        "verdict": VERDICT_MAP.get(d.get("verdict"), "nocall"),
        "confidence": float(d.get("confidence") or 0.5),
        "evidence": EVIDENCE_MAP.get(
            d.get("evidence_category"),
            d.get("evidence_label", "—"),
        ),
        "detail": ". ".join(bits) or "No supporting evidence recorded.",
        "supporting_genes": genes,
        "model_votes": d.get("model_votes", []),
        "literature": [],
    }


def _shape_real(report_path: Path, lit_path: Path | None) -> dict[str, Any]:
    with open(report_path, encoding="utf-8") as f:
        raw = json.load(f)
    literature = None
    if lit_path is not None and lit_path.exists():
        with open(lit_path, encoding="utf-8") as f:
            literature = json.load(f)

    return {
        "source": "backend",
        "source_label": f"Real pipeline output · {raw.get('sample_id', report_path.stem)}",
        "sample_id": raw.get("sample_id"),
        "species": raw.get("species", "Klebsiella pneumoniae"),
        "generated_utc": raw.get("generated_utc"),
        "models_used": raw.get("models_used", []),
        "genome_features": raw.get("genome_features", {}),
        "coverage": {
            "species": raw.get("species", "Klebsiella pneumoniae"),
            "antibiotics": [d["drug"] for d in raw.get("drugs", [])],
        },
        "antibiotics": [_shape_drug(d) for d in raw.get("drugs", [])],
        "literature_block": literature,
    }


def load_report(uploaded_filename: str) -> dict[str, Any]:
    """Return a UI-shaped report dict for the given uploaded filename."""
    example = _pick_example_paths(uploaded_filename)
    if example and example[0].exists():
        return _shape_real(example[0], example[1])

    with open(MOCK_PATH, encoding="utf-8") as f:
        data = json.load(f)
    data["source"] = "mock"
    data["source_label"] = "Mock dataset"
    return data
