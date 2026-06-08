# Job-Resume Shortlisting MVP

Three-stage candidate matching pipeline with an HR cabinet, fairness audit, recruiter feedback loop, and LLM candidate analysis.

1. **Stage 1 — retrieval**: dense embeddings (`BAAI/bge-large-en-v1.5`, 1024 dims) in Elasticsearch with hybrid scoring (kNN cosine + BM25 over text/skills/titles).
2. **Stage 2 — cross-encoder rerank**: `cross-encoder/ms-marco-MiniLM-L-12-v2` joins (job_text, resume_text) and outputs `ce_score ∈ [0, 1]`. The same model is used **offline** to generate training labels and **online** to populate one ML feature. At inference a **cascade** scores only the top-M most promising candidates with the CE; the tail gets a default score (`0.0`), tunable via env.
3. **Stage 3 — LightGBM combiner**: `LGBMRanker` (LambdaRank/NDCG, 30 features) consumes `ce_score_x_skill` plus 29 structured features (embedding similarity, skills overlap, title overlap, experience, retrieval rank, within-group z-scores). Outputs final ranking + SHAP contributions.

On top of the ranking core the backend adds: JWT-style session auth, a per-user **HR cabinet** (run history, custom vacancies), **recruiter feedback** capture, a **Kanban** hiring pipeline, a **fairness audit**, optional **LLM candidate analysis** (via OpenRouter), and PDF/DOCX **vacancy file parsing**.

## Repository Layout

```
src/
  ml/             # LightGBM training, feature engineering, evaluation, feedback retraining
  embeddings/     # BGE encoding + Elasticsearch index builder
backend/
  app/
    api/          # FastAPI routes
    config/       # Settings (env-driven)
    schemas/      # Pydantic request/response models
    services/     # auth, shortlist, ranking, cross-encoder, elasticsearch, db,
                  #   history, cabinet, fairness, kanban, feedback, AI analysis,
                  #   vacancy parser, runtime metrics, explanations
  requirements.txt
  run_api.py      # uvicorn entrypoint for local runs
frontend/         # Static HR UI (vanilla HTML/CSS/JS), served at /ui
docker/           # docker-compose, backend & frontend Dockerfiles, nginx config
data/
  Clear/                       # Raw cleaned datasets (jobs_clean.csv, resumes_clean.csv)
  pair_features_labeled.csv    # Labeled training pairs for the ranker
  embeddings/*.npy             # Output of src.embeddings.build (gitignored)
  generate_labels.py           # Cross-encoder relabeling script (offline)
  build_pairs.py               # Builds (job, resume) candidate pairs + features
  smart_merge.py               # Dataset merge/cleanup helpers
  clean_resume_duplicates.py   # Resume de-duplication helper
models/                        # Trained ranker artifacts + metrics (metadata/features tracked)
requirements-ml.txt            # Heavy ML deps (torch, sentence-transformers) for offline scripts
```

## Data

- `data/Clear/jobs_clean.csv` — 2 296 vacancies.
- `data/Clear/resumes_clean.csv` — 18 174 resumes (`person_id` → `resume_id`).
- `data/pair_features_labeled.csv` — **20 400 trainable (job, resume) pairs** (408 vacancies × 50 candidates). Labels are 5 absolute buckets of `ce_score`. Only vacancies that have at least one strong positive (label ≥ 3) **and** one negative (label ≤ 1) are retained — LambdaRank requires label variation within each group. Pre-filter pool = 114 800 pairs across all 2 296 vacancies; 1 888 vacancies were dropped as degenerate (see `data/generate_labels.py`).

The 408 trainable vacancies are split 284 train / 62 valid / 62 test (14 200 / 3 100 / 3 100 rows).

---

## Bootstrap (one-time, run locally)

These steps produce the artifacts that the Docker stack consumes. They need GPU/CPU compute and are NOT executed at runtime.

