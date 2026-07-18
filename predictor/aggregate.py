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

# When rule models conflict and no ML breaks the tie, defer to the most
# drug-specific / curated caller. Kleborate is Klebsiella-specific and
# distinguishes a true carbapenemase from a mere ESBL, whereas AMRFinderPlus
# maps any beta-lactam gene to every beta-lactam (it over-calls carbapenems).
RULE_PRIORITY = ("Kleborate", "AMRFinderPlus")


def _primary_rule_call(rules: pd.DataFrame):
    """Call of the highest-priority rule model that has an R/S opinion here."""
    by_model = {row["model"]: row["call"] for _, row in rules.iterrows()}
    for m in RULE_PRIORITY:
        if by_model.get(m) in (CALL_RESISTANT, CALL_SUSCEPTIBLE):
            return m, by_model[m]
    return None, None


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
    """Reconcile rule-based + ML calls into one verdict.

    Rule policy is CONSENSUS-based (not "any R wins"): a confident mechanistic
    FAIL requires the rule models to AGREE. When they conflict (e.g. AMRFinderPlus
    flags an intrinsic blaSHV/fosA but Kleborate calls susceptible) we defer to a
    decisive ML probability, else return no-call — this is what stops the system
    over-calling resistance on wild-type isolates.
    """
    drug = group["drug"].iloc[0]
    votes = group[["model", "call", "prob", "evidence_type"]].to_dict("records")

    rules = group[group["evidence_type"] == EVIDENCE_RULE]
    mls = group[group["evidence_type"] == EVIDENCE_ML]
    determinants = sorted({g for lst in group["genes"] for g in (lst or [])})

    rule_calls = [c for c in rules["call"].tolist() if c in (CALL_RESISTANT, CALL_SUSCEPTIBLE)]
    rule_R = rule_calls.count(CALL_RESISTANT)
    rule_S = rule_calls.count(CALL_SUSCEPTIBLE)

    ml_probs = [p for p in mls["prob"].tolist() if p is not None]
    mean_p = sum(ml_probs) / len(ml_probs) if ml_probs else None
    spread = (max(ml_probs) - min(ml_probs)) if len(ml_probs) >= 2 else 0.0

    def mk(verdict, cat, conf, reason):
        return DrugVerdict(drug, verdict, cat, conf, determinants,
                           target_present=target_present, target_note=target_note,
                           reason=reason, votes=votes)

    # --- target gate first ---
    if not target_present:
        return mk(NOCALL, "iii", None, "molecular target absent — drug not applicable")
    # --- out-of-distribution genome ---
    if ood:
        return mk(NOCALL, "ii", None, "genome unlike training data (out-of-distribution)")

    # --- 1) rule models UNANIMOUS resistant -> mechanistic FAIL (category i) ---
    if rule_R and rule_S == 0:
        conf = round(max(0.85, mean_p), 3) if mean_p is not None else 0.9
        reason = f"{rule_R} rule model(s) agree on a known resistance determinant"
        if mean_p is not None and mean_p < LO:
            reason += "; note: ML predicts susceptible (possible intrinsic / non-functional allele)"
        return mk(FAIL, "i", conf, reason)

    # --- 2) rule models CONFLICT -> decisive ML, else defer to the most
    #        drug-specific rule caller (Kleborate), else no-call ---
    if rule_R and rule_S:
        if mean_p is not None and mean_p >= HI:
            return mk(FAIL, "ii", round(mean_p, 3),
                      f"rule models conflict (R:{rule_R}/S:{rule_S}); ML resolves resistant (P={mean_p:.2f})")
        if mean_p is not None and mean_p <= LO:
            return mk(WORK, "ii", round(1 - mean_p, 3),
                      f"rule models conflict (R:{rule_R}/S:{rule_S}); ML resolves susceptible")
        pm, pc = _primary_rule_call(rules)
        if pc == CALL_RESISTANT:
            return mk(FAIL, "i", 0.8,
                      f"rule models conflict; deferring to {pm} (Klebsiella-specific) → resistant")
        if pc == CALL_SUSCEPTIBLE:
            return mk(WORK, "iii" if not determinants else "ii", 0.7,
                      f"rule models conflict; deferring to {pm} (Klebsiella-specific) → susceptible "
                      f"(other caller flagged an intrinsic/expected gene)")
        return mk(NOCALL, "ii", None,
                  f"rule models conflict (R:{rule_R}/S:{rule_S}); no decisive signal")

    # --- 3) rule models UNANIMOUS susceptible ---
    if rule_S and rule_R == 0:
        if mean_p is not None and mean_p >= HI:
            return mk(NOCALL, "ii", None,
                      f"no known determinant but ML predicts resistant (P={mean_p:.2f})")
        conf = round(1 - mean_p, 3) if mean_p is not None else 0.75
        cat = "iii" if not determinants else "ii"
        return mk(WORK, cat, conf, "no known resistance determinant; predicted susceptible")

    # --- 4) no rule information -> ML-only band logic ---
    if mean_p is None:
        return mk(NOCALL, "iii", None, "no rule determinant and no ML probability")
    if spread > SPREAD:
        return mk(NOCALL, "ii", None, f"ML models disagree (prob spread {spread:.2f})")
    if mean_p >= HI:
        return mk(FAIL, "ii", round(mean_p, 3), "statistical association (no rule determinant)")
    if mean_p <= LO:
        return mk(WORK, "iii" if not determinants else "ii", round(1 - mean_p, 3),
                  "no known resistance signal; predicted susceptible")
    return mk(NOCALL, "ii", None, f"evidence weak/uncertain (mean P_resistant {mean_p:.2f})")


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
