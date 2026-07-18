"""Assemble the benchmark pilot: select genomes, download FASTAs, build a
genetic-relatedness (Mash) grouped split.

Pipeline
  1. Stratified-select ~N genomes from data/bvbrc_kp/labels.tsv so every scored
     drug keeps both R and S present (rare drugs seeded first). Piperacillin/
     tazobactam is excluded (~4 labels — too few to score).
  2. Download each genome's assembled FASTA from BV-BRC (reuses
     data/download_bvbrc.download_fastas).
  3. Mash-sketch + single-linkage cluster the *downloaded* genomes into groups so
     near-clonal isolates never straddle train/test (reuses eval.grouped_split).

Outputs (under --workdir, default $SCRATCH/genomefirewall/pilot):
  genomes/<genome_id>.fna     assembled genomes (big — on $SCRATCH)
  pilot_labels.tsv            labels.tsv rows for downloaded genomes only
  clusters.tsv                genome_id  cluster_id   (the grouped split)
  folds.json                  GroupKFold test assignments (for a trained baseline)
  manifest.tsv                genome_id  fna  n_bytes  downloaded

Run it on a compute node (download + mash are not login-node work):
  sbatch setup/build_dataset.sbatch          # or:  python -m eval.build_dataset ...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval import grouped_split                 # noqa: E402

# BV-BRC assembled contigs come from the data API (the ftp.bvbrc.org host that
# download_bvbrc.py targets is firewalled from Sherlock; the API works over HTTPS).
SEQ_API = "https://www.bv-brc.org/api/genome_sequence/"

LABELS = REPO / "data" / "bvbrc_kp" / "labels.tsv"
# Piperacillin/tazobactam has ~4 labels in this dump — cannot be scored.
EXCLUDE_DRUGS = {"piperacillin/tazobactam"}


def load_labels(path=LABELS) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", dtype={"genome_id": str})
    df = df[~df["antibiotic"].isin(EXCLUDE_DRUGS)].copy()
    return df


def select_genomes(df: pd.DataFrame, n=200, seed=42, min_per_class=8) -> list[str]:
    """Pick ~n genome_ids that keep both R and S present for every scored drug.

    Rare drugs are seeded first (guarantee >= min_per_class R and S where the data
    allows), then we fill up to n with a random draw over the remaining genomes.
    Deterministic given `seed`.
    """
    rng = np.random.default_rng(seed)
    pheno = {(g, d): p for g, d, p in
             df[["genome_id", "antibiotic", "phenotype"]].itertuples(index=False)}
    drugs = list(df["antibiotic"].unique())
    # pool of genomes for each (drug, phenotype)
    pool = defaultdict(list)
    for (g, d), p in pheno.items():
        pool[(d, p)].append(g)

    selected: set[str] = set()

    def have(drug, phen):
        return sum(1 for g in selected if pheno.get((g, drug)) == phen)

    # rarest drug first so scarce classes get first pick of shared genomes
    rarity = df["antibiotic"].value_counts().index[::-1]
    for drug in rarity:
        for phen in ("R", "S"):
            cand = [g for g in pool[(drug, phen)] if g not in selected]
            rng.shuffle(cand)
            need = min_per_class - have(drug, phen)
            selected.update(cand[:max(0, need)])

    # fill to n with a random draw over all genomes
    allg = df["genome_id"].unique().tolist()
    rng.shuffle(allg)
    for g in allg:
        if len(selected) >= n:
            break
        selected.add(g)
    return sorted(selected)


def report_coverage(df: pd.DataFrame, genomes: list[str]) -> pd.DataFrame:
    sub = df[df["genome_id"].isin(set(genomes))]
    cov = (sub.groupby(["antibiotic", "phenotype"]).size()
           .unstack(fill_value=0).reindex(columns=["R", "S"], fill_value=0))
    cov["total"] = cov.sum(axis=1)
    return cov.sort_values("total")


def _uniquify_headers(fasta: str, genome_id: str) -> str:
    """BV-BRC's dna+fasta gives every contig the same '>accn|undefined' header;
    makeblastdb (inside AMRFinderPlus) rejects duplicate IDs. Renumber them."""
    out, n = [], 0
    for line in fasta.splitlines():
        if line.startswith(">"):
            n += 1
            out.append(f">{genome_id}_contig{n}")
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def _fetch_fasta(genome_id: str, dest: Path, retries=3, min_bytes=1000) -> bool:
    """Download one genome's assembled contigs as FASTA from the BV-BRC data API."""
    rql = (f"eq(genome_id,{genome_id})&select(genome_id,sequence)"
           f"&limit(25000)&http_accept=application/dna+fasta")
    url = SEQ_API + "?" + urllib.parse.quote(rql, safe="=&(),+.*")
    req = urllib.request.Request(url, headers={"Accept": "application/dna+fasta"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) >= min_bytes and data.lstrip()[:1] == b">":
                dest.write_text(_uniquify_headers(data.decode("utf-8", "replace"),
                                                  genome_id))
                return True
            raise ValueError(f"short/empty response ({len(data)} bytes)")
        except Exception as e:
            if attempt == retries - 1:
                print(f"[build_dataset] FASTA {genome_id} failed: {e}", file=sys.stderr)
            time.sleep(1.0 + attempt)
    return False


def download(genomes: list[str], workdir: Path) -> pd.DataFrame:
    gdir = workdir / "genomes"
    gdir.mkdir(parents=True, exist_ok=True)
    man = []
    for i, g in enumerate(genomes):
        fna = gdir / f"{g}.fna"
        if not (fna.exists() and fna.stat().st_size > 1000):
            _fetch_fasta(g, fna)
            time.sleep(0.25)                 # be polite to the API
        ok = fna.exists() and fna.stat().st_size > 1000
        man.append({"genome_id": g, "fna": str(fna),
                    "n_bytes": fna.stat().st_size if fna.exists() else 0,
                    "downloaded": ok})
        if (i + 1) % 25 == 0:
            print(f"[build_dataset] downloaded {i+1}/{len(genomes)}")
    return pd.DataFrame(man)


def main():
    ap = argparse.ArgumentParser()
    default_wd = Path(os.environ.get("SCRATCH", "/tmp")) / "genomefirewall" / "pilot"
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-per-class", type=int, default=8)
    ap.add_argument("--workdir", default=str(default_wd))
    ap.add_argument("--mash-threshold", type=float, default=0.0005,
                    help="Mash distance to collapse near-clonal genomes (~99.95%% ANI)")
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--skip-download", action="store_true",
                    help="reuse genomes already in <workdir>/genomes")
    args = ap.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    df = load_labels()

    genomes = select_genomes(df, args.n, args.seed, args.min_per_class)
    print(f"[build_dataset] selected {len(genomes)} genomes (target {args.n})")
    print(report_coverage(df, genomes).to_string())

    if args.skip_download:
        gdir = workdir / "genomes"
        man = pd.DataFrame([{"genome_id": g, "fna": str(gdir / f"{g}.fna"),
                             "n_bytes": (gdir / f"{g}.fna").stat().st_size
                             if (gdir / f"{g}.fna").exists() else 0,
                             "downloaded": (gdir / f"{g}.fna").exists()}
                            for g in genomes])
    else:
        man = download(genomes, workdir)
    man.to_csv(workdir / "manifest.tsv", sep="\t", index=False)
    ok = man[man["downloaded"]]["genome_id"].tolist()
    print(f"[build_dataset] {len(ok)}/{len(genomes)} FASTAs available")

    # labels restricted to genomes we actually have
    df[df["genome_id"].isin(set(ok))].to_csv(
        workdir / "pilot_labels.tsv", sep="\t", index=False)

    # Mash grouped split over the downloaded genomes
    labels, folds = grouped_split.build_split(
        str(workdir / "genomes"), str(workdir / "mash"),
        threshold=args.mash_threshold, n_splits=args.n_splits)
    clusters = pd.DataFrame(sorted(labels.items()),
                            columns=["genome_id", "cluster_id"])
    clusters.to_csv(workdir / "clusters.tsv", sep="\t", index=False)
    sizes = Counter(labels.values())
    with open(workdir / "folds.json", "w") as f:
        json.dump([{"fold": i, "test": te} for i, (_, te) in enumerate(folds)], f)

    n_clusters = len(sizes)
    biggest = sizes.most_common(1)[0][1] if sizes else 0
    print(f"[build_dataset] {len(ok)} genomes -> {n_clusters} clusters "
          f"@ mash<= {args.mash_threshold}; largest cluster = {biggest} genomes; "
          f"singletons = {sum(1 for s in sizes.values() if s == 1)}")
    print(f"[build_dataset] wrote workdir: {workdir}")


if __name__ == "__main__":
    main()
