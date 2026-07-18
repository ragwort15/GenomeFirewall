# Genome Firewall — Benchmark (K. pneumoniae pilot)

- Workdir: `/scratch/users/ymo/genomefirewall/pilot`
- Genomes scored: 200 (153 Mash clusters @ dist<= 0.0005)
- Labels scored: 1419

## System comparison (macro-averaged over drugs)

| system | scope | balanced_acc | recall_R | recall_S | f1 | auroc | pr_auc | no_call | brier |
|---|---|---|---|---|---|---|---|---|---|
| deterministic | pooled | 0.744 | 0.858 | 0.629 | 0.713 | 0.746 | 0.692 | 0.0 | 0.2184 |
| deterministic | cluster-dedup | 0.765 | 0.856 | 0.674 | 0.708 | 0.768 | 0.68 | 0.0 | - |
| llm | pooled | 0.762 | 0.983 | 0.541 | 0.832 | 0.893 | 0.853 | 0.006 | 0.1961 |
| llm | cluster-dedup | 0.786 | 0.978 | 0.593 | 0.851 | 0.923 | 0.925 | 0.007 | - |

## Per-drug tables

- `per_drug_metrics__deterministic.csv`
- `per_drug_metrics__llm.csv`

## Generalization by genetic group
- Per-cluster breakdown: `by_group.csv` (153 clusters; largest = 14 genomes)
- POOLED counts every genome (clonal lineages over-represented); CLUSTER-DEDUP keeps one genome per Mash cluster — the honest generalization number.

## Caveats (read before trusting numbers)
- **Pretrained-model leakage:** any ML adapter (e.g. WGS_to_AMR) was trained on BV-BRC K. pneumoniae, so pilot genomes may be in its training set — this inflates ML/aggregator scores. The Mash split fixes *own-model* leakage, not pretrained leakage.
- **Probability coverage:** AUROC / PR-AUC / Brier need a P(resistant); rule-only predictions have none, so those columns are NaN unless an ML adapter contributes.
- Every result must be confirmed by standard laboratory testing (research prototype).
