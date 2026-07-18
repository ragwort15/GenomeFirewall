"""ML adapter: SeviJordi/WGS_to_AMR (K. pneumoniae, pre-trained).

Ships trained models + `predict_AMR.sh`; takes an assembly FASTA and writes a
CSV with a genome id, per-antibiotic resistance probability, and binary R/S.
Runs in its own conda env (`AMR_prediction`); we shell out via `conda run`.

Column mapping (COL_MAP / prob-vs-call detection) is finalized against a real
output CSV during the smoke test — see external_models/WGS_to_AMR/example output.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import pandas as pd

from .base import (ModelAdapter, Prediction, EVIDENCE_ML,
                   CALL_RESISTANT, CALL_SUSCEPTIBLE, CALL_UNCERTAIN)

# WGS_to_AMR CSV column suffix (Spanish) -> our standardized drug name.
# Columns are "Prob_resistance_<suffix>" and "Prediction_<suffix>".
COL_MAP = {
    "Amikacina": "amikacin", "Aztreonam": "aztreonam", "Cefepime": "cefepime",
    "Ceftazidima": "ceftazidime", "Ciprofloxacina": "ciprofloxacin",
    "Fosfomicina": "fosfomycin", "Gentamicina": "gentamicin", "Imipenem": "imipenem",
    "Levofloxacina": "levofloxacin", "Meropenem": "meropenem",
    "Piperacilina_tazobactam": "piperacillin/tazobactam", "Tobramicina": "tobramycin",
}


class WGSToAMR(ModelAdapter):
    name = "WGS_to_AMR"
    evidence_type = EVIDENCE_ML
    drugs = tuple(sorted(set(COL_MAP.values())))

    def __init__(self, repo_dir=None, env_name="AMR_prediction",
                 conda_base="/oak/stanford/groups/engreitz/Users/ymo/miniforge3",
                 workdir="/tmp"):
        base = Path(__file__).resolve().parents[2]
        self.repo_dir = Path(repo_dir or base / "external_models" / "WGS_to_AMR")
        self.env_name = env_name
        self.conda_base = conda_base
        self.workdir = workdir

    def is_installed(self) -> bool:
        return (self.repo_dir / "predict_AMR.sh").exists() and \
               Path(self.conda_base, "envs", self.env_name).exists()

    def predict(self, fasta_path: str) -> pd.DataFrame:
        out_csv = str(Path(self.workdir) / (Path(fasta_path).stem + ".wgs2amr.csv"))
        Path(self.workdir).mkdir(parents=True, exist_ok=True)
        script = str(self.repo_dir / "predict_AMR.sh")
        fasta_path = str(Path(fasta_path).resolve())
        # Activate the env in a login shell (NOT `conda run`): predict_AMR.sh uses
        # GNU `parallel` with an exported bash function, which breaks under the
        # captured, non-login `conda run` wrapper (exit 127).
        # NOTE arg order: predict_AMR.sh requires -o FIRST then -i LAST (its -i
        # handler slurps all trailing paths). Reversing them prints usage + exit 1.
        inner = (f"source {self.conda_base}/etc/profile.d/conda.sh && "
                 f"conda activate {self.env_name} && "
                 f"bash {script} -o {out_csv} -i {fasta_path}")
        print("[WGS_to_AMR]", inner, file=sys.stderr)
        proc = subprocess.run(["bash", "-c", inner], cwd=str(self.workdir),
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"WGS_to_AMR rc={proc.returncode}\n--- STDOUT ---\n{proc.stdout[-3000:]}"
                f"\n--- STDERR ---\n{proc.stderr[-3000:]}")
        return self._parse(out_csv, sample=Path(fasta_path).stem)

    def _parse(self, csv_path: str, sample=None) -> pd.DataFrame:
        """Columns: Sample, Prob_resistance_<suffix>..., Prediction_<suffix>...
        Prediction_ holds the authoritative R/S (per-drug threshold); Prob_ is
        P(resistant). Pick the matching sample row (basename may gain '_genomic')."""
        df = pd.read_csv(csv_path)
        row = df.iloc[0]
        if sample is not None and "Sample" in df.columns:
            m = df[df["Sample"].astype(str).str.contains(str(sample), na=False)]
            if len(m):
                row = m.iloc[0]
        preds = []
        for suffix, drug in COL_MAP.items():
            pcol, dcol = f"Prob_resistance_{suffix}", f"Prediction_{suffix}"
            prob = None
            if pcol in df.columns:
                try:
                    prob = float(row[pcol])
                except (TypeError, ValueError):
                    prob = None
            call = CALL_UNCERTAIN
            if dcol in df.columns:
                val = str(row[dcol]).strip().upper()
                call = CALL_RESISTANT if val == "R" else \
                    CALL_SUSCEPTIBLE if val == "S" else CALL_UNCERTAIN
            if prob is not None or call != CALL_UNCERTAIN:
                preds.append(Prediction(drug=drug, call=call, prob=prob,
                                        evidence_type=EVIDENCE_ML))
        return self._frame(preds)
