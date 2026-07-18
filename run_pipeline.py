"""Deterministic end-to-end runner: FASTA -> decision report JSON.

    conda activate genomefirewall
    python run_pipeline.py -i data/smoke/GCF_000240185.1_ASM24018v2.fna \
        --sample-id KP-HS11286 -o report.json

Runs Module 1 (annotation/features) + Module 2 (all installed models +
aggregation) + report builder. The LLM narrative + paper-qa citation layer is
added on top by agent/ (optional; needs OPENAI_API_KEY).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from genome_reader.run_amrfinder import run_amrfinder
from genome_reader import features as F
from predictor import registry, aggregate
from agent.report import build_report, save_report


def run(fasta, sample_id, species="Klebsiella pneumoniae", workdir="/tmp",
        organism="Klebsiella_pneumoniae", models=None):
    workdir = str(Path(workdir)); Path(workdir).mkdir(parents=True, exist_ok=True)

    # Module 1: annotate + features (also reused by rule adapter, but we want
    # GenomeFeatures + the target gate for the report/aggregator).
    tsv = run_amrfinder(fasta, str(Path(workdir) / (Path(fasta).stem + ".amrfinder.tsv")),
                        organism=organism)
    df = F.parse_amrfinder_tsv(tsv)
    feats = F.extract_features(df)

    # Module 2: run selected models (default all pretrained), then aggregate.
    long_df = registry.run_all_models(fasta, species=species, workdir=workdir,
                                      models=models)
    target_fn = lambda drug: F.target_present(drug, feats)
    verdicts = aggregate.aggregate(long_df, target_fn=target_fn)

    models_used = sorted(long_df["model"].unique().tolist()) if not long_df.empty else []
    report = build_report(sample_id, species, verdicts, features=feats,
                          models_used=models_used)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("--sample-id", default="sample")
    ap.add_argument("--species", default="Klebsiella pneumoniae")
    ap.add_argument("--workdir", default="/tmp/genomefirewall")
    ap.add_argument("--models", default=None,
                    help="comma-separated adapter names (default: all pretrained). "
                         "Use --list-models to see options.")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("-o", "--output", default="report.json")
    args = ap.parse_args()
    if args.list_models:
        print("available:", registry.available_models())
        print("untrained (need training):", registry.TRAINING_REQUIRED)
        return
    models = [m.strip() for m in args.models.split(",")] if args.models else None
    report = run(args.input, args.sample_id, args.species, args.workdir, models=models)
    save_report(report, args.output)
    print(json.dumps(report["summary"], indent=2))
    print(f"\nReport written to {args.output}")


if __name__ == "__main__":
    main()
