"""Run the Genome Firewall pipeline over the pilot genomes (batch / SLURM array).

For each downloaded genome, run Module 1 + 2 (annotation + all installed models +
aggregation) and save the FULL decision report to <workdir>/reports/<id>.json.
That report already carries everything downstream scoring needs:
  * the deterministic per-drug verdict + confidence            (aggregate.py)
  * per-drug model_votes (incl. ML P_resistant) + genes        (evidence bundle
    for both the reconstructed prob and the LLM decision head)

Sharding: an array of M tasks; task S processes genomes whose index % M == S.
Idempotent — a genome whose report already exists is skipped, so failed shards
can be re-run.

  python -m eval.predict_batch --workdir $SCRATCH/genomefirewall/pilot \
      --shard $SLURM_ARRAY_TASK_ID --nshards 20
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import run_pipeline                              # noqa: E402
from agent.report import save_report            # noqa: E402


def genomes_for_shard(workdir: Path, shard: int, nshards: int) -> list[str]:
    man = pd.read_csv(workdir / "manifest.tsv", sep="\t", dtype={"genome_id": str})
    ok = man[man["downloaded"]].sort_values("genome_id")["genome_id"].tolist()
    return [g for i, g in enumerate(ok) if i % nshards == shard]


def predict_one(genome_id: str, workdir: Path, species: str) -> dict:
    fasta = workdir / "genomes" / f"{genome_id}.fna"
    # per-genome scratch so concurrent array tasks never collide on intermediates
    base = Path(os.environ.get("L_SCRATCH", str(workdir / "_tmp")))
    tmp = base / "gf_predict" / genome_id
    tmp.mkdir(parents=True, exist_ok=True)
    return run_pipeline.run(str(fasta), sample_id=genome_id, species=species,
                            workdir=str(tmp))


def main():
    ap = argparse.ArgumentParser()
    default_wd = Path(os.environ.get("SCRATCH", "/tmp")) / "genomefirewall" / "pilot"
    ap.add_argument("--workdir", default=str(default_wd))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--species", default="Klebsiella pneumoniae")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    workdir = Path(args.workdir)
    reports = workdir / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    todo = genomes_for_shard(workdir, args.shard, args.nshards)
    print(f"[predict_batch] shard {args.shard}/{args.nshards}: {len(todo)} genomes")
    done = failed = 0
    for gid in todo:
        out = reports / f"{gid}.json"
        if out.exists() and not args.overwrite:
            done += 1
            continue
        try:
            report = predict_one(gid, workdir, args.species)
            save_report(report, str(out))
            done += 1
            print(f"[predict_batch] {gid} OK ({report['summary']})")
        except Exception as e:
            failed += 1
            print(f"[predict_batch] {gid} FAILED: {e}")
            traceback.print_exc()
    print(f"[predict_batch] shard {args.shard} done: {done} ok, {failed} failed")


if __name__ == "__main__":
    main()
