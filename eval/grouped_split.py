"""Genetic-relatedness (grouped) split via Mash.

The challenge's key honesty requirement: identical / near-identical genomes must
NOT appear in both train and test, or scores are inflated. We sketch all genomes
with Mash, single-linkage cluster below a distance threshold, and produce
group-aware CV folds so whole clusters stay together.

Threshold is left to the team to tune+justify (challenge). Default 0.0005 Mash
distance (~>99.95% ANI) collapses near-clonal isolates; raise it (e.g. 0.02-0.05)
to group by lineage/clonal complex for a stricter generalization test.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np


def _run(cmd, **kw):
    print("[grouped_split]", " ".join(map(str, cmd)), file=sys.stderr)
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def mash_distances(genome_dir, workdir, kmer=21, sketch=1000):
    """Sketch every *.fna/*.fasta in genome_dir; return (ids, dist_matrix)."""
    genome_dir, workdir = Path(genome_dir), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    fastas = sorted([p for p in genome_dir.iterdir()
                     if p.suffix in (".fna", ".fasta", ".fa")])
    ids = [p.stem for p in fastas]
    msh = workdir / "all.msh"
    _run(["mash", "sketch", "-k", str(kmer), "-s", str(sketch),
          "-o", str(msh.with_suffix("")), *map(str, fastas)])
    out = _run(["mash", "dist", str(msh), str(msh)]).stdout
    idx = {p.name: i for i, p in enumerate(fastas)}
    n = len(fastas)
    D = np.zeros((n, n))
    for line in out.strip().splitlines():
        a, b, d, *_ = line.split("\t")
        i, j = idx[Path(a).name], idx[Path(b).name]
        D[i, j] = float(d)
    return ids, D


def cluster(ids, D, threshold=0.0005):
    """Single-linkage: union genomes with Mash distance <= threshold."""
    n = len(ids)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if D[i, j] <= threshold:
                union(i, j)
    roots = {}
    labels = {}
    for i, gid in enumerate(ids):
        r = find(i)
        labels[gid] = roots.setdefault(r, len(roots))
    return labels  # {genome_id: cluster_id}


def grouped_folds(cluster_labels: dict, n_splits=5, seed=42):
    """GroupKFold over cluster ids -> list of (train_ids, test_ids)."""
    from sklearn.model_selection import GroupKFold
    ids = list(cluster_labels)
    groups = [cluster_labels[i] for i in ids]
    X = np.zeros((len(ids), 1))
    folds = []
    for tr, te in GroupKFold(n_splits=n_splits).split(X, groups=groups):
        folds.append(([ids[i] for i in tr], [ids[i] for i in te]))
    return folds


def build_split(genome_dir, workdir, threshold=0.0005, n_splits=5):
    ids, D = mash_distances(genome_dir, workdir)
    labels = cluster(ids, D, threshold)
    n_clusters = len(set(labels.values()))
    print(f"[grouped_split] {len(ids)} genomes -> {n_clusters} clusters "
          f"@ mash<= {threshold}", file=sys.stderr)
    return labels, grouped_folds(labels, n_splits)
