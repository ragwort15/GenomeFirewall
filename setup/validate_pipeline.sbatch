#!/bin/bash
#SBATCH -J gf_validate
#SBATCH -p normal
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8GB
#SBATCH -o /scratch/users/ymo/gf_validate_%j.out
#SBATCH -e /scratch/users/ymo/gf_validate_%j.err
#
# One-genome end-to-end validation on a real BV-BRC draft assembly (renumbered
# headers): AMRFinderPlus + adapters + aggregate -> report. Confirms the pipeline
# survives multi-contig drafts before the full prediction array is launched.

set -euo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"
conda activate genomefirewall
cd "$PROJ"

python run_pipeline.py \
  -i "$SCRATCH/gf_validate/genomes/573.23197.fna" \
  --sample-id 573.23197 \
  --workdir "$SCRATCH/gf_validate/tmp" \
  -o "$SCRATCH/gf_validate/573.23197.report.json"
echo "=== report drugs ==="
python - <<'PY'
import json
r=json.load(open("/scratch/users/ymo/gf_validate/573.23197.report.json"))
print("models_used:", r["models_used"]); print("summary:", r["summary"])
for d in r["drugs"]:
    print(f'  {d["drug"]:26s} {d["verdict"]:16s} cat({d["evidence_category"]}) '
          f'conf={d["confidence"]} votes={[(v["model"],v["call"],v["prob"]) for v in d["model_votes"]]}')
PY
echo "=== DONE ==="
