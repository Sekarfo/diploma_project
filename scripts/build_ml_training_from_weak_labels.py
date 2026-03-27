from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATASET_OUTPUTS_DIR = PROCESSED_DIR / "dataset_outputs"
CSV_DIR = DATASET_OUTPUTS_DIR / "csv"
PARQUET_DIR = DATASET_OUTPUTS_DIR / "parquet"
EMBEDDINGS_DIR = DATASET_OUTPUTS_DIR / "embeddings"

JOBS_PARQUET_CANDIDATES = (
    PROCESSED_DIR / "jobs_clean.parquet",
    DATASET_OUTPUTS_DIR / "jobs_clean.parquet",
    PARQUET_DIR / "jobs_clean.parquet",
)
JOBS_CSV_CANDIDATES = (
    PROCESSED_DIR / "jobs_clean.csv",
    DATASET_OUTPUTS_DIR / "jobs_clean.csv",
    CSV_DIR / "jobs_clean.csv",
)
RESUMES_PARQUET_CANDIDATES = (
    PROCESSED_DIR / "resumes_clean.parquet",
    DATASET_OUTPUTS_DIR / "resumes_clean.parquet",
    PARQUET_DIR / "resumes_clean.parquet",
)
RESUMES_CSV_CANDIDATES = (
    PROCESSED_DIR / "resumes_clean.csv",
    DATASET_OUTPUTS_DIR / "resumes_clean.csv",
    CSV_DIR / "resumes_clean.csv",
)
OBSERVED_PARQUET_CANDIDATES = (
    PARQUET_DIR / "observed_pairs.parquet",
    DATASET_OUTPUTS_DIR / "observed_pairs.parquet",
)
OBSERVED_CSV_CANDIDATES = (
    CSV_DIR / "observed_pairs.csv",
    DATASET_OUTPUTS_DIR / "observed_pairs.csv",
)
JOB_EMBEDDINGS_CANDIDATES = (
    PROCESSED_DIR / "job_embeddings.npy",
    DATASET_OUTPUTS_DIR / "job_embeddings.npy",
    EMBEDDINGS_DIR / "job_embeddings.npy",
)
RESUME_EMBEDDINGS_CANDIDATES = (
    PROCESSED_DIR / "resume_embeddings.npy",
    DATASET_OUTPUTS_DIR / "resume_embeddings.npy",
    EMBEDDINGS_DIR / "resume_embeddings.npy",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build auto-labeled ranking dataset from embeddings + observed pair scores."
    )
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--hard-negs", type=int, default=20)
    parser.add_argument("--random-negs", type=int, default=20)
    parser.add_argument("--hard-pool", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-candidates-per-job", type=int, default=8)
    return parser.parse_args()


def load_dataframe(
    parquet_candidates: tuple[Path, ...],
    csv_candidates: tuple[Path, ...],
    label: str,
) -> pd.DataFrame:
    read_errors: list[str] = []
    for path in parquet_candidates:
        if path.exists():
            try:
                return pd.read_parquet(path)
            except Exception as exc:
                read_errors.append(f"parquet read failed for {path}: {exc}")
    for path in csv_candidates:
        if path.exists():
            try:
                return pd.read_csv(path)
            except Exception as exc:
                read_errors.append(f"csv read failed for {path}: {exc}")
    searched = "\n- ".join(str(path) for path in (*parquet_candidates, *csv_candidates))
    details = ("\nRead errors:\n- " + "\n- ".join(read_errors)) if read_errors else ""
    raise FileNotFoundError(f"Could not load {label}. Checked:\n- {searched}{details}")


def load_optional_dataframe(
    parquet_candidates: tuple[Path, ...],
    csv_candidates: tuple[Path, ...],
) -> pd.DataFrame:
    read_errors: list[str] = []
    for path in parquet_candidates:
        if path.exists():
            try:
                return pd.read_parquet(path)
            except Exception as exc:
                read_errors.append(f"parquet read failed for {path}: {exc}")
    for path in csv_candidates:
        if path.exists():
            try:
                return pd.read_csv(path)
            except Exception as exc:
                read_errors.append(f"csv read failed for {path}: {exc}")
    if read_errors:
        print("[warn] Failed to read optional observed_pairs files:")
        for err in read_errors:
            print(f"[warn] {err}")
    return pd.DataFrame(columns=["job_id", "resume_id", "matched_score", "observed_pair_count", "source"])


def load_array(candidates: tuple[Path, ...], label: str) -> np.ndarray:
    for path in candidates:
        if path.exists():
            return np.load(path)
    searched = "\n- ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Could not load {label}. Checked:\n- {searched}")


