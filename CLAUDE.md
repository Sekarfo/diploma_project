# Project: Job-Resume Matching MVP

AI-powered talent pipeline tool that matches resumes to job descriptions using a trained XGBoost ranker.

## Running the project

### Backend (FastAPI) — Terminal 1
```bash
# From repo root
.venv/Scripts/activate         # activate venv (Windows PowerShell: .venv\Scripts\Activate.ps1)
python backend/run_api.py      # http://127.0.0.1:8000
```
- Swagger UI: http://127.0.0.1:8000/docs
- Hot-reload is enabled via uvicorn `reload=True`

### Frontend (Vite + React) — Terminal 2
```bash
cd frontend
npm run dev                    # http://localhost:5173
```

## Architecture

### Backend (`backend/`)
- **Framework**: FastAPI + uvicorn
- **Model**: XGBoost ranker loaded from `models/ranker_model.json`
- **Entry point**: `backend/run_api.py`
- **App**: `backend/app/main.py`
- **Routes**: `backend/app/api/routes.py`
  - `GET  /health`
  - `POST /rank-candidates` — rank with precomputed features
  - `POST /match-job` — full flow: load candidates -> build features -> rank
- **Services**: `backend/app/services/`
  - `ranking_service.py` — XGBoost inference
  - `feature_builder_service.py` — feature engineering
  - `job_matching_service.py` — orchestrates full match-job flow
- **Data**: `backend/data/candidates.json` — local demo candidates
- **Schemas**: `backend/app/schemas/` — Pydantic request/response models
- **Config**: `backend/app/config/` — constants, paths

### Frontend (`frontend/`)
- **Stack**: React 18, TypeScript, Vite, React Router v6, Zustand, TanStack Query
- **Port**: 5173
- **Pages**: Dashboard, Vacancies, VacancyCreate, VacancyDetail, Processing, Candidates, CandidateProfile, Shortlists, FeedbackTraining, Analytics, Integrations, Settings
- **Components**: `frontend/src/components/` — layout (Sidebar, TopBar, AppLayout), common (ScoreBadge, ExplanationPanel, StatusIndicator, ProgressTracker), candidates, vacancies

## Key file locations

| Purpose | Path |
|---|---|
| Backend entry | `backend/run_api.py` |
| API routes | `backend/app/api/routes.py` |
| Ranking logic | `backend/app/services/ranking_service.py` |
| Feature building | `backend/app/services/feature_builder_service.py` |
| Candidate data | `backend/data/candidates.json` |
| Trained model | `models/ranker_model.json` |
| Model metadata | `models/ranker_metadata.json` |
| Frontend app | `frontend/src/App.tsx` |
| Vite config | `frontend/vite.config.ts` |
| Example requests | `backend/examples/` |

## Data pipeline (already complete)
- Raw data: `data/raw/`
- Parsed: `data/parsed/jobs.jsonl`, `data/parsed/resumes.jsonl`
- Train/val/test splits: `data/splits/`
- Training script: `data/train_ranker.py`
- Model metrics: `models/metrics/`

## Dependencies
- **Python**: fastapi, uvicorn, pandas, xgboost (installed in `.venv`)
- **Node**: see `frontend/package.json` (`node_modules` already present)

## Current branch
- `feature/hr-shortlist-ui` — adding HR shortlist UI flow
- Main branch: `main`
