"""Download K. pneumoniae AST labels (and optionally genomes) from BV-BRC.

BV-BRC (ex-PATRIC) is the primary data source. Per the challenge brief we keep
ONLY laboratory-measured results: genome_amr records that carry a real
`laboratory_typing_method` (MIC / disk diffusion / broth microdilution / agar
dilution ...). Records with an empty method are general/predicted phenotypes and
are DROPPED.

Outputs (under --out):
  labels.tsv     genome_id  antibiotic  phenotype(R/S)  method  measurement  unit
  summary.tsv    per-antibiotic R/S counts
  genomes/<id>.fna   (only with --download-fasta)

Usage:
  python download_bvbrc.py --out data/bvbrc_kp            # labels only
  python download_bvbrc.py --out data/bvbrc_kp --download-fasta --max-genomes 50
"""
from __future__ import annotations

import argparse
import io
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

API = "https://bv-brc.org/api/genome_amr/"
FTP_HTTPS = "https://ftp.bvbrc.org/genomes"   # <id>/<id>.fna
KP_TAXON = 573

# our covered drugs. Matching is normalization-based (see _norm) so all BV-BRC
# separator spellings collapse: "piperacillin/tazobactam", "piperacillin-
# tazobactam", "piperacillin tazobactam" -> "piperacillintazobactam".
DRUGS = {
    "amikacin": ["amikacin"],
    "aztreonam": ["aztreonam"],
    "ceftazidime": ["ceftazidime"],
    "cefepime": ["cefepime"],
    "ciprofloxacin": ["ciprofloxacin"],
    "fosfomycin": ["fosfomycin", "fosfomycintrometamol"],
    "gentamicin": ["gentamicin"],
    "imipenem": ["imipenem"],
    "meropenem": ["meropenem"],
    "tobramycin": ["tobramycin"],
    "piperacillin/tazobactam": ["piperacillintazobactam"],
}


def _norm(name: str) -> str:
    """lowercase; strip separators/space so spelling variants collapse."""
    return "".join(c for c in name.strip().lower() if c.isalnum())


ALIAS = {_norm(a): std for std, aliases in DRUGS.items() for a in aliases}

SELECT = ("genome_id,genome_name,antibiotic,resistant_phenotype,"
          "laboratory_typing_method,measurement,measurement_unit,measurement_sign")
PHENO = {"resistant": "R", "susceptible": "S"}   # Intermediate dropped by default


def _fetch_page(offset, chunk):
    # No server-side antibiotic filter (drug-name spellings vary and RQL value
    # encoding is fragile); fetch all K. pneumoniae AST rows and filter client-
    # side with _norm(). taxon 573 = K. pneumoniae.
    rql = (f"eq(taxon_id,{KP_TAXON})"
           f"&select({SELECT})&limit({chunk},{offset})&http_accept=text/tsv")
    url = API + "?" + urllib.parse.quote(rql, safe="=&(),+")
    req = urllib.request.Request(url, headers={"Accept": "text/tsv"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def fetch_labels(chunk=25000, keep_intermediate=False):
    """Paginate genome_amr; return list of dicts (lab-measured only)."""
    rows, offset, header = [], 0, None
    while True:
        text = _fetch_page(offset, chunk)
        lines = text.splitlines()
        if not lines:
            break
        if header is None:
            header = [h.strip().strip('"') for h in lines[0].split("\t")]
        data = lines[1:]
        if not data:
            break
        for ln in data:
            vals = [v.strip().strip('"') for v in ln.split("\t")]
            rec = dict(zip(header, vals))
            method = rec.get("laboratory_typing_method", "").strip()
            if not method:                       # DROP non-lab-measured
                continue
            pheno = rec.get("resistant_phenotype", "").strip().lower()
            if pheno not in PHENO and not (keep_intermediate and pheno == "intermediate"):
                continue
            drug = ALIAS.get(_norm(rec.get("antibiotic", "")))
            if not drug:
                continue
            rows.append({
                "genome_id": rec["genome_id"], "antibiotic": drug,
                "phenotype": PHENO.get(pheno, "I"), "method": method,
                "measurement": rec.get("measurement", ""),
                "unit": rec.get("measurement_unit", ""),
            })
        print(f"[bvbrc] offset {offset}: +{len(data)} rows (kept total {len(rows)})",
              file=sys.stderr)
        if len(data) < chunk:
            break
        offset += chunk
        time.sleep(0.3)
    return rows


def dedup(rows):
    """Collapse duplicate (genome_id, antibiotic): majority phenotype; drop ties."""
    votes = defaultdict(Counter)
    meta = {}
    for r in rows:
        votes[(r["genome_id"], r["antibiotic"])][r["phenotype"]] += 1
        meta[(r["genome_id"], r["antibiotic"])] = r
    out = []
    for key, c in votes.items():
        top = c.most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            continue  # conflicting labels -> drop
        m = meta[key]; m = {**m, "phenotype": top[0][0]}
        out.append(m)
    return out


def write_outputs(rows, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    with open(out / "labels.tsv", "w") as f:
        f.write("genome_id\tantibiotic\tphenotype\tmethod\tmeasurement\tunit\n")
        for r in rows:
            f.write(f'{r["genome_id"]}\t{r["antibiotic"]}\t{r["phenotype"]}\t'
                    f'{r["method"]}\t{r["measurement"]}\t{r["unit"]}\n')
    summ = defaultdict(Counter)
    for r in rows:
        summ[r["antibiotic"]][r["phenotype"]] += 1
    with open(out / "summary.tsv", "w") as f:
        f.write("antibiotic\tR\tS\ttotal\n")
        for drug in sorted(summ):
            c = summ[drug]
            f.write(f'{drug}\t{c["R"]}\t{c["S"]}\t{c["R"]+c["S"]}\n')
    print(f"[bvbrc] wrote {len(rows)} labels -> {out/'labels.tsv'}")
    return out


def download_fastas(rows, out_dir, max_genomes=None):
    gids = sorted({r["genome_id"] for r in rows})
    if max_genomes:
        gids = gids[:max_genomes]
    gdir = Path(out_dir) / "genomes"; gdir.mkdir(parents=True, exist_ok=True)
    ok = 0
    for gid in gids:
        dest = gdir / f"{gid}.fna"
        if dest.exists():
            ok += 1; continue
        url = f"{FTP_HTTPS}/{gid}/{gid}.fna"
        try:
            urllib.request.urlretrieve(url, dest)
            ok += 1
        except Exception as e:
            print(f"[bvbrc] FASTA {gid} failed: {e}", file=sys.stderr)
        time.sleep(0.1)
    print(f"[bvbrc] downloaded {ok}/{len(gids)} FASTAs -> {gdir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--chunk", type=int, default=25000)
    ap.add_argument("--keep-intermediate", action="store_true")
    ap.add_argument("--download-fasta", action="store_true")
    ap.add_argument("--max-genomes", type=int, default=None)
    args = ap.parse_args()
    rows = dedup(fetch_labels(args.chunk, args.keep_intermediate))
    write_outputs(rows, args.out)
    if args.download_fasta:
        download_fastas(rows, args.out, args.max_genomes)


if __name__ == "__main__":
    main()
