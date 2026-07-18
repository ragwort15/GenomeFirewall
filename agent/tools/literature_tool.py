"""Literature tool — paperqa2 evidence with citations, via the AGeneTic layer.

Runs in the `geneqa` env (paper-qa + OPENAI_API_KEY). Given a query it searches
PubMed/PubTator/bioRxiv, downloads open-access PDFs, CAPS the set to `max_pdfs`,
and asks paper-qa a question over them — returning an answer + ranked citations.
Best-effort: never raises (returns an error field instead).
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

AGENETIC = Path("/oak/stanford/groups/engreitz/Users/ymo/Tools/AGeneTic")


def _load_agenetic():
    # Put the AGeneTic REPO ROOT on the path (NOT src/): their wrapper package is
    # literally named `src.paperqa`, which would shadow the installed `paperqa`
    # library if `src/` were on the path. Import their wrapper as `src.paperqa`.
    if str(AGENETIC) not in sys.path:
        sys.path.insert(0, str(AGENETIC))
    import yaml
    from src.paperqa import qa                  # AGeneTic wrapper (src/paperqa/qa.py)
    from src.search import search_all           # AGeneTic search (src/search/__init__.py)
    cfg = {}
    cfg_path = AGENETIC / "config.yaml"
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
    return qa, search_all, cfg


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:60]


def literature_search(query: str, question: str, cache_dir="/tmp/gf_pdfs",
                      max_pdfs: int = 3, cfg=None) -> dict:
    """Search -> download <= max_pdfs OA PDFs -> paper-qa answer + citations.

    Returns {query, question, answer, n_pdfs, citations:[{title,citation,doi,year,
    excerpt,score}], error?}.
    """
    try:
        qa, search_all, base_cfg = _load_agenetic()
    except Exception as e:
        return {"query": query, "answer": "", "citations": [], "n_pdfs": 0,
                "error": f"literature layer unavailable: {e}"}

    cfg = {**base_cfg, **(cfg or {})}
    # keep the candidate pool small so we don't over-download before the cap
    cfg.setdefault("search", {})
    cfg["search"] = {**cfg.get("search", {}), "max_results": 3}

    pdf_dir = Path(cache_dir) / _slug(query)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    try:
        search_all(query, pdf_dir, cfg)
    except Exception as e:
        return {"query": query, "answer": "", "citations": [], "n_pdfs": 0,
                "error": f"search failed: {e}"}

    # CAP to max_pdfs (delete extras in this per-query dir)
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    for extra in pdfs[max_pdfs:]:
        try:
            extra.unlink()
        except OSError:
            pass
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        return {"query": query, "question": question, "answer": "",
                "citations": [], "n_pdfs": 0,
                "error": "no open-access PDFs retrieved"}

    try:
        settings = qa.build_settings(cfg)
        session = asyncio.run(qa.answer(question, pdf_dir, settings))
    except Exception as e:
        return {"query": query, "question": question, "answer": "",
                "citations": [], "n_pdfs": len(pdfs), "error": f"paper-qa failed: {e}"}

    contexts = sorted(session.contexts or [],
                      key=lambda c: -(c.score if c.score is not None else -1))
    seen, cites = set(), []
    for c in contexts:
        doc = getattr(c.text, "doc", None)
        title = getattr(doc, "title", None) or getattr(doc, "docname", "") or ""
        key = title[:80]
        if key in seen:
            continue
        seen.add(key)
        cites.append({
            "title": title,
            "citation": getattr(doc, "citation", "") or "",
            "doi": getattr(doc, "doi", "") or "",
            "year": getattr(doc, "year", "") or "",
            "score": c.score,
            "excerpt": (c.context or "")[:280],
        })
        if len(cites) >= max_pdfs:
            break
    return {"query": query, "question": question,
            "answer": session.answer or "", "n_pdfs": len(pdfs), "citations": cites}
