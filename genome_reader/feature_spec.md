# Module 1 — Feature specification (FASTA → features)

Documented, repeatable path from a quality-checked assembly FASTA to model
features. Default annotation tool: **AMRFinderPlus** (NCBI, public-domain).

## Pipeline
```
assembly.fasta
  └─ run_amrfinder.py  ──►  amrfinder --nucleotide --organism Klebsiella_pneumoniae --plus
                            └─ amrfinder.tsv
  └─ features.py       ──►  GenomeFeatures + gene→drug evidence map + target-gate
```

## `amrfinder.tsv` (input to feature extraction)
Standard AMRFinderPlus columns used here (others ignored):
`Element type` (keep `AMR`; drop `STRESS`/`VIRULENCE`), `Element subtype`
(`AMR` vs `POINT`), `Gene symbol`, `Class`, `Subclass`, `% Identity to reference`,
`% Coverage of reference`.

## Feature outputs
1. **`GenomeFeatures`** (`features.extract_features`)
   - `genes`: set of AMR gene symbols present (e.g. `blaKPC-2`, `blaCTX-M-15`, `aac(6')-Ib-cr`, `fosA`, `qnrB1`).
   - `point_mutations`: set of resistance point mutations, AMRFinderPlus-formatted (e.g. `gyrA_S83I`).
   - `n_amr_elements`: convenience count.
2. **Binary feature vector** (`features.build_feature_vector`)
   - Presence/absence over a **fixed gene vocabulary** frozen at training time so
     train/infer columns always align. Order = `gene_vocab`.
3. **Gene→drug evidence map** (`features.get_gene_drug_evidence`)
   - `{drug: [determinants...]}` matched via AMRFinderPlus `Class`/`Subclass`.
   - Basis for report **evidence category (i)** (known resistance gene/mutation).
4. **Target gate** (`features.target_present(drug, features)`)
   - `(bool, explanation)`. Default `True` (targets are core chromosomal genes:
     PBPs, gyrA/parC, 30S rRNA, MurA). Override hook for detected target loss.
   - Ensures we never call "likely to work" purely from absence of resistance
     markers without confirming the drug's molecular target exists.

## Covered drugs (standardized names)
amikacin, gentamicin, tobramycin, ciprofloxacin, ceftazidime, cefepime,
aztreonam, imipenem, meropenem, piperacillin/tazobactam, fosfomycin.

## Reproducibility
- Pin AMRFinderPlus + DB version (`amrfinder --version`, `amrfinder --database_version`);
  record in the run manifest.
- Same FASTA + same DB version → identical TSV → identical features.
