#!/bin/bash
#SBATCH -J gf_full
#SBATCH -p normal
#SBATCH --time=00:40:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=12GB
#SBATCH -o /scratch/users/ymo/gf_full_%j.out
#SBATCH -e /scratch/users/ymo/gf_full_%j.err
#
# Full ensemble smoke test: AMRFinderPlus (rules) + WGS_to_AMR (ML, own env) ->
# aggregate -> report. Shows per-drug verdicts + per-model votes.

set -euo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"
conda activate genomefirewall
cd "$PROJ"

python run_pipeline.py \
  -i data/smoke/GCF_000240185.1_ASM24018v2.fna \
  --sample-id KP-HS11286 \
  --workdir "$SCRATCH/gf_full" \
  -o data/smoke/report_full.json

echo "=== ENSEMBLE REPORT ==="
python - <<'PY'
import json
r=json.load(open("data/smoke/report_full.json"))
print("models:",r["models_used"]," summary:",r["summary"])
for d in r["drugs"]:
    votes="  ".join(f'{v["model"]}={v["call"]}'+(f'({v["prob"]:.2f})' if v["prob"] is not None else '')
                     for v in d["model_votes"])
    print(f'\n{d["drug"]:24s} -> {d["verdict"]:15s} cat({d["evidence_category"]}) conf={d["confidence"]}')
    print(f'    reason: {d["reason"]}')
    print(f'    votes : {votes}')
PY
echo "=== DONE ==="
