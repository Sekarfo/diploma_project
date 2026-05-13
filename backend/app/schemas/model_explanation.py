from __future__ import annotations

from pydantic import BaseModel


class GlobalShapFeature(BaseModel):
    feature: str
    label: str
    description: str
    used_in_model: bool
    mean_abs_shap: float
    mean_shap: float


class FeatureGlossaryItem(BaseModel):
    feature: str
    label: str
    description: str
    used_in_model: bool


class GlobalModelExplanationResponse(BaseModel):
    source: str
    validation_rows: int
    validation_jobs: int
    top_features: list[GlobalShapFeature]
    feature_glossary: list[FeatureGlossaryItem]
