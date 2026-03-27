from __future__ import annotations

import argparse
import ast
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATASET_OUTPUTS_DIR = PROCESSED_DIR / "dataset_outputs"
EMBEDDINGS_DIR = DATASET_OUTPUTS_DIR / "embeddings"
PARQUET_DIR = DATASET_OUTPUTS_DIR / "parquet"

JOBS_PARQUET_CANDIDATES = (
    PROCESSED_DIR / "jobs_clean.parquet",
    DATASET_OUTPUTS_DIR / "jobs_clean.parquet",
    PARQUET_DIR / "jobs_clean.parquet",
)
JOBS_CSV_CANDIDATES = (
    PROCESSED_DIR / "jobs_clean.csv",
    DATASET_OUTPUTS_DIR / "jobs_clean.csv",
    DATASET_OUTPUTS_DIR / "csv" / "jobs_clean.csv",
)
RESUMES_PARQUET_CANDIDATES = (
    PROCESSED_DIR / "resumes_clean.parquet",
    DATASET_OUTPUTS_DIR / "resumes_clean.parquet",
    PARQUET_DIR / "resumes_clean.parquet",
)
RESUMES_CSV_CANDIDATES = (
    PROCESSED_DIR / "resumes_clean.csv",
    DATASET_OUTPUTS_DIR / "resumes_clean.csv",
    DATASET_OUTPUTS_DIR / "csv" / "resumes_clean.csv",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Sentence-BERT embeddings for cleaned jobs and resumes datasets."
    )
    parser.add_argument(
        "--model-name",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model name.",
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--disable-normalize",
        action="store_true",
        help="Disable embedding normalization.",
    )
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


def parse_list_col(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, np.ndarray):
        return [str(x).strip() for x in value.tolist() if str(x).strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() == "nan":
            return []
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, np.ndarray):
                return [str(x).strip() for x in parsed.tolist() if str(x).strip()]
            if isinstance(parsed, (list, tuple, set)):
                return [str(x).strip() for x in parsed if str(x).strip()]
            if isinstance(parsed, str):
                return [parsed.strip()] if parsed.strip() else []
            return [str(parsed).strip()]
        except Exception:
            if "," in text:
                return [part.strip() for part in text.split(",") if part.strip()]
            return [text]
    return [str(value).strip()] if str(value).strip() else []


def normalize_jobs_df(df: pd.DataFrame) -> pd.DataFrame:
    if "job_id" not in df.columns:
        raise ValueError("jobs dataset missing required column: job_id")
    if "job_text" not in df.columns:
        raise ValueError("jobs dataset missing required column: job_text")

    if "job_skills_norm" not in df.columns:
        df["job_skills_norm"] = [[] for _ in range(len(df))]
    if "job_years_required" not in df.columns:
        df["job_years_required"] = 0.0

    df["job_text"] = df["job_text"].fillna("").astype(str)
    df["job_skills_norm"] = df["job_skills_norm"].apply(parse_list_col)
    df["job_years_required"] = pd.to_numeric(df["job_years_required"], errors="coerce").fillna(0.0)
    return df


def normalize_resumes_df(df: pd.DataFrame) -> pd.DataFrame:
    if "resume_id" not in df.columns:
        raise ValueError("resumes dataset missing required column: resume_id")
    if "resume_text" not in df.columns:
        raise ValueError("resumes dataset missing required column: resume_text")

    if "resume_skills_norm" not in df.columns:
        df["resume_skills_norm"] = [[] for _ in range(len(df))]
    if "resume_titles_norm" not in df.columns:
        df["resume_titles_norm"] = [[] for _ in range(len(df))]
    if "resume_years_experience" not in df.columns:
        df["resume_years_experience"] = 0.0

    df["resume_text"] = df["resume_text"].fillna("").astype(str)
    df["resume_skills_norm"] = df["resume_skills_norm"].apply(parse_list_col)
    df["resume_titles_norm"] = df["resume_titles_norm"].apply(parse_list_col)
    df["resume_years_experience"] = pd.to_numeric(df["resume_years_experience"], errors="coerce").fillna(0.0)
    return df


def encode_jobs(model: SentenceTransformer, texts: list[str], batch_size: int, normalize: bool) -> np.ndarray:
    if hasattr(model, "encode_query"):
        vectors = model.encode_query(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=normalize,
        )
    else:
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=normalize,
        )
    return np.asarray(vectors, dtype="float32")


def encode_resumes(model: SentenceTransformer, texts: list[str], batch_size: int, normalize: bool) -> np.ndarray:
    if hasattr(model, "encode_document"):
        vectors = model.encode_document(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=normalize,
        )
    else:
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=normalize,
        )
    return np.asarray(vectors, dtype="float32")


def main() -> None:
    args = parse_args()
    normalize_embeddings = not args.disable_normalize

    jobs_df = normalize_jobs_df(load_dataframe(JOBS_PARQUET_CANDIDATES, JOBS_CSV_CANDIDATES, "jobs dataset"))
    resumes_df = normalize_resumes_df(
        load_dataframe(RESUMES_PARQUET_CANDIDATES, RESUMES_CSV_CANDIDATES, "resumes dataset")
    )

    model = SentenceTransformer(args.model_name)

    job_embeddings = encode_jobs(
        model=model,
        texts=jobs_df["job_text"].tolist(),
        batch_size=args.batch_size,
        normalize=normalize_embeddings,
    )
    resume_embeddings = encode_resumes(
        model=model,
        texts=resumes_df["resume_text"].tolist(),
        batch_size=args.batch_size,
        normalize=normalize_embeddings,
    )

    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    np.save(EMBEDDINGS_DIR / "job_embeddings.npy", job_embeddings)
    np.save(EMBEDDINGS_DIR / "resume_embeddings.npy", resume_embeddings)

    try:
        jobs_df.to_parquet(PARQUET_DIR / "jobs_clean.parquet", index=False)
        resumes_df.to_parquet(PARQUET_DIR / "resumes_clean.parquet", index=False)
    except Exception as exc:
        for path in (PARQUET_DIR / "jobs_clean.parquet", PARQUET_DIR / "resumes_clean.parquet"):
            if path.exists():
                path.unlink()
        print(f"[warn] Skipped parquet export: {exc}")

    print("Embeddings complete.")
    print(f"Model: {args.model_name}")
    print(f"normalize_embeddings={normalize_embeddings}")
    print(f"jobs={len(jobs_df)} resumes={len(resumes_df)}")
    print(f"embedding_dim={job_embeddings.shape[1] if len(job_embeddings) else 0}")
    print(f"Saved: {EMBEDDINGS_DIR / 'job_embeddings.npy'}")
    print(f"Saved: {EMBEDDINGS_DIR / 'resume_embeddings.npy'}")


if __name__ == "__main__":
    main()
