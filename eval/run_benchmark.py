"""Score the pilot and emit the benchmark report (challenge success criteria).

Joins per-genome predictions (<workdir>/reports/*.json) to the ground-truth
labels, then scores TWO systems on identical rows:
  * deterministic  — the aggregator verdict + reconstructed P(resistant)
  * llm            — the decision head that fuses all evidence (optional; --llm)

For each system it reports the brief's metrics via eval.metrics / eval.calibration:
balanced accuracy, recall_R, recall_S, F1, AUROC, PR-AUC, no-call rate, Brier +
reliability plot. Generalization is reported two ways: POOLED (every genome) and
CLUSTER-DEDUP (one genome per Mash cluster) — the latter removes clonal
over-representation and is the honest generalization number.

  conda activate genomefirewall
  python -m eval.run_benchmark --workdir $SCRATCH/genomefirewall/pilot --llm
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval import metrics as M                    # noqa: E402
from eval import calibration as C                # noqa: E402


def load_env(path=REPO / ".env"):
    """Minimal .env loader (python-dotenv isn't in the env). Sets any KEY=VALUE
    line into os.environ without overriding values already present."""
    if not Path(path).exists():
        return
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and not os.environ.get(k):
            os.environ[k] = v

VERDICT2CALL = {"likely_to_fail": "R", "likely_to_work": "S", "no_call": "no_call"}


# ---------- prediction extraction ----------

def reconstruct_prob(d: dict):
    """Continuous P(resistant): prefer mean ML vote prob; else derive from the
    verdict + confidence; None when nothing is available (rule-only, no conf)."""
    ml = [v["prob"] for v in d.get("model_votes", []) if v.get("prob") is not None]
    if ml:
        return float(np.mean(ml))
    c = d.get("confidence")
    if c is None:
        return None
    if d["verdict"] == "likely_to_fail":
        return float(c)
    if d["verdict"] == "likely_to_work":
        return float(1.0 - c)
    return None


def det_rows(report: dict) -> list[dict]:
    gid = report["sample_id"]
    out = []
    for d in report.get("drugs", []):
        out.append({"genome_id": gid, "drug": d["drug"],
                    "y_pred": VERDICT2CALL.get(d["verdict"], "no_call"),
                    "prob": reconstruct_prob(d)})
    return out


def reaggregate_rows(report: dict) -> list[dict]:
    """Re-run the CURRENT aggregate.py fusion over the report's stored model votes,
    so the deterministic arm reflects the latest reconciliation policy without
    re-running AMRFinderPlus. (Model calls are already saved in model_votes.)"""
    from predictor import aggregate as AGG
    gid = report["sample_id"]
    tp, recs = {}, []
    for d in report.get("drugs", []):
        tp[d["drug"]] = d.get("target_present", True)
        genes = d.get("supporting_genes", [])
        for i, v in enumerate(d.get("model_votes", [])):
            recs.append({"model": v["model"], "drug": d["drug"], "call": v["call"],
                         "prob": v.get("prob"), "evidence_type": v.get("evidence_type"),
                         "genes": genes if i == 0 else []})
    if not recs:
        return []
    verdicts = AGG.aggregate(pd.DataFrame(recs),
                             target_fn=lambda drug: (tp.get(drug, True), ""))
    out = []
    for _, r in verdicts.iterrows():
        vd = {"verdict": r["verdict"], "confidence": r["confidence"],
              "model_votes": r["votes"]}
        out.append({"genome_id": gid, "drug": r["drug"],
                    "y_pred": VERDICT2CALL.get(r["verdict"], "no_call"),
                    "prob": reconstruct_prob(vd)})
    return out


def llm_rows(gid: str, decisions: dict) -> list[dict]:
    return [{"genome_id": gid, "drug": drug, "y_pred": dec["call"], "prob": dec["prob"]}
            for drug, dec in decisions.items()]


# ---------- assembly ----------

def load_reports(workdir: Path) -> list[dict]:
    reps = []
    for p in sorted((workdir / "reports").glob("*.json")):
        try:
            reps.append(json.load(open(p)))
        except Exception as e:
            print(f"[run_benchmark] bad report {p.name}: {e}")
    return reps


def truth(workdir: Path) -> pd.DataFrame:
    df = pd.read_csv(workdir / "pilot_labels.tsv", sep="\t", dtype={"genome_id": str})
    return (df[["genome_id", "antibiotic", "phenotype"]]
            .rename(columns={"antibiotic": "drug", "phenotype": "y_true"}))


def build_tidy(pred_rows: list[dict], y: pd.DataFrame) -> pd.DataFrame:
    pred = pd.DataFrame(pred_rows)
    tidy = pred.merge(y, on=["genome_id", "drug"], how="inner")
    return tidy[["genome_id", "drug", "y_true", "y_pred", "prob"]]


def llm_decisions(reports, workdir: Path, use_literature: bool, max_llm: int | None):
    """Run (and cache) the decision head per genome. Returns {gid: {drug: dec}}."""
    from agent.decision_head import decide
    from agent.api.interface import get_handler
    if not os.environ.get("OPENAI_API_KEY"):
        print("[run_benchmark] OPENAI_API_KEY unset — skipping LLM arm")
        return {}
    handler = get_handler("openai", model="gpt-4o")
    cache = workdir / "llm_decisions"
    cache.mkdir(exist_ok=True)
    lit_fn = None
    if use_literature:
        from agent.tools.literature_tool import literature_for_report

    out = {}
    reps = reports if max_llm is None else reports[:max_llm]
    for i, rep in enumerate(reps):
        gid = rep["sample_id"]
        cp = cache / f"{gid}.json"
        if cp.exists():
            out[gid] = json.load(open(cp))
            continue
        lit = None
        if use_literature:
            vdf = pd.DataFrame([{"drug": d["drug"],
                                 "evidence_category": d["evidence_category"],
                                 "genes": d["supporting_genes"]}
                                for d in rep["drugs"]])
            try:
                lit = literature_for_report(vdf)
            except Exception as e:
                print(f"[run_benchmark] literature failed for {gid}: {e}")
        dec = decide(rep, literature=lit, handler=handler)
        if dec:
            json.dump(dec, open(cp, "w"))
            out[gid] = dec
        print(f"[run_benchmark] LLM {i+1}/{len(reps)} {gid}: "
              f"{len(dec) if dec else 0} drugs decided")
    return out


# ---------- scoring ----------

def score_system(tidy: pd.DataFrame, clusters: dict, name: str, outdir: Path) -> dict:
    per_drug = M.per_drug_metrics(tidy)
    per_drug.to_csv(outdir / f"per_drug_metrics__{name}.csv", index=False)
    macro = M.macro_summary(per_drug)
    cov = C.coverage_accuracy(tidy)
    brier = C.brier(tidy)
    brier.to_csv(outdir / f"brier__{name}.csv", index=False)
    if tidy.dropna(subset=["prob"]).shape[0]:
        C.reliability_plot(tidy, str(outdir / f"reliability__{name}.png"),
                           title=f"Reliability — {name}")

    # cluster-dedup: keep one (deterministic) genome per Mash cluster
    if clusters:
        by_cluster = {}
        for gid in tidy["genome_id"].unique():
            by_cluster.setdefault(clusters.get(gid, gid), []).append(gid)
        keep = {sorted(v)[0] for v in by_cluster.values()}
        dedup = tidy[tidy["genome_id"].isin(keep)]
        macro_dedup = M.macro_summary(M.per_drug_metrics(dedup))
        n_clusters = len(by_cluster)
    else:
        macro_dedup, n_clusters = {}, None

    return {"system": name,
            "n_labels": int(len(tidy)),
            "n_genomes": int(tidy["genome_id"].nunique()),
            "n_clusters": n_clusters,
            "coverage": cov,
            "macro_pooled": macro,
            "macro_cluster_dedup": macro_dedup,
            "brier_macro": round(float(brier["brier"].mean()), 4) if len(brier) else None}


def group_breakdown(tidy: pd.DataFrame, clusters: dict) -> pd.DataFrame:
    rows = []
    for cid, genomes in _invert(clusters).items():
        g = tidy[tidy["genome_id"].isin(genomes)]
        if not len(g):
            continue
        called = g[g["y_pred"].isin(["R", "S"])]
        acc = float((called["y_pred"] == called["y_true"]).mean()) if len(called) else np.nan
        rows.append({"cluster_id": cid, "n_genomes": len(set(genomes) & set(g["genome_id"])),
                     "n_labels": len(g), "n_R": int((g["y_true"] == "R").sum()),
                     "n_S": int((g["y_true"] == "S").sum()),
                     "called_accuracy": round(acc, 3) if acc == acc else np.nan})
    return pd.DataFrame(rows).sort_values("n_genomes", ascending=False)


def _invert(clusters: dict) -> dict:
    out = {}
    for gid, cid in clusters.items():
        out.setdefault(cid, []).append(gid)
    return out


def write_markdown(summaries, per_drug_paths, group_df, args, outdir):
    lines = ["# Genome Firewall — Benchmark (K. pneumoniae pilot)\n",
             f"- Workdir: `{args.workdir}`",
             f"- Genomes scored: {summaries[0]['n_genomes']} "
             f"({summaries[0]['n_clusters']} Mash clusters @ dist<= {args.mash_threshold})",
             f"- Labels scored: {summaries[0]['n_labels']}\n",
             "## System comparison (macro-averaged over drugs)\n",
             "| system | scope | balanced_acc | recall_R | recall_S | f1 | auroc | pr_auc | no_call | brier |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        for scope, key in (("pooled", "macro_pooled"), ("cluster-dedup", "macro_cluster_dedup")):
            m = s.get(key, {}) or {}
            lines.append(
                f"| {s['system']} | {scope} | {m.get('balanced_acc','-')} | "
                f"{m.get('recall_R','-')} | {m.get('recall_S','-')} | {m.get('f1','-')} | "
                f"{m.get('auroc','-')} | {m.get('pr_auc','-')} | {m.get('no_call_rate','-')} | "
                f"{s['brier_macro'] if scope=='pooled' else '-'} |")
    lines += [
        "\n## Per-drug tables", "",
        *[f"- `{Path(p).name}`" for p in per_drug_paths],
        "\n## Generalization by genetic group",
        f"- Per-cluster breakdown: `by_group.csv` "
        f"({len(group_df)} clusters; largest = {int(group_df['n_genomes'].max())} genomes)",
        "- POOLED counts every genome (clonal lineages over-represented); "
        "CLUSTER-DEDUP keeps one genome per Mash cluster — the honest generalization number.",
        "\n## Caveats (read before trusting numbers)",
        "- **Pretrained-model leakage:** any ML adapter (e.g. WGS_to_AMR) was trained on "
        "BV-BRC K. pneumoniae, so pilot genomes may be in its training set — this inflates "
        "ML/aggregator scores. The Mash split fixes *own-model* leakage, not pretrained leakage.",
        "- **Probability coverage:** AUROC / PR-AUC / Brier need a P(resistant); rule-only "
        "predictions have none, so those columns are NaN unless an ML adapter contributes.",
        "- Every result must be confirmed by standard laboratory testing (research prototype).",
        ""]
    (outdir / "BENCHMARK.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    default_wd = Path(os.environ.get("SCRATCH", "/tmp")) / "genomefirewall" / "pilot"
    ap.add_argument("--workdir", default=str(default_wd))
    ap.add_argument("--out", default=str(REPO / "Result" / "benchmark_kp_pilot"))
    ap.add_argument("--mash-threshold", type=float, default=0.0005)
    ap.add_argument("--llm", action="store_true", help="also score the LLM decision head")
    ap.add_argument("--literature", action="store_true", help="fetch paper-qa literature for the LLM head")
    ap.add_argument("--max-llm", type=int, default=None, help="cap genomes sent to the LLM (cost)")
    args = ap.parse_args()
    load_env()                                    # pick up OPENAI_API_KEY from .env

    workdir = Path(args.workdir)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    reports = load_reports(workdir)
    if not reports:
        sys.exit(f"[run_benchmark] no reports in {workdir/'reports'} — run predict_batch first")
    y = truth(workdir)
    clusters = {}
    cf = workdir / "clusters.tsv"
    if cf.exists():
        cl = pd.read_csv(cf, sep="\t", dtype={"genome_id": str})
        clusters = dict(zip(cl["genome_id"], cl["cluster_id"]))

    # deterministic system (re-aggregated with the current fusion policy)
    det_tidy = build_tidy([r for rep in reports for r in reaggregate_rows(rep)], y)
    det_tidy.to_csv(outdir / "tidy__deterministic.csv", index=False)
    summaries = [score_system(det_tidy, clusters, "deterministic", outdir)]
    per_drug_paths = [outdir / "per_drug_metrics__deterministic.csv"]

    # LLM system (optional)
    if args.llm:
        decs = llm_decisions(reports, workdir, args.literature, args.max_llm)
        if decs:
            llm_tidy = build_tidy([r for gid, d in decs.items() for r in llm_rows(gid, d)], y)
            llm_tidy.to_csv(outdir / "tidy__llm.csv", index=False)
            summaries.append(score_system(llm_tidy, clusters, "llm", outdir))
            per_drug_paths.append(outdir / "per_drug_metrics__llm.csv")

    group_df = group_breakdown(det_tidy, clusters) if clusters else pd.DataFrame()
    group_df.to_csv(outdir / "by_group.csv", index=False)
    json.dump(summaries, open(outdir / "macro_summary.json", "w"), indent=2)
    write_markdown(summaries, per_drug_paths, group_df, args, outdir)

    print(f"\n[run_benchmark] wrote {outdir}")
    for s in summaries:
        print(f"  {s['system']:14s} pooled={s['macro_pooled']}  "
              f"dedup={s['macro_cluster_dedup']}")


if __name__ == "__main__":
    main()
