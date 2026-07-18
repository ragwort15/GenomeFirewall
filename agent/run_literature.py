"""Attach paperqa2 literature evidence to a decision report (max N PDFs total).

Picks the most clinically important detected determinant from report.json (KPC /
carbapenemase preferred), runs ONE paper-qa search capped to --max-pdfs, and:
  * stores the result at report["literature"] (answer + citations + n_pdfs)
  * also attaches the citation list to each drug whose supporting_genes include
    that determinant (so the per-drug cards show provenance)
Writes literature.json alongside and rewrites report.json in place.

    conda activate geneqa   # paper-qa + OPENAI_API_KEY
    python -m agent.run_literature data/smoke/report.json --max-pdfs 3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.tools.literature_tool import literature_search

# preference order for which determinant to research (most clinically decisive first)
PRIORITY = ["blaKPC", "blaNDM", "blaOXA-48", "blaVIM", "rmtB", "armA",
            "blaCTX-M", "blaSHV", "gyrA", "fosA"]


def pick_determinant(report: dict):
    genes = []
    for d in report.get("drugs", []):
        for g in d.get("supporting_genes", []) or []:
            if g not in genes:
                genes.append(g)
    for pref in PRIORITY:
        for g in genes:
            if g.lower().startswith(pref.lower()):
                return g
    return genes[0] if genes else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json")
    ap.add_argument("--max-pdfs", type=int, default=3)
    ap.add_argument("--cache-dir", default=None)
    args = ap.parse_args()

    report = json.load(open(args.report_json))
    gene = pick_determinant(report)
    if not gene:
        print("[run_literature] no determinant in report; nothing to search")
        return

    base = gene.split("_")[0]          # e.g. blaKPC-2 -> blaKPC-2; gyrA_S83I -> gyrA
    query = f"{base} antimicrobial resistance Klebsiella pneumoniae"
    question = (f"How does {base} confer antibiotic resistance in Klebsiella "
                f"pneumoniae, and which antibiotics does it affect? Summarize the "
                f"mechanism and clinical relevance.")
    cache = args.cache_dir or str(Path(args.report_json).parent / "pdf_cache")
    print(f"[run_literature] researching {gene} (query: {query!r}, max {args.max_pdfs} PDFs)")

    lit = literature_search(query, question, cache_dir=cache, max_pdfs=args.max_pdfs)
    lit["determinant"] = gene
    report["literature"] = lit

    # attach citations to drugs that share this determinant
    for d in report.get("drugs", []):
        if any(g.split("_")[0].lower() == base.lower()
               for g in (d.get("supporting_genes") or [])):
            d["literature"] = lit.get("citations", [])

    out_lit = str(Path(args.report_json).with_name("literature.json"))
    json.dump(lit, open(out_lit, "w"), indent=2)
    json.dump(report, open(args.report_json, "w"), indent=2)
    print(f"[run_literature] determinant={gene}  n_pdfs={lit.get('n_pdfs')}  "
          f"citations={len(lit.get('citations', []))}  error={lit.get('error','-')}")
    print(f"[run_literature] wrote {out_lit} and updated {args.report_json}")


if __name__ == "__main__":
    main()
