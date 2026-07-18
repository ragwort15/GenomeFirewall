"""Confidence-quality assessment: Brier score + reliability (calibration) plot.

Also reports how the no-call option trades coverage for accuracy. A confident-
but-wrong prediction is the dangerous failure mode, so calibration matters as
much as accuracy here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def brier(df: pd.DataFrame) -> pd.DataFrame:
    """Per-drug Brier score on rows with a probability + true label."""
    rows = []
    for drug, g in df.groupby("drug", sort=True):
        gp = g.dropna(subset=["prob"])
        if len(gp) and gp["y_true"].nunique() > 1:
            y = (gp["y_true"] == "R").astype(int).values
            rows.append({"drug": drug, "brier": round(brier_score_loss(y, gp["prob"]), 4),
                         "n": len(gp)})
    return pd.DataFrame(rows)


def reliability_plot(df: pd.DataFrame, out_png: str, n_bins=10, title="Reliability"):
    """Pool all (prob, y_true) and plot predicted vs observed resistance."""
    gp = df.dropna(subset=["prob"])
    y = (gp["y_true"] == "R").astype(int).values
    p = gp["prob"].astype(float).values
    bins = np.linspace(0, 1, n_bins + 1)
    idx = np.digitize(p, bins) - 1
    xs, ys = [], []
    for b in range(n_bins):
        m = idx == b
        if m.sum():
            xs.append(p[m].mean()); ys.append(y[m].mean())
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="perfect")
    ax.plot(xs, ys, "o-", color="#1f8a8a", label="model")
    ax.set_xlabel("Predicted P(resistant)"); ax.set_ylabel("Observed fraction resistant")
    ax.set_title(title); ax.legend(); fig.tight_layout()
    fig.savefig(out_png, dpi=130); plt.close(fig)
    return out_png


def coverage_accuracy(df: pd.DataFrame) -> dict:
    """No-call rate and accuracy on the remaining (called) predictions."""
    n = len(df)
    called = df[df["y_pred"].isin(["R", "S"])]
    acc = float((called["y_pred"] == called["y_true"]).mean()) if len(called) else float("nan")
    return {"n": n, "no_call_rate": round(1 - len(called) / n, 3) if n else None,
            "called_accuracy": round(acc, 3)}
