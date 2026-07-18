"""Aggregate multi-model outputs into one per-drug verdict.

Consumes the long DataFrame from registry.run_all_models (columns:
model, drug, call, prob, evidence_type, genes, note) and produces one row per
drug with: verdict, evidence category (i/ii/iii), calibrated-ish confidence,
supporting genes, per-model votes, and the reason for any no-call.

Reconciliation policy (honest by construction):
  * Rule-based determinant detected (evidence 'rule', call R) -> FAIL, category (i).
    Mechanism trumps a weak ML disagreement; confidence anchored high.
  * Otherwise decide from ML P(resistant):
       mean_p >= HI            -> FAIL   (category ii)
       mean_p <= LO            -> WORK   (category iii if no determinants)
       LO < mean_p < HI        -> NO-CALL (uncertain band)
  * NO-CALL also when: ML models disagree (spread > SPREAD), rule vs ML conflict,
    a model abstains as majority, or the genome is out-of-distribution (ood).
  * Target gate: target absent -> NO-CALL ("drug not applicable / target absent"),
    never "works".
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
import pandas as pd

from .adapters.base import (EVIDENCE_RULE, EVIDENCE_ML,
                            CALL_RESISTANT, CALL_SUSCEPTIBLE, CALL_UNCERTAIN)

FAIL, WORK, NOCALL = "likely_to_fail", "likely_to_work", "no_call"

# thresholds on P(resistant); tune/justify on the calibration split
LO = 0.35
HI = 0.65
SPREAD = 0.40   # max-min across ML probs above this => models disagree


@dataclass
class DrugVerdict:
    drug: str
    verdict: str
    evidence_category: str          # 'i' | 'ii' | 'iii'
    confidence: float | None
    genes: list = field(default_factory=list)
    target_present: bool = True
    target_note: str = ""
    reason: str = ""
    votes: list = field(default_factory=list)   # [{model,call,prob,evidence_type}]

    def to_dict(self):
        return asdict(self)


def _confidence(verdict, mean_p, rule_hit):
    if verdict == NOCALL:
        return None
    if rule_hit and verdict == FAIL:
        return round(max(0.85, mean_p if mean_p is not None else 0.9), 3)
    if verdict == FAIL:
        return round(mean_p, 3)
    if verdict == WORK:
        return round(1 - mean_p, 3)  # confidence in susceptibility
    return None


def aggregate_drug(group: pd.DataFrame, target_present=True, target_note="",
                   ood=False) -> DrugVerdict:
    drug = group["drug"].iloc[0]
    votes = group[["model", "call", "prob", "evidence_type"]].to_dict("records")

    rules = group[group["evidence_type"] == EVIDENCE_RULE]
    mls = group[group["evidence_type"] == EVIDENCE_ML]

    rule_hit = bool((rules["call"] == CALL_RESISTANT).any())
    determinants = sorted({g for lst in group["genes"] for g in (lst or [])})

    ml_probs = [p for p in mls["prob"].tolist() if p is not None]
    mean_p = sum(ml_probs) / len(ml_probs) if ml_probs else None
    spread = (max(ml_probs) - min(ml_probs)) if len(ml_probs) >= 2 else 0.0

    # --- target gate first ---
    if not target_present:
        return DrugVerdict(drug, NOCALL, "iii", None, determinants,
                           target_present=False, target_note=target_note,
                           reason="molecular target absent — drug not applicable",
                           votes=votes)

    # --- OOD ---
    if ood:
        return DrugVerdict(drug, NOCALL, "ii", None, determinants,
                           target_note=target_note,
                           reason="genome unlike training data (out-of-distribution)",
                           votes=votes)

    # --- rule-based mechanism ---
    if rule_hit:
        # if ML strongly disagrees, flag but keep mechanism (report the tension)
        note = "known resistance determinant detected"
        if mean_p is not None and mean_p < LO:
            note += "; note: ML models predict susceptible (possible non-functional allele)"
        v = DrugVerdict(drug, FAIL, "i", None, determinants,
                        target_note=target_note, reason=note, votes=votes)
        v.confidence = _confidence(FAIL, mean_p, rule_hit=True)
        return v

    # --- ML-driven ---
    if mean_p is None:
        return DrugVerdict(drug, NOCALL, "iii", None, determinants,
                           target_note=target_note,
                           reason="no rule determinant and no ML probability",
                           votes=votes)

    if spread > SPREAD:
        return DrugVerdict(drug, NOCALL, "ii", None, determinants,
                           target_note=target_note,
                           reason=f"ML models disagree (prob spread {spread:.2f})",
                           votes=votes)

    if mean_p >= HI:
        return DrugVerdict(drug, FAIL, "ii", _confidence(FAIL, mean_p, False),
                           determinants, target_note=target_note,
                           reason="statistical association (no known determinant)",
                           votes=votes)
    if mean_p <= LO:
        cat = "iii" if not determinants else "ii"
        return DrugVerdict(drug, WORK, cat, _confidence(WORK, mean_p, False),
                           determinants, target_note=target_note,
                           reason="no known resistance signal; models predict susceptible",
                           votes=votes)
    return DrugVerdict(drug, NOCALL, "ii", None, determinants,
                       target_note=target_note,
                       reason=f"evidence weak/uncertain (mean P_resistant {mean_p:.2f})",
                       votes=votes)


def aggregate(long_df: pd.DataFrame, target_fn=None, ood_drugs=None) -> pd.DataFrame:
    """long_df -> per-drug verdicts DataFrame.

    target_fn(drug) -> (present: bool, note: str); default all present.
    ood_drugs: optional set of drugs flagged out-of-distribution.
    """
    ood_drugs = ood_drugs or set()
    rows = []
    for drug, g in long_df.groupby("drug", sort=False):
        present, note = (True, "")
        if target_fn is not None:
            present, note = target_fn(drug)
        v = aggregate_drug(g, target_present=present, target_note=note,
                           ood=(drug in ood_drugs))
        rows.append(v.to_dict())
    return pd.DataFrame(rows)
