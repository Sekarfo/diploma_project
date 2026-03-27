from __future__ import annotations

from typing import Any

import pandas as pd


FEATURE_META: dict[str, dict[str, Any]] = {
    "embedding_cosine": {
        "label": "Semantic Similarity (Cosine)",
        "description": "Cosine similarity between job and resume embeddings. Higher means semantically closer text.",
        "used_in_model": True,
    },
    "embedding_cosine_norm": {
        "label": "Semantic Similarity (Normalized)",
        "description": "Cosine score normalized to [0, 1] for stable tree split behavior.",
        "used_in_model": True,
    },
    "skill_overlap_count": {
        "label": "Skill Overlap Count",
        "description": "Number of required job skills found in resume skills.",
        "used_in_model": True,
    },
    "skill_overlap_ratio": {
        "label": "Skill Overlap Ratio",
        "description": "Share of required skills covered by the candidate.",
        "used_in_model": True,
    },
    "title_overlap_ratio": {
        "label": "Title Overlap Ratio",
        "description": "Token overlap between vacancy title and candidate historical titles.",
        "used_in_model": True,
    },
    "resume_years_experience": {
        "label": "Resume Experience (Years)",
        "description": "Total years of experience extracted from resume.",
        "used_in_model": True,
    },
    "job_years_required": {
        "label": "Job Required Experience (Years)",
        "description": "Years of experience required by vacancy.",
        "used_in_model": True,
    },
    "years_gap": {
        "label": "Experience Gap (Resume - Job)",
        "description": "Difference between candidate years and job required years.",
        "used_in_model": True,
    },
    "experience_match_flag": {
        "label": "Experience Match Flag",
        "description": "Binary feature: 1 if candidate meets required years, else 0.",
        "used_in_model": True,
    },
    "retrieval_rank": {
        "label": "Retrieval Rank",
        "description": "Stage-1 retrieval position before reranking. Lower is better.",
        "used_in_model": True,
    },
    "missing_skills_count": {
        "label": "Missing Skills Count",
        "description": "How many required skills are missing in resume. Used for interpretation panel only.",
        "used_in_model": False,
    },
    "education_match": {
        "label": "Education Match",
        "description": "Education requirement match flag. Not currently in training features.",
        "used_in_model": False,
    },
    "location_constraint_match": {
        "label": "Location or Constraint Match",
        "description": "Location / work-mode / constraint compatibility flag. Not currently in training features.",
        "used_in_model": False,
    },
}

MODEL_FEATURE_ORDER = [
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

RAW_FEATURE_ORDER = MODEL_FEATURE_ORDER + [
    "missing_skills_count",
]


class ExplanationService:
    """Builds candidate-level and global feature explanations for shortlist output."""

    @staticmethod
    def feature_glossary() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for feature, meta in FEATURE_META.items():
            rows.append(
                {
                    "feature": feature,
                    "label": str(meta["label"]),
                    "description": str(meta["description"]),
                    "used_in_model": bool(meta["used_in_model"]),
                }
            )
        rows.sort(key=lambda item: (not item["used_in_model"], item["feature"]))
        return rows

    def build_explanation(self, row: pd.Series) -> dict:
        matched_skills = row.get("matched_skills", []) or []
        missing_skills = row.get("missing_skills", []) or []
        experience_summary = str(row.get("experience_summary", ""))
        title_summary = str(row.get("title_summary", ""))

        top_positive_factors = self._top_factors(row, positive=True, top_n=3)
        top_negative_factors = self._top_factors(row, positive=False, top_n=3)
        raw_feature_values = self._raw_feature_values(row, missing_skills=missing_skills)
        baseline_score = self._to_float(row.get("shap_base_value"))

        return {
            "matched_skills": list(matched_skills),
            "missing_skills": list(missing_skills),
            "experience_summary": experience_summary,
            "title_summary": title_summary,
            "baseline_score": baseline_score,
            "top_positive_factors": top_positive_factors,
            "top_negative_factors": top_negative_factors,
            "raw_feature_values": raw_feature_values,
        }

    def _top_factors(self, row: pd.Series, *, positive: bool, top_n: int) -> list[dict[str, Any]]:
        factors: list[dict[str, Any]] = []
        for feature in MODEL_FEATURE_ORDER:
            shap_value = self._to_float(row.get(f"shap_{feature}"))
            if shap_value is None:
                continue
            if positive and shap_value <= 0:
                continue
            if (not positive) and shap_value >= 0:
                continue

            meta = FEATURE_META.get(feature, {})
            factors.append(
                {
                    "feature": feature,
                    "label": str(meta.get("label", feature)),
                    "impact": float(shap_value),
                    "raw_value": self._format_feature_value(feature, row),
                    "description": str(meta.get("description", "")),
                }
            )

        if positive:
            factors.sort(key=lambda item: float(item["impact"]), reverse=True)
        else:
            factors.sort(key=lambda item: float(item["impact"]))
        return factors[:top_n]

    def _raw_feature_values(self, row: pd.Series, *, missing_skills: list[str]) -> dict[str, str]:
        raw: dict[str, str] = {}
        for feature in RAW_FEATURE_ORDER:
            meta = FEATURE_META.get(feature, {})
            raw[str(meta.get("label", feature))] = self._format_feature_value(feature, row)

        raw["Missing Skills"] = ", ".join(missing_skills) if missing_skills else "none"
        raw["Missing Skills Count"] = str(len(missing_skills))
        return raw

    @staticmethod
    def _to_float(value: Any) -> float | None:
        numeric = pd.to_numeric(value, errors="coerce")
        if pd.isna(numeric):
            return None
        return float(numeric)

    def _format_feature_value(self, feature: str, row: pd.Series) -> str:
        if feature == "missing_skills_count":
            missing_skills = row.get("missing_skills", []) or []
            return str(len(missing_skills))

        value = row.get(feature)
        numeric = pd.to_numeric(value, errors="coerce")
        if not pd.isna(numeric):
            if feature in {"retrieval_rank", "skill_overlap_count", "experience_match_flag"}:
                return str(int(round(float(numeric))))
            return f"{float(numeric):.4f}"
        if value is None:
            return "n/a"
        text = str(value).strip()
        return text if text else "n/a"
