"""Per-drug performance metrics (challenge success criteria).

Reports, per antibiotic: balanced accuracy, recall for resistant and susceptible
SEPARATELY, F1, AUROC, PR-AUC. Also handles the no-call convention: metrics are
computed on the CALLED subset, and no-call rate is reported alongside.

Inputs are tidy DataFrames with columns:
    genome_id, drug, y_true (R/S), y_pred (R/S/NC), prob (P_resistant, optional)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (balanced_accuracy_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score)

R, S, NC = "R", "S", "no_call"


def _biner(y):
    return np.array([1 if v == R else 0 for v in y])


def per_drug_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """One row per drug. Classification metrics on the called subset;
    AUROC/PR-AUC use prob over all rows with a probability."""
    rows = []
    for drug, g in df.groupby("drug", sort=True):
        n = len(g)
        called = g[g["y_pred"].isin([R, S])]
        n_called = len(called)
        rec = {"drug": drug, "n": n, "n_called": n_called,
               "no_call_rate": round(1 - n_called / n, 3) if n else np.nan}
        if n_called and called["y_true"].nunique() > 1:
            yt, yp = _biner(called["y_true"]), _biner(called["y_pred"])
            rec["balanced_acc"] = round(balanced_accuracy_score(yt, yp), 3)
            rec["recall_R"] = round(recall_score(yt, yp, pos_label=1, zero_division=0), 3)
            rec["recall_S"] = round(recall_score(yt, yp, pos_label=0, zero_division=0), 3)
            rec["f1"] = round(f1_score(yt, yp, pos_label=1, zero_division=0), 3)
        else:
            rec.update({"balanced_acc": np.nan, "recall_R": np.nan,
                        "recall_S": np.nan, "f1": np.nan})
        # ranking metrics on rows that have a probability + both classes
        gp = g.dropna(subset=["prob"]) if "prob" in g else g.iloc[0:0]
        if len(gp) and gp["y_true"].nunique() > 1:
            yt = _biner(gp["y_true"]); p = gp["prob"].astype(float).values
            rec["auroc"] = round(roc_auc_score(yt, p), 3)
            rec["pr_auc"] = round(average_precision_score(yt, p), 3)
        else:
            rec["auroc"] = np.nan; rec["pr_auc"] = np.nan
        rows.append(rec)
    out = pd.DataFrame(rows)
    return out[["drug", "n", "n_called", "no_call_rate", "balanced_acc",
               "recall_R", "recall_S", "f1", "auroc", "pr_auc"]]


def macro_summary(per_drug: pd.DataFrame) -> dict:
    num = per_drug.select_dtypes("number")
    return {c: round(float(num[c].mean()), 3) for c in
            ("balanced_acc", "recall_R", "recall_S", "f1", "auroc", "pr_auc",
             "no_call_rate") if c in num}
