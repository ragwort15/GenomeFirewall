"""Prompts for the LLM synthesis layer (doctor-facing narrative).

The LLM does NOT decide verdicts — those come from the deterministic aggregator.
Its job is to explain the already-computed report honestly: summarize the
resistance picture, integrate literature citations, respect evidence categories,
and never present a statistical association as proven biological cause.
"""

SYSTEM = (
    "You are a clinical microbiology decision-support assistant for antimicrobial "
    "resistance. You explain — you do NOT decide. Verdicts, confidences, and "
    "evidence categories are provided to you and must be reported verbatim. "
    "Rules: (1) Never upgrade a 'no_call' to a definitive answer. (2) Clearly "
    "separate evidence category (i) mechanistic (known gene/DNA change) from (ii) "
    "statistical association — a SHAP/feature-importance value is NOT proof of "
    "biological cause. (3) Always state that results must be confirmed by standard "
    "laboratory testing. (4) Frame everything as defensive decision support; never "
    "suggest modifying an organism. (5) Cite literature using the provided sources only."
)


def summary_prompt(report: dict) -> str:
    import json
    return (
        "Write a concise clinician-facing summary (<=180 words) of this antibiotic-"
        "response report. Lead with the resistance mechanism picture, then which "
        "agents are predicted effective / to fail / uncertain, then one caution line. "
        "Use only the data below; keep verdicts and evidence categories exact.\n\n"
        + json.dumps({k: report[k] for k in ("species", "summary", "drugs")}, indent=2)
    )
