#!/bin/bash
#SBATCH -J gf_smoke3
#SBATCH -p normal
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=12GB
#SBATCH -o /scratch/users/ymo/gf_smoke3_%j.out
#SBATCH -e /scratch/users/ymo/gf_smoke3_%j.err
#
# Full 3-model ensemble smoke test: AMRFinderPlus + Kleborate (rules) + WGS_to_AMR (ML).

set -uo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"; conda activate genomefirewall; cd "$PROJ"

echo "available models: $(python -c 'from predictor import registry;print(registry.available_models())')"

python run_pipeline.py -i data/smoke/GCF_000240185.1_ASM24018v2.fna \
  --sample-id KP-HS11286 --workdir "$SCRATCH/gf_smoke3" -o data/smoke/report.json

echo "=== 3-MODEL ENSEMBLE ==="
python - <<'PY'
import json
r=json.load(open("data/smoke/report.json"))
print("models:",r["models_used"]," summary:",r["summary"])
print("AMR elements:",r["genome_features"]["n_amr_elements"],
      "| point_mutations:",r["genome_features"]["point_mutations"])
for d in r["drugs"]:
    votes=" ".join(f'{v["model"][:5]}={v["call"]}'+(f'{v["prob"]:.2f}' if v["prob"] is not None else '')
                   for v in d["model_votes"])
    print(f'{d["drug"]:24s} {d["verdict"]:15s} cat({d["evidence_category"]}) conf={d["confidence"]} | {votes}')
PY
echo "=== DONE ==="