```powershell
# 1. Install the heavy ML toolkit (torch + sentence-transformers + lightgbm + sklearn).
python -m pip install -r requirements-ml.txt

# 2. Encode jobs and resumes with BGE-large -> data/embeddings/*.npy (~5 min GPU / 6 h CPU).
python -m src.embeddings.build

# 3. Generate cross-encoder labels in pair_features_labeled.csv (~2 min GPU).
#    Idempotent: pass --rescore to recompute from scratch.
python data/generate_labels.py

# 4. Train LightGBM LambdaRank ranker -> models/lgbm_ranker.joblib (Optuna HPO).
python -m src.ml.train
```

The tracked artifacts are `models/ranker_features.joblib` and `models/ranker_metadata.json` (metrics + tuned params); the trained `models/lgbm_ranker.joblib` is produced by step 4 and is gitignored.

## Run the full system (Docker)

The Docker stack runs **Elasticsearch + backend + frontend**. It does **not** bundle a Postgres
container — the backend connects to a **Postgres instance on the host** via
`host.docker.internal:5432`. Make sure Postgres is running on the host and the target database
exists before bringing the stack up (the backend auto-creates its schema on startup).

```powershell
# 1. Configure environment.
cp .env.example .env
# edit .env:
#   - AUTH_PASSWORD_PEPPER  (required; long random string)
#   - POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB  (host DB credentials; default DB: diploma)
#   - OPENROUTER_API_KEY    (optional; enables LLM candidate analysis)

docker compose -f docker/docker-compose.yml up -d --build

# 2. Index resumes + embeddings into the Elasticsearch container (one-time).
docker compose -f docker/docker-compose.yml exec backend `
    python -m src.embeddings.index_elasticsearch --recreate-index
```

Services:

| Service | URL | Notes |
| --- | --- | --- |
| Frontend (nginx) | http://localhost | Serves SPA at `/ui/` (root redirects there), reverse-proxies API to backend |
| Backend (FastAPI) | http://localhost:8000 | Swagger at `/docs` |
| Elasticsearch | http://localhost:9200 | single-node, security disabled, 2 GB heap |
| Postgres (host) | host.docker.internal:5432 | **Not** a compose service; runs on the host. Default DB `diploma`, schema auto-created on backend startup |

The backend image bundles the cross-encoder (`cross-encoder/ms-marco-MiniLM-L-12-v2`, ~500 MB) so the first `/shortlist` request doesn't stall on HF download. Models, embeddings and CSVs are mounted from host (`../models`, `../data`) read-only.

To rebuild after code changes:
```powershell
docker compose -f docker/docker-compose.yml build --no-cache backend frontend
docker compose -f docker/docker-compose.yml up -d
```

Stop:
```powershell
docker compose -f docker/docker-compose.yml down
# add -v to also drop the Elasticsearch volume
```

## Runtime Flow

```
job_id (or vacancy text)
   ↓
load job embedding from data/embeddings/job_embeddings.npy
   ↓
ES hybrid retrieve top-N (default 100; kNN + BM25 on text/skills/titles)
   ↓
build 29 structured features per candidate
   ↓
CrossEncoder scores top-M candidates (cascade); tail gets default 0.0
   ↓
ce_score → engineer_features() → ce_score_x_skill (dampened CE signal)
   ↓
