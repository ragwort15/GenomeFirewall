"""LLM synthesis layer on top of the deterministic report.

Adds (optionally): a paper-qa literature block per mechanistic drug, a parsed
clinical-context block, and an LLM-written clinician summary. All optional and
best-effort — if OPENAI_API_KEY / paper-qa are absent, the deterministic report
is returned unchanged. The LLM never changes verdicts/confidences.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.report import build_report
from agent import prompts
from agent.tools.literature_tool import literature_for_report
from agent.tools.clinical_tool import parse_clinical_note


def enrich_report(sample_id, species, verdicts_df, features=None, models_used=None,
                  clinical_note=None, do_literature=True, do_summary=True,
                  provider="openai", model="gpt-4o"):
    handler = None
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from agent.api.interface import get_handler
            handler = get_handler(provider, model=model)
        except Exception as e:
            print(f"[orchestrator] LLM handler unavailable: {e}")

    literature = literature_for_report(verdicts_df) if do_literature else None
    clinical = parse_clinical_note(clinical_note, handler) if clinical_note else None

    report = build_report(sample_id, species, verdicts_df, features=features,
                          models_used=models_used, literature=literature,
                          clinical_context=clinical)

    if do_summary and handler is not None:
        summary = handler.get_completion(prompts.SYSTEM, prompts.summary_prompt(report))
        if summary:
            report["clinician_summary"] = summary
    return report
