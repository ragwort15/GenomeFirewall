"""ModelAdapter abstraction for Module 2 (Predictor).

Every published AMR model — rule-based (AMRFinderPlus, Kleborate) or ML
(WGS_to_AMR, PhenotypeSeeker, Kover, AMR-GNN) — is wrapped in one adapter so the
registry can run them uniformly and the aggregator can reconcile their outputs.

Design mirrors DeepRare's tool pattern: adapters are plain Python objects invoked
by control flow (not LLM function-calling). Adapters that live in their own conda
env shell out via subprocess; this base class does not import any model deps.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

# Call codes used everywhere downstream.
CALL_RESISTANT = "R"      # likely to fail
CALL_SUSCEPTIBLE = "S"    # likely to work
CALL_UNCERTAIN = "U"      # model itself abstains (feeds no-call logic)

EVIDENCE_RULE = "rule"    # known resistance gene/mutation  -> report category (i)
EVIDENCE_ML = "ml"        # statistical association          -> report category (ii)


@dataclass
class Prediction:
    """One (drug, model) result. prob is P(resistant) in [0,1] when available."""
    drug: str
    call: str                      # R / S / U
    prob: Optional[float] = None   # P(resistant); None for pure rule-based
    evidence_type: str = EVIDENCE_ML
    genes: list = field(default_factory=list)  # supporting determinants (rule-based)
    note: str = ""


class ModelAdapter(ABC):
    """Base class for a wrapped AMR predictor."""

    name: str = "base"
    #: model class for reporting; 'rule' or 'ml'
    evidence_type: str = EVIDENCE_ML
    #: species this adapter is valid for (lowercase binomial)
    species_supported: tuple = ("klebsiella pneumoniae",)
    #: drugs this adapter can score (standardized lowercase names)
    drugs: tuple = ()

    def supports(self, species: str) -> bool:
        return species.strip().lower() in self.species_supported

    @abstractmethod
    def is_installed(self) -> bool:
        """True if the tool/env/weights are present and runnable."""

    def setup(self) -> None:
        """Optional: install tool / create env / download weights. May raise."""
        raise NotImplementedError(f"{self.name}: setup() not implemented")

    def train(self, dataset_dir: str) -> None:
        """Optional: for models shipping training code only (PhenotypeSeeker,
        Kover, AMR-GNN). Trains per-antibiotic on the organizer dataset."""
        raise NotImplementedError(f"{self.name}: train() not implemented")

    @abstractmethod
    def predict(self, fasta_path: str) -> pd.DataFrame:
        """Run the model on one assembly FASTA.

        Returns a long DataFrame with columns:
            model, drug, call, prob, evidence_type, genes, note
        One row per drug this adapter scores.
        """

    # -- helper so subclasses build the standard frame consistently --
    def _frame(self, preds: list[Prediction]) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "model": self.name,
                    "drug": p.drug,
                    "call": p.call,
                    "prob": p.prob,
                    "evidence_type": p.evidence_type or self.evidence_type,
                    "genes": p.genes,
                    "note": p.note,
                }
                for p in preds
            ],
            columns=["model", "drug", "call", "prob", "evidence_type", "genes", "note"],
        )
