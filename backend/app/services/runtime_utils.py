from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LIST_ITEM_PATTERN = re.compile(r"'([^']*)'|\"([^\"]*)\"")


def parse_list_col(value: Any) -> list[str]:
    def normalize_items(items: list[Any]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in items:
            token = str(item).strip().lower().strip(" '\"")
            if not token:
                continue
            if token not in seen:
                out.append(token)
                seen.add(token)
        return out

    if value is None:
        return []

    if isinstance(value, np.ndarray):
        return normalize_items(value.tolist())

    if isinstance(value, (list, tuple, set)):
        return normalize_items(list(value))

    if isinstance(value, str):
        text = value.strip()
        if text == "" or text.lower() == "nan":
            return []

        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, np.ndarray):
                return normalize_items(parsed.tolist())
            if isinstance(parsed, (list, tuple, set)):
                return normalize_items(list(parsed))
            if isinstance(parsed, str):
                return normalize_items(re.split(r"[,\|;]", parsed))
            return normalize_items([parsed])
        except Exception:
            pass

        if text.startswith("[") and text.endswith("]"):
            inner = text[1:-1].strip()
            if not inner:
                return []

            quoted = [m.group(1) or m.group(2) for m in LIST_ITEM_PATTERN.finditer(inner)]
            quoted = [item.strip() for item in quoted if item and item.strip()]
            if quoted:
                return normalize_items(quoted)

            if "," in inner:
                return normalize_items(re.split(r"[,\|;]", inner))

            return normalize_items(inner.split())

        if "," in text or "|" in text or ";" in text:
            return normalize_items(re.split(r"[,\|;]", text))

        return normalize_items([text])

    try:
        if pd.isna(value):
            return []
    except Exception:
        pass

    text_value = str(value).strip()
    return normalize_items([text_value]) if text_value else []


def to_float(value: Any, default: float = 0.0) -> float:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return float(default)
    return float(numeric)


def token_set(text: str) -> set[str]:
    return set(str(text).lower().replace("/", " ").replace("-", " ").split())


def title_overlap_ratio(job_title: str, resume_titles: list[str]) -> float:
    job_tokens = token_set(job_title)
    resume_tokens = token_set(" ".join(resume_titles))
    if not job_tokens:
        return 0.0
    return float(len(job_tokens & resume_tokens) / len(job_tokens))


def load_dataframe(
    parquet_candidates: tuple[Path, ...],
    csv_candidates: tuple[Path, ...],
    label: str,
) -> tuple[pd.DataFrame, Path]:
    read_errors: list[str] = []

    for path in parquet_candidates:
        if not path.exists():
            continue
        try:
            return pd.read_parquet(path), path
        except Exception as exc:
            read_errors.append(f"Parquet read failed for {path}: {exc}")

    for path in csv_candidates:
        if not path.exists():
            continue
        try:
            return pd.read_csv(path), path
        except Exception as exc:
            read_errors.append(f"CSV read failed for {path}: {exc}")

    searched = "\n- ".join(str(p) for p in ((*parquet_candidates, *csv_candidates)))
    details = ("\nRead errors:\n- " + "\n- ".join(read_errors)) if read_errors else ""
    raise FileNotFoundError(f"Could not load {label}. Checked:\n- {searched}{details}")


def find_first_existing(candidates: tuple[Path, ...], label: str) -> Path:
    for path in candidates:
        if path.exists():
            return path
    searched = "\n- ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"Could not find {label}. Checked:\n- {searched}")


def normalize_jobs_df(df: pd.DataFrame) -> pd.DataFrame:
    if "job_id" not in df.columns:
        raise ValueError("jobs dataset is missing required column: job_id")

    if "job_title" not in df.columns:
        df["job_title"] = ""
    if "job_description" not in df.columns:
        df["job_description"] = ""
    if "job_skills_norm" not in df.columns:
        df["job_skills_norm"] = [[] for _ in range(len(df))]
    if "job_years_required" not in df.columns:
        df["job_years_required"] = 0.0

    df["job_id"] = df["job_id"].astype(str)
    df["job_title"] = df["job_title"].fillna("").astype(str)
    df["job_description"] = df["job_description"].fillna("").astype(str)
    df["job_skills_norm"] = df["job_skills_norm"].apply(parse_list_col)
    df["job_years_required"] = pd.to_numeric(df["job_years_required"], errors="coerce").fillna(0.0)
    return df


def normalize_resumes_df(df: pd.DataFrame) -> pd.DataFrame:
    if "resume_id" not in df.columns:
        raise ValueError("resumes dataset is missing required column: resume_id")

    if "resume_text" not in df.columns:
        df["resume_text"] = ""
    if "resume_skills_norm" not in df.columns:
        df["resume_skills_norm"] = [[] for _ in range(len(df))]
    if "resume_titles_norm" not in df.columns:
        df["resume_titles_norm"] = [[] for _ in range(len(df))]
    if "resume_years_experience" not in df.columns:
        df["resume_years_experience"] = 0.0

    df["resume_id"] = df["resume_id"].astype(str)
    df["resume_text"] = df["resume_text"].fillna("").astype(str)
    df["resume_skills_norm"] = df["resume_skills_norm"].apply(parse_list_col)
    df["resume_titles_norm"] = df["resume_titles_norm"].apply(parse_list_col)
    df["resume_years_experience"] = pd.to_numeric(df["resume_years_experience"], errors="coerce").fillna(0.0)
    return df


def build_index_map(df: pd.DataFrame, id_col: str, label: str) -> dict[str, int]:
    duplicated = df[id_col].duplicated(keep=False)
    if duplicated.any():
        duplicate_ids = sorted(df.loc[duplicated, id_col].unique().tolist())
        preview = ", ".join(duplicate_ids[:10])
        raise ValueError(f"Found duplicate {label} ids in {id_col}: {preview}")
    return {str(identifier): idx for idx, identifier in enumerate(df[id_col].tolist())}