def parse_list_col(value: object) -> list[str]:
    def normalize_items(items: list[object]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for raw in items:
            token = str(raw).strip().lower()
            token = token.strip(" '\"")
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
        if not text or text.lower() == "nan":
            return []
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, np.ndarray):
                return normalize_items(parsed.tolist())
            if isinstance(parsed, (list, tuple, set)):
                return normalize_items(list(parsed))
            if isinstance(parsed, str):
                parts = re.split(r"[,\|;]", parsed)
                return normalize_items(parts)
            return normalize_items([parsed])
        except Exception:
            if text.startswith("[") and text.endswith("]"):
                text = text[1:-1]
            parts = re.split(r"[,\|;]", text)
            return normalize_items(parts)
    return normalize_items([value])


def to_float(value: object, default: float = 0.0) -> float:
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


def normalize_jobs_df(df: pd.DataFrame) -> pd.DataFrame:
    required = ["job_id", "job_title", "job_description", "job_skills_norm", "job_years_required"]
    for column in required:
        if column not in df.columns:
            if column in {"job_skills_norm"}:
                df[column] = [[] for _ in range(len(df))]
            elif column in {"job_years_required"}:
                df[column] = 0.0
            else:
                df[column] = ""
    df["job_id"] = df["job_id"].astype(str)
    df["job_title"] = df["job_title"].fillna("").astype(str)
    df["job_description"] = df["job_description"].fillna("").astype(str)
    df["job_skills_norm"] = df["job_skills_norm"].apply(parse_list_col)
    df["job_years_required"] = pd.to_numeric(df["job_years_required"], errors="coerce").fillna(0.0)
    return df


def normalize_resumes_df(df: pd.DataFrame) -> pd.DataFrame:
    required = ["resume_id", "resume_text", "resume_skills_norm", "resume_titles_norm", "resume_years_experience"]
    for column in required:
        if column not in df.columns:
            if column in {"resume_skills_norm", "resume_titles_norm"}:
                df[column] = [[] for _ in range(len(df))]
            elif column in {"resume_years_experience"}:
                df[column] = 0.0
            else:
                df[column] = ""
    df["resume_id"] = df["resume_id"].astype(str)
    df["resume_text"] = df["resume_text"].fillna("").astype(str)
    df["resume_skills_norm"] = df["resume_skills_norm"].apply(parse_list_col)
    df["resume_titles_norm"] = df["resume_titles_norm"].apply(parse_list_col)
    df["resume_years_experience"] = pd.to_numeric(df["resume_years_experience"], errors="coerce").fillna(0.0)
    return df


def weak_score(
    *,
    embedding_cosine_norm: float,
    skill_overlap_ratio: float,
    title_overlap: float,
    experience_match_flag: int,
    observed_score: float | None,
) -> float:
    values = [
        (0.45, float(np.clip(embedding_cosine_norm, 0.0, 1.0))),
        (0.25, float(np.clip(skill_overlap_ratio, 0.0, 1.0))),
        (0.10, float(np.clip(title_overlap, 0.0, 1.0))),
        (0.10, float(np.clip(experience_match_flag, 0.0, 1.0))),
    ]
    if observed_score is not None and not np.isnan(observed_score):
        values.append((0.25, float(np.clip(observed_score, 0.0, 1.0))))
    total_weight = sum(weight for weight, _ in values)
    return float(sum(weight * value for weight, value in values) / total_weight)


