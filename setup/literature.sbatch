#!/bin/bash
#SBATCH -J gf_lit
#SBATCH -p normal
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8GB
#SBATCH -o /scratch/users/ymo/gf_lit_%j.out
#SBATCH -e /scratch/users/ymo/gf_lit_%j.err
#
# paperqa2 literature search (max 3 PDFs) attached to the decision report.
# Runs in the `geneqa` env (paper-qa) with OPENAI_API_KEY from .env; needs network
# (PubMed/bioRxiv PDF download + OpenAI API) -> compute node, not login.

set -uo pipefail
MINIFORGE=/oak/stanford/groups/engreitz/Users/ymo/miniforge3
PROJ=/oak/stanford/groups/engreitz/Users/ymo/Hackanation/GenomeFirewall
source "$MINIFORGE/etc/profile.d/conda.sh"
conda activate geneqa
cd "$PROJ"

# load OPENAI_API_KEY (+ optional NCBI creds) from .env
if [ -f .env ]; then set -a; source .env; set +a; fi
echo "OPENAI_API_KEY set: ${OPENAI_API_KEY:+yes}"

REPORT=${1:-data/smoke/report.json}
python -m agent.run_literature "$REPORT" --max-pdfs 3

echo "=== literature.json ==="
python - <<'PY'
import json
l=json.load(open("data/smoke/literature.json"))
print("determinant:",l.get("determinant")," n_pdfs:",l.get("n_pdfs")," error:",l.get("error","-"))
print("answer:", (l.get("answer") or "")[:500])
for c in l.get("citations",[]):
    print(f"  - {c.get('title','')[:90]}  {c.get('doi','')}")
PY
echo "=== DONE ==="
