#!/bin/bash
#SBATCH -J gf_wdraft
#SBATCH -p normal
#SBATCH --time=00:25:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=10GB
#SBATCH -o /scratch/users/ymo/gf_wdraft_%j.out
#SBATCH -e /scratch/users/ymo/gf_wdraft_%j.err
#
# Confirm the FIXED WGS_to_AMR adapter runs on BV-BRC DRAFT assemblies (multi-
# contig), not just the complete HS11286 — before re-running the 200-genome array.
set -uo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"; conda activate genomefirewall; cd "$PROJ"
G=/scratch/users/ymo/genomefirewall/pilot/genomes
python - <<'PY'
import os, glob
from predictor.adapters.wgs_to_amr import WGSToAMR
a = WGSToAMR(workdir=os.environ["SCRATCH"]+"/gf_wdraft")
for fna in sorted(glob.glob("/scratch/users/ymo/genomefirewall/pilot/genomes/*.fna"))[:2]:
    gid = os.path.basename(fna)[:-4]
    print(f"\n=== {gid} ===")
    try:
        df = a.predict(fna)
        print(df[["drug","call","prob"]].to_string(index=False))
    except Exception as e:
        print("FAILED:", str(e)[:1500])
PY
echo "=== DONE ==="
