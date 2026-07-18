"""Render a decision-report JSON (from agent/report.py) to a self-contained
static HTML file — same look as app/mock_report.html but populated with REAL data.

    python -m agent.html_report data/smoke/report.json -o data/smoke/report.html
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

VC = {"likely_to_fail": ("#c0392b", "#fdecea", "#f3b6ae", "LIKELY TO FAIL"),
      "likely_to_work": ("#1e7e46", "#e9f7ef", "#a7dcbd", "LIKELY TO WORK"),
      "no_call": ("#8a6d00", "#fbf4dd", "#ecd98a", "NO-CALL")}
CATC = {"i": ("#e7eefc", "#274b9a"), "ii": ("#f3ecfb", "#6b3ea6"), "iii": ("#eef3f7", "#4a6172")}
CALL_TXT = {"R": "Resistant", "S": "Susceptible", "U": "Uncertain"}


def _esc(x):
    return html.escape(str(x))


def _pill(drug, verdict):
    c, bg, br, _ = VC[verdict]
    return (f"<span style='background:{bg};color:{c};border:1px solid {br};padding:3px 10px;"
            f"border-radius:16px;font-size:12.5px;font-weight:600;margin:2px;display:inline-block'>{_esc(drug)}</span>")


def _votes_table(votes):
    rows = ""
    for v in votes:
        prob = "—" if v.get("prob") is None else f"{float(v['prob']):.2f}"
        et = v.get("evidence_type", "")
        badge = "rule" if et == "rule" else "ML"
        bc, bbg = ("#274b9a", "#e7eefc") if et == "rule" else ("#6b3ea6", "#f3ecfb")
        call = CALL_TXT.get(v.get("call"), v.get("call", ""))
        cc = {"Resistant": "#c0392b", "Susceptible": "#1e7e46"}.get(call, "#8a6d00")
        rows += (f"<tr><td>{_esc(v['model'])}</td>"
                 f"<td><span style='font-size:10px;padding:2px 6px;border-radius:5px;background:{bbg};color:{bc}'>{badge}</span></td>"
                 f"<td style='font-weight:700;color:{cc}'>{call}</td><td>{prob}</td></tr>")
    return f"<table class='v'><tr><th>Model</th><th>Type</th><th>Call</th><th>P(res)</th></tr>{rows}</table>"


def _drug_card(d):
    c, bg, br, vlabel = VC[d["verdict"]]
    conf = ("insufficient / conflicting" if d["confidence"] is None
            else f"{round(d['confidence']*100)}% confidence")
    fillw = 100 if d["confidence"] is None else round(d["confidence"] * 100)
    fillc = "#e0d9b0" if d["confidence"] is None else c
    catbg, catc = CATC.get(d["evidence_category"], ("#eee", "#333"))
    genes = d.get("supporting_genes") or []
    gchips = ("".join(f"<span class='g'>{_esc(g)}</span>" for g in genes)
              if genes else "<span class='g' style='opacity:.6'>none detected</span>")
    lit = "".join(
        f"<div class='ref'><b>{_esc(r.get('title','') or 'source')}</b> "
        f"<span class='mono'>{_esc(r.get('doi',''))}</span></div>"
        for r in (d.get("literature") or []))
    lit_block = f"<h4>Literature (paper-qa)</h4>{lit}" if lit else ""
    return f"""
    <div class="drug">
      <div class="hd" onclick="this.parentElement.classList.toggle('open')">
        <span class="verdict" style="background:{bg};color:{c};border:1px solid {br}">{vlabel}</span>
        <div class="name">{_esc(d['drug'])}</div>
        <div class="conf"><div class="bar"><div class="fill" style="width:{fillw}%;background:{fillc}"></div></div>
          <div class="ct">{conf}</div></div>
        <span class="cat" style="background:{catbg};color:{catc}">evidence {d['evidence_category']}</span>
        <span class="chev">▸</span>
      </div>
      <div class="body">
        <div class="gate">🎯 Target gate: {_esc(d.get('target_note') or 'n/a')}</div>
        <p class="reason"><b>Reason:</b> {_esc(d['reason'])}<br>
           <b>Evidence ({d['evidence_category']}):</b> {_esc(d.get('evidence_label',''))}</p>
        <h4>Supporting genes / DNA changes</h4><div class="chips">{gchips}</div>
        <h4>Per-model output (ensemble)</h4>{_votes_table(d['model_votes'])}
        {lit_block}
      </div>
    </div>"""


def _patient_panel(report):
    cc = report.get("clinical_context") or {}
    if not cc:
        return ("<div class='card'><h2>Patient / clinical context</h2>"
                "<div class='empty'>No clinical record provided — genomic prediction only.<br>"
                "<span class='muted'>Clinical context (infection site, prior antibiotics, "
                "allergies, renal function) can be added later; it informs interpretation only, "
                "never the genomic probability.</span></div></div>")
    rows = "".join(f"<div class='k'>{_esc(k)}</div><div>{_esc(v)}</div>" for k, v in cc.items())
    return (f"<div class='card'><h2>Patient / clinical context</h2>"
            f"<div class='kv'>{rows}</div>"
            f"<p class='muted'>Context informs interpretation only, not the genomic probability.</p></div>")


def _literature_panel(report):
    lit = report.get("literature") or {}
    cites = lit.get("citations") or []
    head = "<div class='card lit'><h2>Literature &amp; clinical research</h2>"
    if not cites:
        why = lit.get("error") or "no open-access literature retrieved"
        det = lit.get("determinant", "")
        return (head + f"<div class='empty'>No literature attached "
                f"{'for ' + _esc(det) if det else ''}.<br><span class='muted'>{_esc(why)}</span>"
                "</div></div>")
    det = lit.get("determinant", "")
    npdf = lit.get("n_pdfs", len(cites))
    ans = lit.get("answer", "")
    body = (f"<p class='muted'>paper-qa over {npdf} open-access PDF(s) for "
            f"<b>{_esc(det)}</b>.</p>")
    if ans:
        body += f"<p class='ans'>{_esc(ans[:600])}</p>"
    for r in cites:
        title = _esc(r.get("title", "") or "source")
        cite = _esc(r.get("citation", "") or "")
        doi = r.get("doi", "")
        link = (f"<a href='https://doi.org/{_esc(doi)}'>doi:{_esc(doi)}</a>" if doi else "")
        exc = _esc((r.get("excerpt", "") or "")[:220])
        body += (f"<div class='ref'><div class='t'>{title}</div>"
                 f"<div class='m'>{cite} {link}</div>"
                 f"<div class='q'>{exc}</div></div>")
    return head + body + "</div>"


def render_html(r: dict) -> str:
    s = r["summary"]
    gf = r.get("genome_features", {})
    buckets = {"likely_to_work": [], "no_call": [], "likely_to_fail": []}
    for d in r["drugs"]:
        buckets[d["verdict"]].append(d["drug"])
    rec_lines = ""
    for v, lbl in [("likely_to_work", "Predicted effective"),
                   ("no_call", "Uncertain — no call"),
                   ("likely_to_fail", "Predicted to fail")]:
        if buckets[v]:
            rec_lines += (f"<div class='rl'><span class='lbl'>{lbl}</span>"
                          + "".join(_pill(x, v) for x in buckets[v]) + "</div>")
    cards = "".join(_drug_card(d) for d in r["drugs"])
    muts = ", ".join(gf.get("point_mutations", []) or []) or "none"
    genes = ", ".join(gf.get("genes", []) or []) or "none"
    cov = r.get("coverage", {})
    summ = (f"<p class='muted' style='margin-top:10px'>{_esc(r.get('clinician_summary',''))}</p>"
            if r.get("clinician_summary") else "")
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Genome Firewall — {_esc(r['sample_id'])}</title>
<style>
:root{{--navy:#0f2a43;--teal:#1f8a8a;--ink:#20313f;--muted:#6b7c8a;--line:#e3e9ef;--bg:#f4f7fa}}
*{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg);font-size:14.5px;line-height:1.45}}
header{{background:linear-gradient(135deg,#0f2a43,#163a5c);color:#fff;padding:16px 26px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}}
header h1{{font-size:19px;margin:0}} header .sub{{font-size:12px;opacity:.85}}
.tag{{background:#1f8a8a;color:#fff;font-size:11px;font-weight:700;padding:4px 9px;border-radius:20px}}
.wrap{{max-width:1180px;margin:0 auto;padding:22px}}
.safety{{background:#fff3cd;border-left:6px solid #e0a800;color:#5c4700;padding:12px 16px;border-radius:10px;margin-bottom:18px}}
.card{{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 1px 3px rgba(16,42,67,.08);padding:18px 20px;margin-bottom:18px}}
.card h2{{font-size:15px;margin:0 0 12px;color:var(--navy)}}
.strip{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:18px}}
.stat{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.stat .n{{font-size:26px;font-weight:700}} .stat .l{{font-size:12px;color:var(--muted);margin-top:4px}}
.fail .n{{color:#c0392b}} .work .n{{color:#1e7e46}} .nc .n{{color:#8a6d00}}
.grid2{{display:grid;grid-template-columns:1.55fr 1fr;gap:18px;align-items:start}}
@media(max-width:960px){{.grid2{{grid-template-columns:1fr}}}}
.rl{{margin:6px 0}} .rl .lbl{{font-size:12px;color:var(--muted);margin-right:8px}}
.muted{{color:var(--muted);font-size:12.5px}}
.empty{{padding:14px;border:1px dashed #c7d3dd;border-radius:10px;background:#fbfdff;color:#54677a;font-size:13px}}
.kv{{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:13px}} .kv .k{{color:var(--muted)}}
.drug{{border:1px solid var(--line);border-radius:12px;margin-bottom:11px;overflow:hidden}}
.hd{{display:flex;align-items:center;gap:12px;padding:12px 15px;cursor:pointer}} .hd:hover{{background:#fafcfe}}
.verdict{{font-weight:700;font-size:12px;padding:4px 10px;border-radius:7px;white-space:nowrap}}
.name{{font-weight:650;font-size:15px;flex:1}}
.conf{{min-width:120px}} .bar{{height:8px;background:#eef2f6;border-radius:6px;overflow:hidden}} .fill{{height:100%}}
.ct{{font-size:11px;color:var(--muted);text-align:right;margin-top:3px}}
.cat{{font-size:10.5px;font-weight:700;padding:3px 8px;border-radius:6px}}
.chev{{color:var(--muted)}} .drug.open .chev{{transform:rotate(90deg)}}
.body{{display:none;padding:6px 16px 16px;border-top:1px solid var(--line);background:#fbfdff}} .drug.open .body{{display:block}}
.body h4{{margin:13px 0 7px;font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted)}}
.gate{{font-size:12.5px;padding:8px 11px;border-radius:8px;background:#eef6ff;border:1px solid #cfe2f2;color:#2b5c86;margin-top:6px}}
.reason{{font-size:13px}} .chips{{display:flex;gap:6px;flex-wrap:wrap}}
.g{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:3px 10px;font-size:12px;font-family:ui-monospace,Menlo,monospace}}
table.v{{width:100%;border-collapse:collapse;font-size:12.5px}} table.v th,table.v td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}}
table.v th{{color:var(--muted);font-size:11px;text-transform:uppercase}}
.lit .ref{{border-left:3px solid var(--teal);padding:8px 11px;background:#fff;border:1px solid var(--line);border-left-width:3px;border-radius:0 8px 8px 0;margin-bottom:9px}}
.lit .ref .t{{font-weight:600;font-size:13px}} .lit .ref .m{{font-size:11.5px;color:var(--muted);margin:3px 0}}
.lit .ref .q{{font-size:12px;color:#3a4b58;font-style:italic}} .lit .ans{{font-size:12.5px;background:#f2fbfb;border-radius:8px;padding:9px 11px}}
.lit a{{color:var(--teal);text-decoration:none}} .lit a:hover{{text-decoration:underline}}
.ref .t{{font-weight:600}}
.mono{{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:#3a4b58;word-break:break-word}}
footer{{max-width:1180px;margin:8px auto 40px;padding:0 22px;color:var(--muted);font-size:12px}}
</style></head><body>
<header><div><h1>🧬🛡️ Genome Firewall</h1>
  <div class="sub">Antibiotic-response report · <i>{_esc(r['species'])}</i> · sample {_esc(r['sample_id'])} · {_esc(r['generated_utc'][:19])}Z</div></div>
  <div class="tag">MODELS: {_esc(', '.join(r.get('models_used', [])))}</div></header>
<div class="wrap">
  <div class="safety">⚠️ <b>{_esc(r['disclaimer'])}</b></div>
  <div class="strip">
    <div class="stat"><div class="n">{s['n_drugs']}</div><div class="l">Antibiotics</div></div>
    <div class="stat fail"><div class="n">{s['n_likely_to_fail']}</div><div class="l">Likely to FAIL</div></div>
    <div class="stat work"><div class="n">{s['n_likely_to_work']}</div><div class="l">Likely to WORK</div></div>
    <div class="stat nc"><div class="n">{s['n_no_call']}</div><div class="l">NO-CALL</div></div>
    <div class="stat"><div class="n">{gf.get('n_amr_elements','?')}</div><div class="l">AMR elements</div></div>
  </div>
  <div class="card"><h2>Clinician summary</h2>{rec_lines}{summ}</div>

  <div class="grid2">
    <div class="card"><h2>Per-antibiotic prediction &amp; model evidence</h2>{cards}</div>
    <div>
      {_patient_panel(r)}
      {_literature_panel(r)}
      <div class="card"><h2>Confidence &amp; no-call</h2>
        <p class="muted">Confidence is calibrated on a held-out split (Brier score + reliability
        curve reported in the benchmark, not shown here). A <b>no-call</b> is returned when evidence
        is weak, models conflict, or the genome is unlike the training data.</p></div>
    </div>
  </div>

  <div class="card"><h2>Genome features (Module 1 · AMRFinderPlus)</h2>
    <p class="mono"><b>Point mutations:</b> {_esc(muts)}</p>
    <p class="mono"><b>Acquired genes:</b> {_esc(genes)}</p></div>
  <div class="card"><h2>Coverage &amp; limitations</h2>
    <p><b style="color:#1e7e46">✔ Covered:</b> {_esc(', '.join(cov.get('species_covered', [])))} · {s['n_drugs']} antibiotics</p>
    <p><b style="color:#c0392b">✘ Not covered:</b> {_esc(', '.join(cov.get('not_covered', [])))}</p>
    <p class="muted">Evidence (i)=known gene/DNA change (mechanistic) · (ii)=statistical association
    only (a feature-importance/SHAP value is not proof of biological cause) · (iii)=no known
    resistance signal (gated on target presence).</p></div>
</div>
<footer>Genome Firewall · defensive biosecurity prototype — predicts/explains existing resistance
only, never designs organisms. Not a medical device. Confirm every result with standard laboratory testing.</footer>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json")
    ap.add_argument("-o", "--output", default=None)
    args = ap.parse_args()
    r = json.load(open(args.report_json))
    out = args.output or str(Path(args.report_json).with_suffix(".html"))
    Path(out).write_text(render_html(r))
    print("wrote", out)


if __name__ == "__main__":
    main()