def assign_label(
    *,
    weak_score_value: float,
    skill_overlap_count: int,
    embedding_cosine_norm: float,
    experience_match_flag: int,
    observed_score: float | None,
) -> int:
    if observed_score is not None and not np.isnan(observed_score):
        if observed_score >= 0.80:
            return 2
        if observed_score <= 0.25:
            return 0

    if skill_overlap_count == 0 and embedding_cosine_norm < 0.58:
        return 0
    if weak_score_value < 0.34:
        return 0
    if weak_score_value >= 0.76 and skill_overlap_count >= 1 and experience_match_flag >= 1:
        return 2
    return 1


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(args.seed)

    jobs_df = normalize_jobs_df(load_dataframe(JOBS_PARQUET_CANDIDATES, JOBS_CSV_CANDIDATES, "jobs dataset"))
    resumes_df = normalize_resumes_df(
        load_dataframe(RESUMES_PARQUET_CANDIDATES, RESUMES_CSV_CANDIDATES, "resumes dataset")
    )
    observed_df = load_optional_dataframe(OBSERVED_PARQUET_CANDIDATES, OBSERVED_CSV_CANDIDATES)

    job_embeddings = load_array(JOB_EMBEDDINGS_CANDIDATES, "job embeddings")
    resume_embeddings = load_array(RESUME_EMBEDDINGS_CANDIDATES, "resume embeddings")

    if len(jobs_df) != len(job_embeddings):
        raise ValueError(f"jobs rows mismatch embeddings: jobs={len(jobs_df)} embeddings={len(job_embeddings)}")
    if len(resumes_df) != len(resume_embeddings):
        raise ValueError(
            f"resumes rows mismatch embeddings: resumes={len(resumes_df)} embeddings={len(resume_embeddings)}"
        )

    score_matrix = np.asarray(job_embeddings @ resume_embeddings.T, dtype=np.float32)
    all_resume_idx = np.arange(len(resumes_df))

    job_index_by_id = {job_id: index for index, job_id in enumerate(jobs_df["job_id"].tolist())}
    resume_index_by_id = {resume_id: index for index, resume_id in enumerate(resumes_df["resume_id"].tolist())}

    observed_df = observed_df.copy()
    for column in ["job_id", "resume_id"]:
        if column not in observed_df.columns:
            observed_df[column] = ""
        observed_df[column] = observed_df[column].astype(str)
    if "matched_score" not in observed_df.columns:
        observed_df["matched_score"] = np.nan
    observed_df["matched_score"] = pd.to_numeric(observed_df["matched_score"], errors="coerce")

    observed_df = observed_df[
        observed_df["job_id"].isin(job_index_by_id.keys()) & observed_df["resume_id"].isin(resume_index_by_id.keys())
    ].copy()

    observed_map: dict[tuple[str, str], float] = {}
    observed_resumes_by_job: dict[str, set[int]] = {}
    for row in observed_df.itertuples(index=False):
        key = (str(row.job_id), str(row.resume_id))
        score = float(row.matched_score) if pd.notna(row.matched_score) else np.nan
        if key not in observed_map or (
            not np.isnan(score) and (np.isnan(observed_map[key]) or score > observed_map[key])
        ):
            observed_map[key] = score
        observed_resumes_by_job.setdefault(str(row.job_id), set()).add(resume_index_by_id[str(row.resume_id)])

    records: list[dict] = []
    for job_idx, job in jobs_df.iterrows():
        scores = score_matrix[job_idx]
        order = np.argsort(-scores)
        top_idx = order[: args.top_k]
        ranked_top = {int(index): rank + 1 for rank, index in enumerate(top_idx)}

        job_skills = {skill.lower() for skill in job["job_skills_norm"] if str(skill).strip()}
        hard_neg_candidates: list[int] = []
        for resume_idx in order[: args.hard_pool]:
            resume_skills = set(resumes_df.iloc[int(resume_idx)]["resume_skills_norm"])
            if len(job_skills & resume_skills) == 0:
                hard_neg_candidates.append(int(resume_idx))
            if len(hard_neg_candidates) >= args.hard_negs:
                break

        excluded = set(int(index) for index in top_idx) | set(hard_neg_candidates)
        remaining = np.array([index for index in all_resume_idx if int(index) not in excluded], dtype=int)
        if len(remaining) > 0:
            sampled = rng.choice(remaining, size=min(args.random_negs, len(remaining)), replace=False)
            random_neg_idx = [int(index) for index in sampled.tolist()]
        else:
            random_neg_idx = []

        observed_indices = sorted(observed_resumes_by_job.get(str(job["job_id"]), set()))
        selected: list[int] = []
        for index in list(top_idx) + hard_neg_candidates + random_neg_idx + observed_indices:
            idx = int(index)
            if idx not in selected:
                selected.append(idx)

        for resume_idx in selected:
            resume = resumes_df.iloc[resume_idx]
            resume_id = str(resume["resume_id"])
            job_id = str(job["job_id"])
            observed_score = observed_map.get((job_id, resume_id), np.nan)

            resume_skills = {skill.lower() for skill in resume["resume_skills_norm"] if str(skill).strip()}
            skill_overlap_count = int(len(job_skills & resume_skills))
            skill_overlap_ratio = float(skill_overlap_count / max(len(job_skills), 1))

            resume_years = float(resume["resume_years_experience"])
            job_years = float(job["job_years_required"])
            years_gap = float(resume_years - job_years)
            experience_match_flag = 1 if years_gap >= 0 else 0

            embedding_cosine = float(scores[resume_idx])
            embedding_cosine_norm = float(np.clip((embedding_cosine + 1.0) / 2.0, 0.0, 1.0))
            current_title_overlap = title_overlap_ratio(str(job["job_title"]), resume["resume_titles_norm"])
            score_value = weak_score(
                embedding_cosine_norm=embedding_cosine_norm,
                skill_overlap_ratio=skill_overlap_ratio,
                title_overlap=current_title_overlap,
                experience_match_flag=experience_match_flag,
                observed_score=observed_score,
            )
            final_label = assign_label(
                weak_score_value=score_value,
                skill_overlap_count=skill_overlap_count,
                embedding_cosine_norm=embedding_cosine_norm,
                experience_match_flag=experience_match_flag,
                observed_score=observed_score,
            )

            source = "generated_from_embeddings"
            if not np.isnan(observed_score) and resume_idx in ranked_top:
                source = "observed_and_generated"
            elif not np.isnan(observed_score):
                source = "observed_pairs_only"

            records.append(
                {
                    "source": source,
                    "job_id": job_id,
                    "resume_id": resume_id,
                    "job_title": str(job["job_title"]),
                    "job_description": str(job["job_description"]),
                    "resume_text": str(resume["resume_text"]),
                    "resume_skills_norm": resume["resume_skills_norm"],
                    "job_skills_norm": job["job_skills_norm"],
                    "embedding_cosine": embedding_cosine,
                    "embedding_cosine_norm": embedding_cosine_norm,
                    "retrieval_rank": int(ranked_top.get(resume_idx, 9999)),
                    "skill_overlap_count": skill_overlap_count,
                    "skill_overlap_ratio": skill_overlap_ratio,
                    "title_overlap_ratio": float(current_title_overlap),
                    "resume_years_experience": resume_years,
                    "job_years_required": job_years,
                    "years_gap": years_gap,
                    "experience_match_flag": int(experience_match_flag),
                    "observed_matched_score": float(observed_score) if not np.isnan(observed_score) else np.nan,
                    "weak_score": float(score_value),
                    "final_label": int(final_label),
                }
            )

    pairs_df = pd.DataFrame(records).drop_duplicates(subset=["job_id", "resume_id"], keep="first").copy()

    job_summary = (
        pairs_df.groupby("job_id")
        .agg(
            row_count=("resume_id", "count"),
            label_variety=("final_label", "nunique"),
            neg_count=("final_label", lambda values: int((values == 0).sum())),
            mid_count=("final_label", lambda values: int((values == 1).sum())),
            pos_count=("final_label", lambda values: int((values == 2).sum())),
        )
        .reset_index()
    )

    trainable_jobs = job_summary[
        (job_summary["row_count"] >= args.min_candidates_per_job)
        & (job_summary["label_variety"] >= 2)
        & (job_summary["neg_count"] >= 1)
        & (job_summary["pos_count"] >= 1)
    ]["job_id"]

    training_df = pairs_df[pairs_df["job_id"].isin(trainable_jobs)].copy()
    training_df = training_df.sort_values(["job_id", "retrieval_rank", "resume_id"]).reset_index(drop=True)

    final_cols = [
        "job_id",
        "resume_id",
        "job_title",
        "job_description",
        "resume_text",
        "resume_skills_norm",
        "job_skills_norm",
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
        "weak_score",
        "observed_matched_score",
        "final_label",
        "source",
    ]
    training_df = training_df[final_cols].copy()

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    pairs_df.to_csv(CSV_DIR / "candidate_pairs_auto.csv", index=False)
    training_df.to_csv(CSV_DIR / "ml_training_template.csv", index=False)

    parquet_written = True
    try:
        pairs_df.to_parquet(PARQUET_DIR / "candidate_pairs_auto.parquet", index=False)
        training_df.to_parquet(PARQUET_DIR / "ml_training_template.parquet", index=False)
    except Exception as exc:
        parquet_written = False
        for path in (
            PARQUET_DIR / "candidate_pairs_auto.parquet",
            PARQUET_DIR / "ml_training_template.parquet",
        ):
            if path.exists():
                path.unlink()
        print(f"[warn] Skipped parquet export: {exc}")

    summary = {
        "jobs_total": int(len(jobs_df)),
        "resumes_total": int(len(resumes_df)),
        "observed_pairs_total": int(len(observed_df)),
        "candidate_pairs_total": int(len(pairs_df)),
        "trainable_jobs": int(training_df["job_id"].nunique() if not training_df.empty else 0),
        "training_rows": int(len(training_df)),
        "label_distribution_training": (
            training_df["final_label"].value_counts().sort_index().to_dict() if not training_df.empty else {}
        ),
    }
    (DATASET_OUTPUTS_DIR / "training_dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Auto-labeling complete.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved: {CSV_DIR / 'candidate_pairs_auto.csv'}")
    if parquet_written:
        print(f"Saved: {PARQUET_DIR / 'ml_training_template.parquet'}")
    else:
        print(f"Saved: {CSV_DIR / 'ml_training_template.csv'}")


if __name__ == "__main__":
    main()
