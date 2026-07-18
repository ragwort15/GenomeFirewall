"""Clinical-context tool (optional).

Parses a free-text clinical note into structured context (site, prior
antibiotics, allergies, renal function) used ONLY for report narrative and
prioritization — never to compute the genomic probabilities. This separation is
deliberate: it keeps the genomic prediction honest and avoids overclaiming.
"""
from __future__ import annotations

import json

SYSTEM = ("You are a clinical microbiology assistant. Extract structured fields "
          "from a free-text clinical note. Return ONLY JSON with keys: "
          "age, sex, setting, suspected_source, prior_antibiotics (list), "
          "allergies (list), renal_function, other. Use null/empty when unknown.")


def parse_clinical_note(note: str, handler=None) -> dict:
    """If an LLM handler is given, use it; otherwise return the raw note."""
    if not note or not note.strip():
        return {}
    if handler is None:
        return {"free_text": note.strip()}
    try:
        out = handler.get_completion(SYSTEM, note)
        out = out.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(out)
    except Exception:
        return {"free_text": note.strip()}
