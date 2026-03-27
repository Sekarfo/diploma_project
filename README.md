# Job-Resume Shortlisting MVP

This project keeps a strict 2-stage pipeline:

1. Stage 1 retrieval: Sentence-BERT embeddings + Elasticsearch kNN.
2. Stage 2 ranking: interpretable feature rebuild + trained `XGBRanker`.


`data/raw/resume_data.csv` is a resume-job paired table.  
The same resume can appear in many rows with different paired jobs.

So preprocessing intentionally builds:

- one canonical `resumes_clean` table (unique resumes),
- one canonical `jobs_clean` table,
- one `observed_pairs` table from raw `matched_score`.

This prevents data leakage into retrieval while preserving supervision for training.

## Clean Data Pipeline

Run from repository root:

```powershell
python scripts/build_resume_job_dataset.py

#Build Sentence-BERT embeddings for jobs/resumes
python scripts/build_embedding.py

# Build auto-labeled pair dataset for ranker training
python scripts/build_ml_training_from_weak_labels.py

# Train ranker
python scripts/Train_ranker.py

# Rebuild Elasticsearch resume index from latest embeddings
python scripts/index_resumes_elasticsearch.py --recreate-index
```

Main outputs:

- `data/processed/dataset_outputs/jobs_clean.csv`
- `data/processed/dataset_outputs/resumes_clean.csv`
- `data/processed/dataset_outputs/csv/observed_pairs.csv`
- `data/processed/dataset_outputs/csv/candidate_pairs_auto.csv`
- `data/processed/dataset_outputs/csv/ml_training_template.csv` (always)
- `data/processed/dataset_outputs/parquet/ml_training_template.parquet` (when `pyarrow` is available)
- `models/xgb_ranker.joblib`
- `models/ranker_features.joblib`

## Runtime Flow

`job_id` -> load job + embedding -> Elasticsearch top-K retrieval -> rebuild ranking features -> `XGBRanker` score -> final shortlist JSON.

The API only serves inference. It does not retrain, re-embed, or re-index during requests.

## Main Endpoints

- `GET /health`
- `GET /stats`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /auth/signup`
- `POST /auth/signin`
- `GET /auth/me`
- `POST /auth/signout`
- `POST /shortlist`
- `POST /shortlist/vacancy`
- `GET /cabinet/history`
- `GET /cabinet/history/{run_id}`

`/shortlist` and `/shortlist/vacancy` now require Bearer auth and are saved to HR cabinet history.

## Environment and Dependencies

1. Fill `.env` in repo root (`DATABASE_URL`, `AUTH_PASSWORD_PEPPER`, Elasticsearch settings).
2. Install backend dependencies:

```powershell
pip install -r backend/requirements.txt
```

## Run API

```powershell
python backend/run_api.py
```

API URL: `http://127.0.0.1:8000`  
Swagger docs: `http://127.0.0.1:8000/docs`  
HR UI: `http://127.0.0.1:8000/ui`

## Runtime CLI

```powershell
python scripts/rerank_candidates_elasticsearch.py --job-id job_ext_00003 --top-k 20 --num-candidates 100
```

Default outputs:

- `data/processed/final_shortlist_<job_id>.csv`
- `data/processed/final_shortlist_<job_id>.json`
