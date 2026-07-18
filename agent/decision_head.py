"""LLM decision head — a SCORABLE call that fuses all evidence.

The production LLM layer (agent/orchestrator.py) is explanation-only: it never
changes the deterministic verdict. This module is the opposite by design — an
experimental head that *decides* from the raw evidence bundle (per-model votes,
detected determinants, target gate, and literature) so we can benchmark whether
LLM + literature fusion beats the deterministic aggregator on the same metrics.

It deliberately does NOT see the aggregator's verdict/confidence (no anchoring).
One LLM call per genome returns a decision for every drug at once (bounded cost).

    from agent.decision_head import decide
    decisions = decide(report, literature=lit, handler=handler)
    # decisions[drug] = {call: R/S/no_call, prob: P_resistant, evidence_category, rationale}

Safety: no_call is a first-class option; category (i) mechanistic evidence is kept
separate from (ii) statistical association; a target-absent gate forces no_call.
If no API key / handler is available, decide() returns None and the caller skips
the LLM arm of the benchmark.
"""
from __future__ import annotations

import json
import re

CALLS = {"R", "S", "no_call"}
CATS = {"i", "ii", "iii"}

SYSTEM = (
    "You are an antimicrobial-resistance decision engine. Given raw genomic evidence "
    "for ONE bacterial genome, decide for EACH antibiotic whether it is likely to "
    "FAIL (organism resistant, call 'R'), likely to WORK (susceptible, call 'S'), or "
    "'no_call' when evidence is weak, conflicting, or unlike known data. Rules: "
    "(1) A known resistance determinant (a real gene/DNA change on the drug's class) "
    "is strong evidence for R — evidence category 'i'. "
    "(2) A model probability without a known determinant is only a statistical "
    "association — category 'ii'; never treat it as mechanistic proof. "
    "(3) Absence of any resistance signal with the target present supports S — "
    "category 'iii'. (4) If the drug's molecular target is absent, return no_call. "
    "(5) Prefer no_call over a confident guess when models disagree or evidence is thin. "
    "(6) Weight callers by SPECIFICITY. Kleborate is a curated Klebsiella-specific "
    "caller that distinguishes a true carbapenemase from a mere ESBL; AMRFinderPlus "
    "is a broad screen that maps ANY beta-lactamase to every beta-lactam and so "
    "over-calls carbapenems. Do NOT call a carbapenem (imipenem/meropenem) resistant "
    "just because a beta-lactamase/ESBL is present — require a carbapenemase. When the "
    "curated caller says susceptible but the broad screen says resistant, favour the "
    "curated susceptible call. "
    "Output STRICT JSON only: an object mapping each drug name to "
    "{\"call\":\"R|S|no_call\",\"prob\":<P(resistant) 0..1>,"
    "\"evidence_category\":\"i|ii|iii\",\"rationale\":\"<=25 words\"}. "
    "prob must be a calibrated probability of resistance (high for R, low for S, "
    "~0.5 for no_call). No prose outside the JSON."
)


def build_evidence(report: dict, literature: dict | None = None) -> dict:
    """Compact per-drug evidence bundle from a decision report (verdict/confidence
    intentionally omitted so the LLM decides from evidence, not the aggregator)."""
    literature = literature or {}
    bundle = {}
    for d in report.get("drugs", []):
        drug = d["drug"]
        votes = [{"model": v.get("model"), "call": v.get("call"),
                  "prob": v.get("prob"), "type": v.get("evidence_type")}
                 for v in d.get("model_votes", [])]
        lits = [c.get("title") or c.get("citation", "")[:120]
                for c in literature.get(drug, [])][:3]
        bundle[drug] = {
            "model_votes": votes,
            "resistance_determinants": d.get("supporting_genes", []),
            "target_present": d.get("target_present", True),
            "target_note": d.get("target_note", ""),
            "literature": lits,
        }
    return bundle


def _extract_json(text: str) -> dict:
    """Best-effort JSON object parse from an LLM completion."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)     # first {...} block
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}
    return {}


def _clean(dec: dict) -> dict | None:
    """Validate/coerce one drug decision; drop if unusable."""
    if not isinstance(dec, dict):
        return None
    call = str(dec.get("call", "")).strip()
    if call not in CALLS:
        return None
    cat = str(dec.get("evidence_category", "")).strip()
    try:
        prob = float(dec.get("prob"))
        prob = min(1.0, max(0.0, prob))
    except (TypeError, ValueError):
        prob = None
    return {"call": call, "prob": prob,
            "evidence_category": cat if cat in CATS else "ii",
            "rationale": str(dec.get("rationale", ""))[:200]}


def decide(report: dict, literature: dict | None = None, handler=None,
           model: str = "gpt-4o", provider: str = "openai") -> dict | None:
    """One call per genome -> {drug: cleaned decision}. None if no LLM available."""
    if handler is None:
        import os
        if not os.environ.get("OPENAI_API_KEY"):
            return None
        from agent.api.interface import get_handler
        handler = get_handler(provider, model=model)

    bundle = build_evidence(report, literature)
    prompt = ("Decide every antibiotic for this genome. Evidence bundle "
              "(JSON, one entry per drug):\n" + json.dumps(bundle, indent=1) +
              "\n\nReturn the STRICT JSON object described in the system message, "
              "with one key per drug above.")
    raw = handler.get_completion(SYSTEM, prompt)
    parsed = _extract_json(raw)
    out = {}
    for drug in bundle:
        cleaned = _clean(parsed.get(drug, {}))
        if cleaned is not None:
            out[drug] = cleaned
    return out
