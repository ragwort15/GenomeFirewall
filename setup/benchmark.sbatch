#!/bin/bash
#SBATCH -J gf_predict
#SBATCH -p normal
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=12GB
#SBATCH --array=0-19
#SBATCH -o /scratch/users/ymo/gf_predict_%A_%a.out
#SBATCH -e /scratch/users/ymo/gf_predict_%A_%a.err
#
# Stage 1: batch prediction over the pilot genomes (AMRFinderPlus + models +
# aggregate -> per-genome report JSON). 20 shards; each shard handles ~1/20 of the
# downloaded genomes. Re-run any failed shard: reports are idempotent.
#
#   sbatch setup/benchmark.sbatch                       # default workdir
#   sbatch setup/benchmark.sbatch $SCRATCH/genomefirewall/pilot

set -euo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"
conda activate genomefirewall
cd "$PROJ"

WORKDIR=${1:-$SCRATCH/genomefirewall/pilot}
NSHARDS=$(( ${SLURM_ARRAY_TASK_COUNT:-20} ))

echo "=== predict shard $SLURM_ARRAY_TASK_ID / $NSHARDS (workdir=$WORKDIR) ==="
python -m eval.predict_batch \
  --workdir "$WORKDIR" \
  --shard "$SLURM_ARRAY_TASK_ID" \
  --nshards "$NSHARDS"
echo "=== shard $SLURM_ARRAY_TASK_ID DONE ==="
