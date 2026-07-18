#!/bin/bash
#SBATCH -J gf_smoke
#SBATCH -p normal
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8GB
#SBATCH -o /scratch/users/ymo/gf_smoke_%j.out
#SBATCH -e /scratch/users/ymo/gf_smoke_%j.err
#
# Core smoke test: Module 1 (AMRFinderPlus) + rule adapter + aggregate -> report.
# Uses conda-installed tools only (no pip layer needed).

set -euo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"
conda activate genomefirewall
cd "$PROJ"

echo "=== versions ==="; amrfinder --version; python -c "import pandas,sklearn;print('pandas',pandas.__version__)"
echo "=== run pipeline ==="
python run_pipeline.py \
  -i data/smoke/GCF_000240185.1_ASM24018v2.fna \
  --sample-id KP-HS11286 \
  --workdir "$SCRATCH/gf_smoke" \
  -o data/smoke/report.json
echo "=== report drugs ==="
python - <<'PY'
import json
r=json.load(open("data/smoke/report.json"))
print("summary:",r["summary"])
for d in r["drugs"]:
    print(f'  {d["drug"]:26s} {d["verdict"]:16s} cat({d["evidence_category"]}) conf={d["confidence"]} genes={d["supporting_genes"]}')
PY
echo "=== DONE ==="
