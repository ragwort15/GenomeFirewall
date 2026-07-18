"""Model registry: choose which adapters to run, run them, return a long frame.

Adapters are keyed by name so the orchestrator / CLI can select a subset
(e.g. only pretrained models). Training-required models (PhenotypeSeeker, Kover,
AMR-GNN) can be registered later; until their trained artifacts exist their
is_installed() is False and they are skipped automatically.

    available_models()                    -> ["AMRFinderPlus","Kleborate","WGS_to_AMR", ...]
    run_all_models(fasta, models=[...])   -> long DataFrame
"""
from __future__ import annotations

import pandas as pd

from .adapters.amrfinder_rules import AMRFinderRules
from .adapters.wgs_to_amr import WGSToAMR

# name -> adapter class. Pretrained models only for now (predict directly from
# FASTA). Add Kleborate here once its adapter is wired; add the training-required
# ones (PhenotypeSeeker/Kover/AMR-GNN) after they are trained on BV-BRC.
ADAPTER_CLASSES = {
    "AMRFinderPlus": AMRFinderRules,
    "WGS_to_AMR": WGSToAMR,
}

# advertised but not yet runnable (need training); listed so the UI can show them
TRAINING_REQUIRED = ["PhenotypeSeeker", "Kover", "AMR-GNN"]

try:  # optional: Kleborate rule adapter (pretrained, Klebsiella-specific)
    from .adapters.kleborate_rules import KleborateRules
    ADAPTER_CLASSES["Kleborate"] = KleborateRules
except Exception:  # pragma: no cover
    pass


def available_models(include_untrained=False):
    names = list(ADAPTER_CLASSES.keys())
    return names + TRAINING_REQUIRED if include_untrained else names


def build_adapters(species="Klebsiella pneumoniae", workdir="/tmp", models=None,
                   extra=None):
    """models: optional list of adapter names to include (default = all registered)."""
    selected = models if models is not None else list(ADAPTER_CLASSES.keys())
    adapters = []
    for name in selected:
        cls = ADAPTER_CLASSES.get(name)
        if cls is None:
            print(f"[registry] unknown/untrained model '{name}' — skipping")
            continue
        try:
            a = cls(workdir=workdir)
        except Exception as e:
            print(f"[registry] skip {name}: {e}")
            continue
        if a.supports(species):
            adapters.append(a)
    for cls in (extra or []):
        adapters.append(cls(workdir=workdir))
    return adapters


def run_all_models(fasta_path, species="Klebsiella pneumoniae", workdir="/tmp",
                   models=None, extra=None, require_installed=True) -> pd.DataFrame:
    frames = []
    for a in build_adapters(species, workdir, models, extra):
        if require_installed and not a.is_installed():
            print(f"[registry] {a.name} not installed/trained — skipping")
            continue
        try:
            frames.append(a.predict(fasta_path))
            print(f"[registry] {a.name} OK")
        except Exception as e:
            print(f"[registry] {a.name} failed: {str(e)[:300]}")
    if not frames:
        return pd.DataFrame(
            columns=["model", "drug", "call", "prob", "evidence_type", "genes", "note"])
    return pd.concat(frames, ignore_index=True)
