#!/bin/bash
#SBATCH -J gf_models
#SBATCH -p normal
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=24GB
#SBATCH -o /scratch/users/ymo/gf_models_%j.out
#SBATCH -e /scratch/users/ymo/gf_models_%j.err
#
# Clone the external published-model repos and build their (isolated) envs.
# Priority: WGS_to_AMR (pre-trained K. pneumoniae) so the smoke test can run.
# PhenotypeSeeker / Kover / AMR-GNN ship training code only — cloned here,
# trained later on the organizer dataset.

set -uo pipefail

MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
EXT=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall/external_models
export PIP_CACHE_DIR="$SCRATCH/pip_cache"; export TMPDIR="${L_SCRATCH:-$SCRATCH/tmp}"
mkdir -p "$EXT" "$PIP_CACHE_DIR" "$TMPDIR"
source "$MINIFORGE/etc/profile.d/conda.sh"

clone(){ # url dir
  if [ -d "$EXT/$2/.git" ]; then echo "[$2] already cloned"; else
    echo "=== cloning $2 ==="; git clone --depth 1 "$1" "$EXT/$2" || echo "WARN: clone $2 failed"; fi
}

command -v git-lfs >/dev/null 2>&1 && git lfs install || echo "(no git-lfs; large weights may be skipped)"

clone https://github.com/SeviJordi/WGS_to_AMR.git        WGS_to_AMR
clone https://github.com/bioinfo-ut/PhenotypeSeeker.git  PhenotypeSeeker
clone https://github.com/aldro61/kover.git               kover
clone https://github.com/andyvng/amr-gnn.git             amr-gnn

echo "=== building WGS_to_AMR env (AMR_prediction) ==="
if [ -f "$EXT/WGS_to_AMR/requirements.yaml" ]; then
  mamba env create -f "$EXT/WGS_to_AMR/requirements.yaml" -y || echo "WARN: AMR_prediction env create failed"
elif [ -f "$EXT/WGS_to_AMR/requirements.yml" ]; then
  mamba env create -f "$EXT/WGS_to_AMR/requirements.yml" -y || echo "WARN: env create failed"
else
  echo "WARN: no requirements.yaml in WGS_to_AMR — inspect repo"
fi

echo "=== repo inventory (for tailoring remaining envs) ==="
for d in WGS_to_AMR PhenotypeSeeker kover amr-gnn; do
  echo "----- $d -----"; ls -la "$EXT/$d" 2>/dev/null | head -30
  echo "  [env/req files]:"; find "$EXT/$d" -maxdepth 2 \
    \( -name "*.yaml" -o -name "*.yml" -o -name "requirements*.txt" -o -name "install.sh" -o -name "setup.py" -o -name "environment*" \) 2>/dev/null | head
done

echo "=== conda envs now ==="; conda env list
echo "=== DONE $(date) ==="
