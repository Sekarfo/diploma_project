from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from backend.app.config import EXPECTED_RANKER_FEATURES, Settings, get_settings
from backend.app.services.errors import ArtifactLoadError
from backend.app.services.runtime_utils import (
    build_index_map,
    find_first_existing,
    load_dataframe,
    normalize_jobs_df,
    normalize_resumes_df,
)


@dataclass
class RuntimeArtifacts:
    jobs_df: pd.DataFrame
    resumes_df: pd.DataFrame
    job_embeddings: np.ndarray
    resume_embeddings: np.ndarray
    model: Any
    feature_columns: list[str]
    job_index_by_id: dict[str, int]
    resume_index_by_id: dict[str, int]
    paths: dict[str, Path]


class ArtifactService:
    """Loads and caches all runtime artifacts needed for retrieval+rereanking."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._artifacts: RuntimeArtifacts | None = None

    def get_artifacts(self) -> RuntimeArtifacts:
        if self._artifacts is None:
            self._artifacts = self._load_artifacts()
        return self._artifacts

    def _load_artifacts(self) -> RuntimeArtifacts:
        try:
            jobs_raw_df, jobs_path = load_dataframe(
                self.settings.jobs_parquet_candidates,
                self.settings.jobs_csv_candidates,
                "jobs dataset",
            )
            resumes_raw_df, resumes_path = load_dataframe(
                self.settings.resumes_parquet_candidates,
                self.settings.resumes_csv_candidates,
                "resumes dataset",
            )

            job_embeddings_path = find_first_existing(
                self.settings.job_embeddings_candidates,
                "job embeddings",
            )
            resume_embeddings_path = find_first_existing(
                self.settings.resume_embeddings_candidates,
                "resume embeddings",
            )
            model_path = find_first_existing(
                self.settings.ranker_model_candidates,
                "ranker model",
            )
            features_path = find_first_existing(
                self.settings.ranker_features_candidates,
                "ranker feature list",
            )

            jobs_df = normalize_jobs_df(jobs_raw_df.copy())
            resumes_df = normalize_resumes_df(resumes_raw_df.copy())

            job_embeddings = np.load(job_embeddings_path)
            resume_embeddings = np.load(resume_embeddings_path)

            if len(jobs_df) != len(job_embeddings):
                raise ValueError(
                    "jobs row count does not match job_embeddings rows: "
                    f"jobs={len(jobs_df)}, embeddings={len(job_embeddings)}"
                )
            if len(resumes_df) != len(resume_embeddings):
                raise ValueError(
                    "resumes row count does not match resume_embeddings rows: "
                    f"resumes={len(resumes_df)}, embeddings={len(resume_embeddings)}"
                )

            model = joblib.load(model_path)
            feature_columns = list(joblib.load(features_path))

            if feature_columns != EXPECTED_RANKER_FEATURES:
                raise ValueError(
                    "Loaded ranker feature list does not match expected runtime schema.\n"
                    f"Loaded:   {feature_columns}\n"
                    f"Expected: {EXPECTED_RANKER_FEATURES}"
                )

            return RuntimeArtifacts(
                jobs_df=jobs_df,
                resumes_df=resumes_df,
                job_embeddings=job_embeddings,
                resume_embeddings=resume_embeddings,
                model=model,
                feature_columns=feature_columns,
                job_index_by_id=build_index_map(jobs_df, "job_id", "job"),
                resume_index_by_id=build_index_map(resumes_df, "resume_id", "resume"),
                paths={
                    "jobs": jobs_path,
                    "resumes": resumes_path,
                    "job_embeddings": job_embeddings_path,
                    "resume_embeddings": resume_embeddings_path,
                    "model": model_path,
                    "features": features_path,
                },
            )
        except Exception as exc:
            raise ArtifactLoadError(f"Failed to load runtime artifacts: {exc}") from exc
