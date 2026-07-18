#!/bin/bash
#SBATCH -J gf_patch
#SBATCH -p normal
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16GB
#SBATCH -o /scratch/users/ymo/gf_patch_%j.out
#SBATCH -e /scratch/users/ymo/gf_patch_%j.err
#
# Fix the genomefirewall env: (1) download AMRFinderPlus DB (missed when the
# original job aborted at the pip failure), (2) add streamlit/openai/pyarrow via
# conda-forge (no source builds). Then re-run the core smoke test.

set -uo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
export PIP_CACHE_DIR="$SCRATCH/pip_cache"; export TMPDIR="${L_SCRATCH:-$SCRATCH/tmp}"
source "$MINIFORGE/etc/profile.d/conda.sh"
conda activate genomefirewall
cd "$PROJ"

echo "=== install missing GUI/LLM packages from conda-forge ==="
mamba install -y -c conda-forge streamlit openai pyarrow python-dotenv || echo "WARN: conda install issue"
pip install --no-build-isolation arxiv || echo "WARN: arxiv pip"

echo "=== download AMRFinderPlus database ==="
amrfinder -u

echo "=== import + version check ==="
amrfinder --version
python -c "import pandas,sklearn,streamlit,openai; print('imports OK; streamlit',streamlit.__version__)"

echo "=== run core smoke test ==="
python run_pipeline.py \
  -i data/smoke/GCF_000240185.1_ASM24018v2.fna \
  --sample-id KP-HS11286 \
  --workdir "$SCRATCH/gf_smoke" \
  -o data/smoke/report.json

echo "=== report ==="
python - <<'PY'
import json
r=json.load(open("data/smoke/report.json"))
print("summary:",r["summary"])
print("models:",r["models_used"])
print("AMR elements:",r["genome_features"].get("n_amr_elements"))
for d in r["drugs"]:
    print(f'  {d["drug"]:26s} {d["verdict"]:16s} cat({d["evidence_category"]}) '
          f'conf={d["confidence"]} genes={d["supporting_genes"]}')
PY
echo "=== DONE $(date) ==="
