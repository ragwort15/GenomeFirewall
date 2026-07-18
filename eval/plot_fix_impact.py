"""Render the fusion-fix impact table as a grouped bar chart.

Four systems x three headline metrics (Balanced acc, Recall S, AUROC) on the
shared 20-genome LLM subset. The two systems the fix changed (Combined, LLM) get
a translucent "before-fix" ghost bar + an improvement arrow, so the story — naive
union collapsed the ensemble; the curated tiebreak recovered it — is visible.

  python -m eval.plot_fix_impact --workdir $SCRATCH/genomefirewall/pilot
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]

SYSTEMS = ["AMRFinderPlus", "Kleborate", "Combined (aggregate)", "LLM+Literature"]
METRICS = [("balanced_acc", "Balanced acc"), ("recall_S", "Recall S\n(catch susceptible)"),
           ("auroc", "AUROC")]
COLORS = {"AMRFinderPlus": "#8c8c8c", "Kleborate": "#c0a35e",
          "Combined (aggregate)": "#3b7dd8", "LLM+Literature": "#1f8a8a"}
# values BEFORE the fusion fix (from the pre-fix run), for the changed systems
BEFORE = {"Combined (aggregate)": {"balanced_acc": 0.50, "recall_S": 0.00, "auroc": 0.50},
          "LLM+Literature": {"balanced_acc": 0.577, "recall_S": 0.154, "auroc": 0.885}}


def main():
    ap = argparse.ArgumentParser()
    default_wd = Path(os.environ.get("SCRATCH", "/tmp")) / "genomefirewall" / "pilot"
    ap.add_argument("--workdir", default=str(default_wd))
    ap.add_argument("--json", default=str(REPO / "Result" / "benchmark_kp_pilot"
                                          / "model_comparison_common.json"))
    ap.add_argument("--out", default=str(REPO / "Result" / "benchmark_kp_pilot"
                                         / "fix_impact.png"))
    args = ap.parse_args()

    cur = json.load(open(args.json))
    x = np.arange(len(METRICS))
    w = 0.8 / len(SYSTEMS)
    fig, ax = plt.subplots(figsize=(11, 6))

    for i, sysname in enumerate(SYSTEMS):
        off = i * w - 0.4 + w / 2
        for j, (key, _) in enumerate(METRICS):
            v = cur[sysname].get(key)
            v = np.nan if v is None else float(v)
            xpos = x[j] + off
            # before-fix ghost bar + arrow for changed systems
            b = BEFORE.get(sysname, {}).get(key)
            if b is not None and not (v != v):
                ax.bar(xpos, b, w, color=COLORS[sysname], alpha=0.28,
                       hatch="////", edgecolor="white", zorder=1)
                if v - b > 0.02:
                    ax.annotate("", xy=(xpos, v), xytext=(xpos, b),
                                arrowprops=dict(arrowstyle="->", color="#127a2e", lw=1.6),
                                zorder=4)
                    # delta beside the arrow (mid-height), value goes above the bar
                    ax.text(xpos + w * 0.62, (b + v) / 2, f"+{v-b:.2f}",
                            ha="left", va="center", fontsize=7,
                            color="#127a2e", fontweight="bold")
            if v != v:                                   # NaN -> n/a
                ax.text(xpos, 0.02, "n/a", ha="center", va="bottom",
                        fontsize=7, color="gray", rotation=90)
                continue
            ax.bar(xpos, v, w, color=COLORS[sysname], edgecolor="white",
                   linewidth=0.5, zorder=3,
                   label=sysname if j == 0 else None)
            ax.text(xpos, v + 0.015, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5)

    ax.axhline(0.5, ls="--", lw=0.8, color="gray")
    ax.text(len(METRICS) - 0.5, 0.51, "0.5 = no skill", fontsize=7, color="gray")
    ax.set_xticks(x); ax.set_xticklabels([lbl for _, lbl in METRICS], fontsize=10)
    ax.set_ylim(0, 1.1); ax.set_ylabel("score (macro-averaged over drugs)")
    ax.set_title("Fusion fix impact — per-model on the shared LLM subset (20 genomes)\n"
                 "hatched = before fix · arrow = improvement", fontsize=11)
    ax.legend(ncol=4, fontsize=8.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.07), frameon=False)
    fig.tight_layout()
    fig.savefig(args.out, dpi=140, bbox_inches="tight"); plt.close(fig)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
