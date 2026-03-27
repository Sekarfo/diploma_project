from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

EXPECTED_RANKER_FEATURES = [
    "embedding_cosine",
    "embedding_cosine_norm",
    "skill_overlap_count",
    "skill_overlap_ratio",
    "title_overlap_ratio",
    "resume_years_experience",
    "job_years_required",
    "years_gap",
    "experience_match_flag",
    "retrieval_rank",
]

_TRUE_VALUES: Final[set[str]] = {"1", "true", "yes", "on"}


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    processed_dir: Path
    dataset_outputs_dir: Path

    jobs_parquet_candidates: tuple[Path, ...]
    jobs_csv_candidates: tuple[Path, ...]
    resumes_parquet_candidates: tuple[Path, ...]
    resumes_csv_candidates: tuple[Path, ...]
    job_embeddings_candidates: tuple[Path, ...]
    resume_embeddings_candidates: tuple[Path, ...]
    ranker_model_candidates: tuple[Path, ...]
    ranker_features_candidates: tuple[Path, ...]

    elasticsearch_url: str
    elasticsearch_username: str | None
    elasticsearch_password: str | None
    elasticsearch_index_name: str

    database_url: str
    db_schema_autocreate: bool
    auth_session_ttl_minutes: int
    auth_password_pepper: str

    default_top_k: int
    default_num_candidates: int
    max_top_k: int
    max_num_candidates: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    root_dir = Path(__file__).resolve().parents[3]
    _load_env_file(root_dir / ".env")
    processed_dir = root_dir / "data" / "processed"
    dataset_outputs_dir = processed_dir / "dataset_outputs"

    return Settings(
        root_dir=root_dir,
        processed_dir=processed_dir,
        dataset_outputs_dir=dataset_outputs_dir,
        jobs_parquet_candidates=(
            processed_dir / "jobs_clean.parquet",
            dataset_outputs_dir / "jobs_clean.parquet",
            dataset_outputs_dir / "parquet" / "jobs_clean.parquet",
        ),
        jobs_csv_candidates=(
            processed_dir / "jobs_clean.csv",
            dataset_outputs_dir / "jobs_clean.csv",
            dataset_outputs_dir / "csv" / "jobs_clean.csv",
        ),
        resumes_parquet_candidates=(
            processed_dir / "resumes_clean.parquet",
            dataset_outputs_dir / "resumes_clean.parquet",
            dataset_outputs_dir / "parquet" / "resumes_clean.parquet",
        ),
        resumes_csv_candidates=(
            processed_dir / "resumes_clean.csv",
            dataset_outputs_dir / "resumes_clean.csv",
            dataset_outputs_dir / "csv" / "resumes_clean.csv",
        ),
        job_embeddings_candidates=(
            processed_dir / "job_embeddings.npy",
            dataset_outputs_dir / "job_embeddings.npy",
            dataset_outputs_dir / "embeddings" / "job_embeddings.npy",
        ),
        resume_embeddings_candidates=(
            processed_dir / "resume_embeddings.npy",
            dataset_outputs_dir / "resume_embeddings.npy",
            dataset_outputs_dir / "embeddings" / "resume_embeddings.npy",
        ),
        ranker_model_candidates=(
            root_dir / "models" / "xgb_ranker.joblib",
        ),
        ranker_features_candidates=(
            root_dir / "models" / "ranker_features.joblib",
        ),
        elasticsearch_url=os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200"),
        elasticsearch_username=os.getenv("ELASTICSEARCH_USERNAME"),
        elasticsearch_password=os.getenv("ELASTICSEARCH_PASSWORD"),
        elasticsearch_index_name=os.getenv("ELASTICSEARCH_INDEX", "resumes_index"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:5432/hr_shortlist",
        ),
        db_schema_autocreate=os.getenv("DB_SCHEMA_AUTOCREATE", "true").strip().lower() in _TRUE_VALUES,
        auth_session_ttl_minutes=int(os.getenv("AUTH_SESSION_TTL_MINUTES", "10080")),
        auth_password_pepper=os.getenv("AUTH_PASSWORD_PEPPER", ""),
        default_top_k=20,
        default_num_candidates=100,
        max_top_k=200,
        max_num_candidates=5000,
    )
