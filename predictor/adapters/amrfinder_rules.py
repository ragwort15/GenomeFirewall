"""Rule-based adapter: AMRFinderPlus determinants -> per-drug R/S call.

Evidence category (i): a known resistance gene / DNA change was detected.
No probability (rule-based); call is R if any determinant maps to the drug,
else S. This is the mechanistic backbone the ML models are reconciled against.
"""
from __future__ import annotations

import pandas as pd

from .base import (ModelAdapter, Prediction, EVIDENCE_RULE,
                   CALL_RESISTANT, CALL_SUSCEPTIBLE)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from genome_reader.run_amrfinder import run_amrfinder
from genome_reader import features as F


class AMRFinderRules(ModelAdapter):
    name = "AMRFinderPlus"
    evidence_type = EVIDENCE_RULE
    drugs = tuple(F.DRUG_CLASS_TOKENS.keys())

    def __init__(self, organism="Klebsiella_pneumoniae", threads=4, workdir="/tmp"):
        self.organism = organism
        self.threads = threads
        self.workdir = workdir

    def is_installed(self) -> bool:
        import shutil
        return shutil.which("amrfinder") is not None

    def predict(self, fasta_path: str) -> pd.DataFrame:
        out_tsv = str(Path(self.workdir) / (Path(fasta_path).stem + ".amrfinder.tsv"))
        run_amrfinder(fasta_path, out_tsv, self.organism, self.threads)
        df = F.parse_amrfinder_tsv(out_tsv)
        evidence = F.get_gene_drug_evidence(df)
        preds = []
        for drug in self.drugs:
            determinants = evidence.get(drug, [])
            call = CALL_RESISTANT if determinants else CALL_SUSCEPTIBLE
            preds.append(Prediction(
                drug=drug, call=call, prob=None,
                evidence_type=EVIDENCE_RULE, genes=determinants,
                note=("known determinant(s): " + ", ".join(determinants))
                if determinants else "no known determinant detected",
            ))
        return self._frame(preds)
