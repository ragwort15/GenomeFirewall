# 🧬🛡️ Genome Firewall

Genome-to-antibiotic-response decision support for ***Klebsiella pneumoniae*** —
Hack-Nation Challenge 06. Takes a quality-checked assembly **FASTA** and returns,
per antibiotic, a **likely-to-work / likely-to-fail / no-call** verdict with a
**calibrated confidence**, an **honest evidence category**, and the supporting
genes/DNA changes — with a doctor-facing report and literature citations.

**Strictly defensive.** Predicts and explains *existing* resistance only. Never
designs, modifies, or optimizes an organism. Every result must be confirmed by
standard laboratory testing.

## Quick start — run the demo locally

The clinician-facing demo (`app.py`) is a Streamlit app that walks through
sign-in → patient details → FASTA upload → antibiotic-response report. It runs
against a mock results file, so no annotation tools or GPUs are required.

1. **Clone the repo**
   ```bash
   git clone https://github.com/ragwort15/GenomeFirewall.git
   cd GenomeFirewall
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add your OpenAI API key** (only needed for the LLM/literature layer;
   the demo runs without it)
   ```bash
   cp .env.example .env 2>/dev/null || true
   echo 'OPENAI_API_KEY=sk-...your-key...' > .env
   ```

5. **Launch the app**
   ```bash
   streamlit run app.py
   ```
   Streamlit prints a local URL (usually http://localhost:8501). Open it.

6. **Sign in** with a demo clinician account:
   | Username    | Password       |
   |-------------|----------------|
   | `demo`      | `demo`         |
   | `dr.smith`  | `genome123`    |
   | `dr.patel`  | `firewall456`  |

7. **Enter patient details** (name, age/sex, care setting, prior antibiotics,
   allergies, eGFR) and click **Continue to genome upload →**.

8. **Upload a bacterial FASTA** (`.fna` / `.fa` / `.fasta`). A sample assembly
   ships with the repo:
   ```
   data/smoke/GCF_000240185.1_ASM24018v2.fna
   ```

9. **Click *Analyze genome →*** to view the per-antibiotic report with
   calibrated confidences, evidence categories, patient context, and the
   mandatory "confirm with standard lab testing" banner.

Use **← Back** at any step to revise previous inputs — all entered data is
preserved in session state.

**Project presentation:** open `docs/pitch.html` in a browser for the
one-page overview (problem → solution → safety layer → stack → architecture →
what's new → hard parts → team).

---

## Pipeline
```
FASTA ─► Module 1  Genome Reader   (AMRFinderPlus → genes/mutations + target gate)
      ─► Module 2  Predictor       (registry runs all models → aggregate → verdict)
      ─► Module 3  Decision Report (JSON → Streamlit demo + LLM/paper-qa narrative)
```

## Models (ensemble)
| Model | Type | Evidence | Env |
|---|---|---|---|
| AMRFinderPlus | rule-based | (i) known gene/mutation | `genomefirewall` |
| Kleborate | rule-based | (i) | `genomefirewall` |
| WGS_to_AMR (pre-trained) | ML | (ii) statistical | `AMR_prediction` |
| PhenotypeSeeker | ML (k-mer LR) | (ii) | `phenotypeseeker` |
| Kover | ML (interpretable rules) | (ii) | `kover` |
| AMR-GNN | ML (GNN) | (ii) | `amr_gnn` |

Rule-based + ML calls are reconciled in `predictor/aggregate.py` (target gate,
no-call on weak/conflicting/OOD evidence).

## Setup
```bash
# one env for everything we build (annotation + ML + agent + paper-qa + Streamlit)
sbatch setup/create_env.sbatch            # creates `genomefirewall` + AMRFinderPlus DB
# external published models (own envs; adapters shell out)
sbatch setup/setup_external_models.sbatch # clones repos, builds AMR_prediction, etc.
```

## Run (deterministic core)
```bash
conda activate genomefirewall
bash data/download_public_smoke.sh        # K. pneumoniae HS11286 (KPC-2 producer)
python run_pipeline.py -i data/smoke/GCF_000240185.1_ASM24018v2.fna \
    --sample-id KP-HS11286 -o report.json
```

## Demo
```bash
conda activate genomefirewall
streamlit run app/streamlit_app.py        # upload FASTA or load report.json
```
Static layout preview (no deps): open `app/mock_report.html`.

## LLM + literature layer (optional)
Set `OPENAI_API_KEY`; `agent/orchestrator.py` adds a paper-qa literature block
(reuses `Tools/AGeneTic`) and an LLM clinician summary. The LLM never changes
verdicts/confidences — it only explains the deterministic report.

## Evaluation (organizer dataset)
`eval/` — per-drug balanced accuracy, recall(R)/recall(S), F1, AUROC, PR-AUC;
Brier + reliability plot; no-call rate; generalization by genetic group
(`grouped_split.py`, Mash/sourmash homology clustering).

## Layout
```
genome_reader/  Module 1   predictor/  Module 2 (adapters/, registry, aggregate, calibrate)
agent/          Module 3   app/        Streamlit + mock_report.html
eval/           metrics    setup/      env + model build jobs      external_models/  cloned repos
```
