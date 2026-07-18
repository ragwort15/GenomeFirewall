#!/bin/bash
#SBATCH -J gf_v2
#SBATCH -p normal
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=12GB
#SBATCH -o /scratch/users/ymo/gf_v2_%j.out
#SBATCH -e /scratch/users/ymo/gf_v2_%j.err
set -uo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"; conda activate genomefirewall; cd "$PROJ"
FNA=data/smoke/GCF_000240185.1_ASM24018v2.fna

echo "############ ENSEMBLE (AMRFinderPlus + WGS_to_AMR) ############"
python run_pipeline.py -i "$FNA" --sample-id KP-HS11286 \
  --models AMRFinderPlus,WGS_to_AMR --workdir "$SCRATCH/gf_v2" -o data/smoke/report_full.json || true
python - <<'PY'
import json
try:
    r=json.load(open("data/smoke/report_full.json"))
    print("models:",r["models_used"]," summary:",r["summary"])
    for d in r["drugs"]:
        votes="  ".join(f'{v["model"]}={v["call"]}'+(f'({v["prob"]:.2f})' if v["prob"] is not None else '') for v in d["model_votes"])
        print(f'{d["drug"]:24s} {d["verdict"]:15s} cat({d["evidence_category"]}) conf={d["confidence"]} | {votes}')
except Exception as e:
    print("report read error:",e)
PY

echo; echo "############ KLEBORATE output columns ############"
rm -rf "$SCRATCH/gf_v2/kleborate"
kleborate -a "$FNA" -o "$SCRATCH/gf_v2/kleborate" -p kpsc 2>&1 | tail -5
echo "--- output files ---"; ls -la "$SCRATCH/gf_v2/kleborate" 2>/dev/null
for f in "$SCRATCH/gf_v2/kleborate"/*.txt; do
  echo "=== $f (header + row, resistance-relevant cols) ==="
  head -1 "$f" | tr '\t' '\n' | grep -niE "res|bla|agly|flq|fcyn|carb|esbl|tet|sul|colistin|Omp" | head -40
done
echo "=== DONE ==="
