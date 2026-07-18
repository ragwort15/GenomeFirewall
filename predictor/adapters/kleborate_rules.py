"""Rule-based adapter: Kleborate (Klebsiella-specific, pretrained curated DB).

Kleborate reports acquired resistance genes grouped by drug class plus a built-in
ciprofloxacin prediction. We map its per-class columns to per-drug R/S calls
(evidence category (i): known determinant detected). Runs in `genomefirewall`.

    kleborate -a genome.fasta -o outdir -p kpsc
    -> outdir/klebsiella_pneumo_complex_output.txt  (single-row TSV)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
import pandas as pd

from .base import (ModelAdapter, Prediction, EVIDENCE_RULE,
                   CALL_RESISTANT, CALL_SUSCEPTIBLE)

PREFIX = "klebsiella_pneumo_complex__amr__"
CIPRO_COL = "klebsiella_pneumo_complex__cipro_prediction__Ciprofloxacin_prediction"

# drug -> Kleborate amr class column suffix(es) whose presence implies resistance
DRUG_COLS = {
    "amikacin": ["AGly_acquired"],
    "gentamicin": ["AGly_acquired"],
    "tobramycin": ["AGly_acquired"],
    "ciprofloxacin": ["Flq_acquired", "Flq_mutations"],
    "ceftazidime": ["Bla_ESBL_acquired", "Bla_ESBL_inhR_acquired", "Bla_Carb_acquired"],
    "cefepime": ["Bla_ESBL_acquired", "Bla_ESBL_inhR_acquired", "Bla_Carb_acquired"],
    "aztreonam": ["Bla_ESBL_acquired", "Bla_ESBL_inhR_acquired"],
    "imipenem": ["Bla_Carb_acquired"],
    "meropenem": ["Bla_Carb_acquired"],
    "piperacillin/tazobactam": ["Bla_acquired", "Bla_inhR_acquired",
                                 "Bla_ESBL_inhR_acquired", "Bla_Carb_acquired"],
    "fosfomycin": ["Fcyn_acquired"],
}
_EMPTY = {"", "-", "nan", "0", "none"}


def _present(val):
    return str(val).strip().lower() not in _EMPTY


class KleborateRules(ModelAdapter):
    name = "Kleborate"
    evidence_type = EVIDENCE_RULE
    drugs = tuple(DRUG_COLS.keys())

    def __init__(self, preset="kpsc", workdir="/tmp"):
        self.preset = preset
        self.workdir = workdir

    def is_installed(self) -> bool:
        return shutil.which("kleborate") is not None

    def predict(self, fasta_path: str) -> pd.DataFrame:
        outdir = Path(self.workdir) / (Path(fasta_path).stem + ".kleborate")
        out_tsv = outdir / "klebsiella_pneumo_complex_output.txt"
        if not out_tsv.exists():
            outdir.mkdir(parents=True, exist_ok=True)
            cmd = ["kleborate", "-a", str(fasta_path), "-o", str(outdir),
                   "-p", self.preset]
            print("[Kleborate]", " ".join(cmd), file=sys.stderr)
            subprocess.run(cmd, check=True)
        df = pd.read_csv(out_tsv, sep="\t", dtype=str).fillna("")
        row = df.iloc[0]

        preds = []
        for drug, suffixes in DRUG_COLS.items():
            genes, hit = [], False
            # ciprofloxacin: prefer Kleborate's built-in prediction
            if drug == "ciprofloxacin" and CIPRO_COL in df.columns:
                pred = str(row[CIPRO_COL]).strip().upper()
                if pred in ("R", "RESISTANT"):
                    hit = True
                elif pred in ("S", "SUSCEPTIBLE"):
                    hit = False
            for suf in suffixes:
                col = PREFIX + suf
                if col in df.columns and _present(row[col]):
                    hit = True
                    genes.extend(str(row[col]).replace(";", ",").split(","))
            genes = [g.strip() for g in genes if g.strip() and g.strip().lower() not in _EMPTY]
            preds.append(Prediction(
                drug=drug, call=CALL_RESISTANT if hit else CALL_SUSCEPTIBLE,
                prob=None, evidence_type=EVIDENCE_RULE, genes=sorted(set(genes)),
                note=("Kleborate determinant(s): " + ", ".join(sorted(set(genes))))
                if genes else "no Kleborate determinant"))
        return self._frame(preds)
