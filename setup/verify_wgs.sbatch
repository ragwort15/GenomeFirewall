#!/bin/bash
#SBATCH -J gf_vwgs
#SBATCH -p normal
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8GB
#SBATCH -o /scratch/users/ymo/gf_vwgs_%j.out
#SBATCH -e /scratch/users/ymo/gf_vwgs_%j.err
set -uo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"; conda activate genomefirewall; cd "$PROJ"
python - <<'PY'
from predictor.adapters.wgs_to_amr import WGSToAMR
import os
a = WGSToAMR(workdir=os.environ["SCRATCH"]+"/gf_wgs")
print("installed:", a.is_installed())
try:
    df = a.predict("data/smoke/GCF_000240185.1_ASM24018v2.fna")
    print(df.to_string(index=False))
except Exception as e:
    print("PREDICT ERROR:\n", str(e)[:4000])
PY
