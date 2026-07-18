#!/bin/bash
#SBATCH -J gf_build
#SBATCH -p normal
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=16GB
#SBATCH -o /scratch/users/ymo/gf_build_%j.out
#SBATCH -e /scratch/users/ymo/gf_build_%j.err
#
# Stage 0: assemble the benchmark pilot — select ~200 K. pneumoniae genomes,
# download their FASTAs from BV-BRC, and build the Mash grouped split.
# Download + mash are compute/network work, so this runs as a job (not login node).

set -euo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"
conda activate genomefirewall
cd "$PROJ"

N=${1:-200}
WORKDIR=${2:-$SCRATCH/genomefirewall/pilot}

echo "=== build pilot dataset (N=$N -> $WORKDIR) ==="
python -m eval.build_dataset --n "$N" --workdir "$WORKDIR"
echo "=== DONE ==="
ls -la "$WORKDIR"
