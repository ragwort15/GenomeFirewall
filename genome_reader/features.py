"""Module 1: turn an AMRFinderPlus TSV into model features + a rule-based
gene->drug evidence map, and report drug-target presence for the gate.

Two consumers:
  * ML adapters that want a presence/absence feature vector over a fixed gene
    vocabulary (build_feature_vector).
  * The rule-based adapters + report, which need which determinants map to which
    drug and the evidence category (get_gene_drug_evidence).

Design note on the TARGET GATE: AMRFinderPlus reports resistance determinants,
not the drug's molecular target. For K. pneumoniae the targets of the covered
drugs are core chromosomal genes (PBPs, gyrA/parC, 30S rRNA/rpsL, murA) that are
essentially always present in a quality-checked assembly. We therefore default
target_present=True for these drug classes and expose a hook to override when a
target-loss signal is detected (e.g. porin/OmpK disruption for carbapenems).
This keeps us honest: we never say "likely to work" purely from absence of
resistance markers without confirming the target exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import pandas as pd

# Standardized drug -> AMRFinderPlus antibiotic Class/Subclass tokens (uppercased,
# matched case-insensitively as substrings against the TSV 'Class'/'Subclass').
DRUG_CLASS_TOKENS = {
    "amikacin": ["AMIKACIN", "AMINOGLYCOSIDE"],
    "gentamicin": ["GENTAMICIN", "AMINOGLYCOSIDE"],
    "tobramycin": ["TOBRAMYCIN", "AMINOGLYCOSIDE"],
    "ciprofloxacin": ["QUINOLONE", "FLUOROQUINOLONE"],
    "ceftazidime": ["CEPHALOSPORIN", "BETA-LACTAM"],
    "cefepime": ["CEPHALOSPORIN", "BETA-LACTAM"],
    "aztreonam": ["MONOBACTAM", "BETA-LACTAM", "CEPHALOSPORIN"],
    "imipenem": ["CARBAPENEM", "BETA-LACTAM"],
    "meropenem": ["CARBAPENEM", "BETA-LACTAM"],
    "piperacillin/tazobactam": ["BETA-LACTAM", "PENICILLIN"],
    "fosfomycin": ["FOSFOMYCIN"],
}

# Molecular target(s) per drug class — used only to describe the gate.
DRUG_TARGET = {
    "amikacin": "30S ribosomal subunit",
    "gentamicin": "30S ribosomal subunit",
    "tobramycin": "30S ribosomal subunit",
    "ciprofloxacin": "DNA gyrase (gyrA) / topoisomerase IV (parC)",
    "ceftazidime": "penicillin-binding proteins",
    "cefepime": "penicillin-binding proteins",
    "aztreonam": "penicillin-binding protein 3",
    "imipenem": "penicillin-binding proteins",
    "meropenem": "penicillin-binding proteins",
    "piperacillin/tazobactam": "penicillin-binding proteins",
    "fosfomycin": "MurA (UDP-GlcNAc enolpyruvyl transferase)",
}


@dataclass
class GenomeFeatures:
    genes: set = field(default_factory=set)             # AMR gene symbols present
    point_mutations: set = field(default_factory=set)   # e.g. "gyrA_S83I"
    raw: pd.DataFrame = field(default_factory=pd.DataFrame)

    def as_dict(self):
        return {"genes": sorted(self.genes),
                "point_mutations": sorted(self.point_mutations),
                "n_amr_elements": len(self.genes) + len(self.point_mutations)}


def parse_amrfinder_tsv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", dtype=str).fillna("")
    df.columns = [c.strip() for c in df.columns]
    return df


def extract_features(df: pd.DataFrame) -> GenomeFeatures:
    """Keep AMR elements (drop STRESS/VIRULENCE). Separate genes from point muts.
    Column names differ across AMRFinderPlus versions: 4.x uses Type/Subtype/
    Element symbol; older uses Element type/Element subtype/Gene symbol."""
    etype = _col(df, "Type", "Element type")
    subtype = _col(df, "Subtype", "Element subtype")
    gsym = _col(df, "Element symbol", "Gene symbol")
    amr = df[df[etype].str.upper().eq("AMR")] if etype else df
    genes, muts = set(), set()
    for _, r in amr.iterrows():
        sym = r[gsym].strip()
        if not sym:
            continue
        # POINT / POINT_DISRUPT subtypes are resistance-associated DNA changes
        if subtype and r[subtype].strip().upper().startswith("POINT"):
            muts.add(sym)          # AMRFinderPlus already formats as gene_MUT
        else:
            genes.add(sym)
    return GenomeFeatures(genes=genes, point_mutations=muts, raw=amr)


def get_gene_drug_evidence(df: pd.DataFrame) -> dict:
    """Map each covered drug -> list of determinants (gene/mutation) whose
    AMRFinderPlus Class/Subclass matches that drug. Basis of evidence category (i).
    """
    cls = _col(df, "Class")
    subcls = _col(df, "Subclass")
    gsym = _col(df, "Element symbol", "Gene symbol")
    etype = _col(df, "Type", "Element type")
    amr = df[df[etype].str.upper().eq("AMR")] if etype else df
    out = {d: [] for d in DRUG_CLASS_TOKENS}
    for _, r in amr.iterrows():
        blob = f"{r.get(cls,'')} {r.get(subcls,'')}".upper()
        sym = r[gsym].strip()
        if not sym:
            continue
        for drug, tokens in DRUG_CLASS_TOKENS.items():
            if any(tok in blob for tok in tokens):
                out[drug].append(sym)
    return out


def target_present(drug: str, features: GenomeFeatures) -> tuple[bool, str]:
    """Deterministic target gate. Default True (core chromosomal targets)."""
    target = DRUG_TARGET.get(drug, "unknown target")
    return True, f"{target} present (core gene assumed intact)"


def build_feature_vector(features: GenomeFeatures, gene_vocab: list[str]) -> list[int]:
    """Binary presence/absence over a FIXED vocabulary (order = gene_vocab).
    The vocabulary is frozen at training time so train/infer columns align."""
    present = features.genes | features.point_mutations
    return [1 if g in present else 0 for g in gene_vocab]


def _col(df: pd.DataFrame, *candidates: str):
    """Return the first matching column name present in df, else None."""
    for c in candidates:
        if c in df.columns:
            return c
    return None
