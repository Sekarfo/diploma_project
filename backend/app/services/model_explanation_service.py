from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend.app.config import Settings, get_settings
from backend.app.services.explanation_service import ExplanationService


class ModelExplanationService:
    def __init__(self, settings: Settings | None = None, explanation_service: ExplanationService | None = None) -> None:
        self.settings = settings or get_settings()
        self.explanation_service = explanation_service or ExplanationService()

    @property
    def _metrics_dir(self) -> Path:
        return self.settings.root_dir / "models" / "metrics"

    @property
    def _shap_summary_path(self) -> Path:
        return self._metrics_dir / "shap_global_summary.csv"

    @property
    def _training_summary_path(self) -> Path:
        return self._metrics_dir / "summary.json"

    def get_global_explanation(self) -> dict:
        if not self._shap_summary_path.exists():
            raise FileNotFoundError(
                "Global SHAP summary not found. Run training script first: scripts/Train_ranker.py"
            )

        shap_df = pd.read_csv(self._shap_summary_path).copy()
        if "feature" not in shap_df.columns:
            raise ValueError(f"Invalid SHAP summary file (missing feature column): {self._shap_summary_path}")

        if "mean_abs_shap" not in shap_df.columns:
            shap_df["mean_abs_shap"] = 0.0
        if "mean_shap" not in shap_df.columns:
            shap_df["mean_shap"] = 0.0
        shap_df["mean_abs_shap"] = pd.to_numeric(shap_df["mean_abs_shap"], errors="coerce").fillna(0.0)
        shap_df["mean_shap"] = pd.to_numeric(shap_df["mean_shap"], errors="coerce").fillna(0.0)
        shap_df = shap_df.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

        validation_rows = 0
        validation_jobs = 0
        if self._training_summary_path.exists():
            try:
                summary = json.loads(self._training_summary_path.read_text(encoding="utf-8"))
                validation_rows = int(summary.get("validation_rows", 0))
                validation_jobs = int(summary.get("validation_jobs", 0))
            except Exception:
                validation_rows = 0
                validation_jobs = 0

        glossary = self.explanation_service.feature_glossary()
        glossary_by_feature = {item["feature"]: item for item in glossary}

        top_features: list[dict] = []
        for _, row in shap_df.iterrows():
            feature = str(row.get("feature", "")).strip()
            if not feature:
                continue
            meta = glossary_by_feature.get(feature, {})
            top_features.append(
                {
                    "feature": feature,
                    "label": str(meta.get("label", feature)),
                    "description": str(meta.get("description", "")),
                    "used_in_model": bool(meta.get("used_in_model", True)),
                    "mean_abs_shap": float(row["mean_abs_shap"]),
                    "mean_shap": float(row["mean_shap"]),
                }
            )

        return {
            "source": str(self._shap_summary_path),
            "validation_rows": validation_rows,
            "validation_jobs": validation_jobs,
            "top_features": top_features,
            "feature_glossary": glossary,
        }


@lru_cache(maxsize=1)
def get_model_explanation_service() -> ModelExplanationService:
    return ModelExplanationService()
