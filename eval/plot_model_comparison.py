"""Compare each model independently vs the combined aggregate vs LLM+literature.

The benchmark scores the *combined* systems; this breaks the ensemble open and
scores every constituent on identical rows:
    AMRFinderPlus (rule) | Kleborate (rule) | Combined (aggregate) | LLM+Literature
so you can see what each contributes. Rule models emit a call but no probability,
so ranking/calibration (AUROC/Brier) only exist for the LLM arm.

Two figures written to <out>:
  model_comparison_common.png   all 4 systems on the shared LLM subset (fair)
  model_comparison_full.png     the 3 non-LLM systems on all genomes

  conda activate genomefirewall
  python -m eval.plot_model_comparison --workdir $SCRATCH/genomefirewall/pilot
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval import metrics as M                                  # noqa: E402
from eval.run_benchmark import (load_reports, truth, build_tidy,  # noqa: E402
                                reaggregate_rows, llm_rows)

METRICS = [("balanced_acc", "Balanced acc"), ("recall_R", "Recall R (catch resistant)"),
           ("recall_S", "Recall S (catch susceptible)"), ("f1", "F1"),
           ("auroc", "AUROC")]
COLORS = {"AMRFinderPlus": "#8c8c8c", "Kleborate": "#c0a35e",
          "Combined (aggregate)": "#3b7dd8", "LLM+Literature": "#1f8a8a"}


def model_rows(reports, model_name):
    rows = []
    for r in reports:
        gid = r["sample_id"]
        for d in r["drugs"]:
            for v in d.get("model_votes", []):
                if v["model"] == model_name:
                    call = v["call"] if v["call"] in ("R", "S") else "no_call"
                    rows.append({"genome_id": gid, "drug": d["drug"],
                                 "y_pred": call, "prob": v.get("prob")})
    return rows


def macro(tidy):
    pd_ = M.per_drug_metrics(tidy)
    num = pd_.select_dtypes("number")
    return {k: (round(float(num[k].mean()), 3) if k in num and num[k].notna().any()
                else np.nan) for k, _ in METRICS}


def grouped_bar(systems: dict, title: str, out_png: str):
    """systems: {name: macro_dict}. Grouped bars: x=metric, hue=system."""
    names = list(systems)
    x = np.arange(len(METRICS))
    w = 0.8 / len(names)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for i, name in enumerate(names):
        vals = [systems[name].get(k, np.nan) for k, _ in METRICS]
        bars = ax.bar(x + i * w - 0.4 + w / 2, [0 if v != v else v for v in vals],
                      w, label=name, color=COLORS.get(name, None),
                      edgecolor="white", linewidth=0.5)
        for b, v in zip(bars, vals):
            txt = "n/a" if v != v else f"{v:.2f}"
            ax.text(b.get_x() + b.get_width() / 2, (0 if v != v else v) + 0.01,
                    txt, ha="center", va="bottom", fontsize=7, rotation=0)
    ax.axhline(0.5, ls="--", lw=0.8, color="gray")
    ax.text(len(METRICS) - 0.55, 0.51, "0.5 = no skill", fontsize=7, color="gray")
    ax.set_xticks(x); ax.set_xticklabels([lbl for _, lbl in METRICS], fontsize=9)
    ax.set_ylim(0, 1.08); ax.set_ylabel("score (macro-averaged over drugs)")
    ax.set_title(title, fontsize=11)
    ax.legend(ncol=len(names), fontsize=8, loc="upper center",
              bbox_to_anchor=(0.5, -0.08), frameon=False)
    fig.tight_layout()
    fig.savefig(out_png, dpi=140, bbox_inches="tight"); plt.close(fig)
    return out_png


def main():
    ap = argparse.ArgumentParser()
    default_wd = Path(os.environ.get("SCRATCH", "/tmp")) / "genomefirewall" / "pilot"
    ap.add_argument("--workdir", default=str(default_wd))
    ap.add_argument("--out", default=str(REPO / "Result" / "benchmark_kp_pilot"))
    args = ap.parse_args()

    workdir = Path(args.workdir)
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    reports = load_reports(workdir)
    y = truth(workdir)

    # per-model + combined tidy frames (all genomes)
    tidies = {
        "AMRFinderPlus": build_tidy(model_rows(reports, "AMRFinderPlus"), y),
        "Kleborate": build_tidy(model_rows(reports, "Kleborate"), y),
        "Combined (aggregate)": build_tidy([r for rep in reports for r in reaggregate_rows(rep)], y),
    }
    # LLM+literature (only genomes with a cached decision)
    llm_cache = workdir / "llm_decisions"
    llm_decs = {p.stem: json.load(open(p)) for p in llm_cache.glob("*.json")} \
        if llm_cache.exists() else {}
    llm_tidy = build_tidy([r for gid, d in llm_decs.items() for r in llm_rows(gid, d)], y) \
        if llm_decs else pd.DataFrame(columns=["genome_id", "drug", "y_true", "y_pred", "prob"])

    # ---- figure 1: fair comparison on the shared LLM subset ----
    common = set(llm_tidy["genome_id"].unique())
    if common:
        sub = {n: t[t["genome_id"].isin(common)] for n, t in tidies.items()}
        sub["LLM+Literature"] = llm_tidy
        systems = {n: macro(t) for n, t in sub.items()}
        json.dump(systems, open(outdir / "model_comparison_common.json", "w"), indent=2)
        p1 = grouped_bar(systems,
                         f"Per-model performance on the shared LLM subset "
                         f"({len(common)} genomes)",
                         str(outdir / "model_comparison_common.png"))
        print("wrote", p1)
        for n, m in systems.items():
            print(f"  {n:22s} {m}")

    # ---- figure 2: the 3 non-LLM systems on all genomes ----
    systems_full = {n: macro(t) for n, t in tidies.items()}
    p2 = grouped_bar(systems_full,
                     f"Per-model performance on all genomes ({y['genome_id'].nunique()} labeled)",
                     str(outdir / "model_comparison_full.png"))
    print("wrote", p2)


if __name__ == "__main__":
    main()
