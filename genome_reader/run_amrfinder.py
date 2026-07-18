"""Module 1 step: run AMRFinderPlus on an assembly FASTA -> TSV.

Gold-standard annotation of AMR genes + point mutations (NCBI, public-domain).
Requires the `genomefirewall` conda env (ships ncbi-amrfinderplus) and a
downloaded DB (`amrfinder -u`).

Usage:
    python run_amrfinder.py -i genome.fasta -o out.tsv \
        [--organism Klebsiella_pneumoniae] [--threads 4]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_ORGANISM = "Klebsiella_pneumoniae"


def run_amrfinder(fasta: str, out_tsv: str, organism: str = DEFAULT_ORGANISM,
                  threads: int = 4, nucleotide: bool = True,
                  skip_existing: bool = True) -> str:
    """Run amrfinder and return the output TSV path. Raises on failure.

    If skip_existing and out_tsv already exists non-empty, reuse it (Module 1 and
    the rule adapter share the same output path -> avoids a redundant ~2 min run).
    """
    if skip_existing and Path(out_tsv).exists() and Path(out_tsv).stat().st_size > 0:
        print(f"[run_amrfinder] reusing existing {out_tsv}", file=sys.stderr)
        return out_tsv
    if shutil.which("amrfinder") is None:
        raise RuntimeError(
            "amrfinder not on PATH. Activate the `genomefirewall` env "
            "(conda activate genomefirewall) and run `amrfinder -u` once."
        )
    Path(out_tsv).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "amrfinder",
        "--nucleotide" if nucleotide else "--protein", fasta,
        "--organism", organism,
        "--plus",
        "--threads", str(threads),
        "-o", out_tsv,
    ]
    print("[run_amrfinder]", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, check=True)
    return out_tsv


def main():
    ap = argparse.ArgumentParser(description="Run AMRFinderPlus on an assembly FASTA")
    ap.add_argument("-i", "--input", required=True, help="assembly FASTA (nucleotide)")
    ap.add_argument("-o", "--output", required=True, help="output TSV path")
    ap.add_argument("--organism", default=DEFAULT_ORGANISM)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--protein", action="store_true", help="input is a proteome")
    args = ap.parse_args()
    path = run_amrfinder(args.input, args.output, args.organism, args.threads,
                         nucleotide=not args.protein)
    print(path)


if __name__ == "__main__":
    main()