LightGBM rank with 30 features → top-K shortlist + per-candidate SHAP
```

Defaults: `num_candidates = 100` (max 300), `top_k = 20` (max 30); CE cascade `top_m` and the
default tail score are env-tunable (`CROSS_ENCODER_CASCADE_*`).

## API Endpoints

**Health / stats**
- `GET /health`, `GET /stats`, `GET /stats/runtime`, `GET /stats/explanations/global`
- `GET /stats/fairness` (auth) — group-level selection-rate / score / feedback audit

**Auth**
- `POST /auth/signup`, `POST /auth/signin`, `GET /auth/me`, `POST /auth/signout`

**Jobs**
- `GET /jobs`, `GET /jobs/{job_id}`

**Shortlist (Bearer auth, recorded in HR cabinet)**
- `POST /shortlist`, `POST /shortlist/vacancy`
- `WS /ws/shortlist` — streaming shortlist with real-time progress events
- `POST /vacancies/parse` — upload a PDF/DOCX vacancy file → extracted title/description/years/skills

**Cabinet**
- `GET /cabinet/history`, `GET /cabinet/history/{run_id}`, `GET /cabinet/vacancies`

**Recruiter feedback**
- `POST /shortlist/{run_id}/feedback`, `GET /shortlist/{run_id}/feedback`, `DELETE /shortlist/{run_id}/feedback/{final_rank}`

**Kanban hiring pipeline**
- `GET /kanban`, `PATCH /kanban/{entry_id}/status`, `DELETE /kanban/{entry_id}`

**LLM candidate analysis (requires `OPENROUTER_API_KEY`)**
- `GET /shortlist/{run_id}/ai-analysis?mode=explain|compare` — SSE stream of AI assessment of the top candidates
- `GET /shortlist/{run_id}/ai-analyses` — stored analyses for a run, keyed by mode

## LLM candidate analysis

`GET /shortlist/{run_id}/ai-analysis` streams (Server-Sent Events) an LLM assessment of the top
candidates, generated via **OpenRouter** (default model `meta-llama/llama-3.1-8b-instruct`).
`mode=explain` produces an individual assessment per top candidate; `mode=compare` produces a
head-to-head comparison with a single hiring recommendation. Results are cached in Postgres and
replayed for free on repeat calls. Per-user rate limit: 5 requests / 3 minutes. The feature is
optional — without `OPENROUTER_API_KEY` the rest of the system runs unaffected.

## Feedback retraining

Recruiter decisions captured via the feedback endpoints can be folded back into the ranker:

```powershell
python -m src.ml.retrain_with_feedback --min-feedback 20 `
    --output models/lgbm_ranker_with_feedback.joblib
```

It joins `recruiter_feedback` with each candidate's `feature_snapshot` from Postgres, maps
decisions to the 5-bucket label scheme (reject→0, maybe→2, accept→3, interview→4), merges with the
original `pair_features_labeled.csv`, and warm-trains a new artifact. The new model is **not** swapped
into production automatically — verify metrics first.

## Feature Set (30 ML features)

| Group | Features |
|---|---|
| Base retrieval | `embedding_cosine`, `retrieval_rank`, `is_top5_retrieval`, `is_top10_retrieval`, `log_retrieval_rank`, `retrieval_rank_inv` |
| Embedding transforms | `embedding_cosine_norm`, `embedding_cosine_squared` |
| Skills | `skill_overlap_count`, `skill_overlap_ratio` |
| Title | `title_overlap_ratio` |
| Experience | `years_gap`, `experience_match_flag`, `resume_years_experience`, `job_years_required`, `abs_years_gap`, `years_gap_squared` |
| Interactions | `skill_overlap_x_emb`, `experience_x_skill`, `experience_x_emb`, `title_x_emb`, `skill_x_title` |
| Per-job z-scores | `embedding_cosine_zscore_in_job`, `skill_overlap_ratio_zscore_in_job`, `title_overlap_ratio_zscore_in_job` |
| Per-job ranks | `embedding_cosine_rank_in_job`, `skill_overlap_rank_in_job`, `title_overlap_rank_in_job`, `combined_rank_in_job` |
| **Distilled CE signal** | **`ce_score_x_skill`** — `ce_score × skill_overlap_ratio`; partial leak controlled at NDCG@10 solo ≈ 0.78 |

LambdaRank `label_gain = [0, 1, 2, 4, 8]` to match the 5-bucket labels.

## Methodology Note (for thesis)

Cross-encoder is used as a **teacher** in a knowledge-distillation setup: it labels (job, resume) pairs offline and reappears at inference only to populate one dampened feature (`ce_score_x_skill = ce_score × skill_overlap_ratio`). Multiplying by `skill_overlap_ratio` (which varies widely within a retrieved pool 0..1) scrambles the CE ordering enough to drop solo NDCG@10 from 1.0 (raw `ce_score`) to ~0.78 — turning a trivial label-reconstruction feature into a controlled hint. The LightGBM combiner is then forced to use the other 29 structured features to refine ranking, ending up in the 0.89–0.91 NDCG@10 zone with realistic interpretable SHAP contributions (valid 0.909, test 0.894 on the current 408-vacancy dataset).
