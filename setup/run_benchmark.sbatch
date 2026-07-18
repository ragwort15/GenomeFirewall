#!/bin/bash
#SBATCH -J gf_score
#SBATCH -p normal
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8GB
#SBATCH -o /scratch/users/ymo/gf_score_%j.out
#SBATCH -e /scratch/users/ymo/gf_score_%j.err
#
# Stage 2: score the pilot and write Result/benchmark_kp_pilot/.
# Pass --llm to also run the LLM decision-head arm (needs OPENAI_API_KEY in .env).
#
#   sbatch setup/run_benchmark.sbatch            # deterministic only
#   sbatch setup/run_benchmark.sbatch --llm      # + LLM decision head

set -euo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"
conda activate genomefirewall
cd "$PROJ"

# export .env (OPENAI_API_KEY) for the LLM arm
if [ -f .env ]; then set -a; source .env; set +a; fi

python -m eval.run_benchmark --workdir "$SCRATCH/genomefirewall/pilot" "$@"
echo "=== BENCHMARK.md ==="
cat Result/benchmark_kp_pilot/BENCHMARK.md 2>/dev/null || true
