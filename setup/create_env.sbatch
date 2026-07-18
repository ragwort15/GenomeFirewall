#!/bin/bash
#SBATCH -J gf_env
#SBATCH -p normal
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16GB
#SBATCH -o /scratch/users/ymo/gf_env_%j.out
#SBATCH -e /scratch/users/ymo/gf_env_%j.err
#
# Create the `genomefirewall` conda env (heavy solve + AMRFinderPlus DB
# download) on a compute node, per Sherlock policy (no heavy work on login).

set -euo pipefail

MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall

# keep caches/tmp off $HOME
export PIP_CACHE_DIR="$SCRATCH/pip_cache"
export TMPDIR="${L_SCRATCH:-$SCRATCH/tmp}"
mkdir -p "$PIP_CACHE_DIR" "$TMPDIR"

source "$MINIFORGE/etc/profile.d/conda.sh"

echo "=== [$(date)] creating env from $PROJ/envs/genomefirewall.yml ==="
mamba env create -f "$PROJ/envs/genomefirewall.yml"

conda activate genomefirewall

echo "=== updating AMRFinderPlus database ==="
amrfinder -u || echo "WARN: amrfinder -u failed; retry later with a live network"

echo "=== import smoke test ==="
python - <<'PY'
import sklearn, pandas, numpy, scipy, Bio, yaml
import openai, streamlit
print("core imports OK:", sklearn.__version__, pandas.__version__)
try:
    import paperqa
    print("paper-qa OK:", getattr(paperqa, "__version__", "?"))
except Exception as e:
    print("paper-qa import WARN:", e)
PY

echo "=== tool versions ==="
amrfinder --version || true
kleborate --version || true
mash --version || true

echo "=== [$(date)] DONE ==="
