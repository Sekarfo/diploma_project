from pathlib import Path
import argparse
import ast
import os

import numpy as np
import pandas as pd
from elasticsearch import Elasticsearch

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATASET_OUTPUTS_DIR = PROCESSED_DIR / "dataset_outputs"

JOBS_PARQUET_CANDIDATES = [
    PROCESSED_DIR / "jobs_clean.parquet",
    DATASET_OUTPUTS_DIR / "jobs_clean.parquet",
    DATASET_OUTPUTS_DIR / "parquet" / "jobs_clean.parquet",
]
JOBS_CSV_CANDIDATES = [
    PROCESSED_DIR / "jobs_clean.csv",
    DATASET_OUTPUTS_DIR / "jobs_clean.csv",
    DATASET_OUTPUTS_DIR / "csv" / "jobs_clean.csv",
]
JOB_EMBEDDINGS_CANDIDATES = [
    PROCESSED_DIR / "job_embeddings.npy",
    DATASET_OUTPUTS_DIR / "job_embeddings.npy",
    DATASET_OUTPUTS_DIR / "embeddings" / "job_embeddings.npy",
]

OUTPUT_DIR = PROCESSED_DIR
INDEX_NAME = "resumes_index"


# -----------------------------
# Helpers
# -----------------------------
def load_jobs() -> pd.DataFrame:
    read_errors: list[str] = []
    for path in JOBS_PARQUET_CANDIDATES:
        if path.exists():
            try:
                return pd.read_parquet(path)
            except Exception as exc:
                read_errors.append(f"parquet read failed for {path}: {exc}")
    for path in JOBS_CSV_CANDIDATES:
        if path.exists():
            try:
                return pd.read_csv(path)
            except Exception as exc:
                read_errors.append(f"csv read failed for {path}: {exc}")

    searched = "\n".join(
        f"- {p}" for p in (JOBS_PARQUET_CANDIDATES + JOBS_CSV_CANDIDATES)
    )
    details = ("\nRead errors:\n- " + "\n- ".join(read_errors)) if read_errors else ""
    raise FileNotFoundError(f"Could not find jobs dataset. Searched:\n{searched}{details}")


def load_job_embeddings() -> np.ndarray:
    for path in JOB_EMBEDDINGS_CANDIDATES:
        if path.exists():
            return np.load(path)

    searched = "\n".join(f"- {p}" for p in JOB_EMBEDDINGS_CANDIDATES)
    raise FileNotFoundError(f"Missing job embeddings file. Searched:\n{searched}")


def parse_list_col(x):
    if x is None:
        return []
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (list, tuple, set)):
        return list(x)
    if isinstance(x, str):
        x = x.strip()
        if x == "" or x.lower() == "nan":
            return []
        try:
            parsed = ast.literal_eval(x)
            if isinstance(parsed, np.ndarray):
                return parsed.tolist()
            if isinstance(parsed, (list, tuple, set)):
                return list(parsed)
            return [str(parsed)]
        except Exception:
            return [x]
    try:
        if pd.isna(x):
            return []
    except Exception:
        pass
    return [x]


def connect_es() -> Elasticsearch:
    es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    es_username = os.getenv("ELASTICSEARCH_USERNAME")
    es_password = os.getenv("ELASTICSEARCH_PASSWORD")

    if es_username and es_password:
        client = Elasticsearch(
            es_url,
            basic_auth=(es_username, es_password),
            request_timeout=60,
        )
    else:
        client = Elasticsearch(
            es_url,
            request_timeout=60,
        )

    if not client.ping():
        raise ConnectionError(f"Could not connect to Elasticsearch at {es_url}")

    return client


def normalize_jobs_df(df: pd.DataFrame) -> pd.DataFrame:
    if "job_id" not in df.columns:
        raise ValueError("Missing column: job_id")
    if "job_text" not in df.columns:
        raise ValueError("Missing column: job_text")

    if "job_title" not in df.columns:
        df["job_title"] = ""
    if "job_description" not in df.columns:
        df["job_description"] = ""
    if "job_skills_norm" not in df.columns:
        df["job_skills_norm"] = [[] for _ in range(len(df))]
    if "job_years_required" not in df.columns:
        df["job_years_required"] = 0.0

    df["job_text"] = df["job_text"].fillna("").astype(str)
    df["job_title"] = df["job_title"].fillna("").astype(str)
    df["job_description"] = df["job_description"].fillna("").astype(str)
    df["job_skills_norm"] = df["job_skills_norm"].apply(parse_list_col)
    df["job_years_required"] = pd.to_numeric(
        df["job_years_required"], errors="coerce"
    ).fillna(0.0)

    return df


def knn_search(
    es: Elasticsearch,
    index_name: str,
    query_vector: np.ndarray,
    top_k: int,
    num_candidates: int,
):
    response = es.search(
        index=index_name,
        knn={
            "field": "embedding",
            "query_vector": query_vector.tolist(),
            "k": top_k,
            "num_candidates": num_candidates,
        },
        source=[
            "resume_id",
            "resume_text",
            "resume_skills_norm",
            "resume_titles_norm",
            "resume_years_experience",
        ],
        size=top_k,
    )
    return response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", type=str, required=True, help="Job ID to retrieve candidates for")
    parser.add_argument("--top-k", type=int, default=20, help="How many candidates to return")
    parser.add_argument("--num-candidates", type=int, default=100, help="Approximate search candidate pool")
    args = parser.parse_args()

    jobs_df = normalize_jobs_df(load_jobs().copy())
    job_embeddings = load_job_embeddings()

    if len(jobs_df) != len(job_embeddings):
        raise ValueError(
            f"Row count mismatch: jobs={len(jobs_df)} embeddings={len(job_embeddings)}"
        )

    match = jobs_df.index[jobs_df["job_id"].astype(str) == str(args.job_id)].tolist()
    if not match:
        raise ValueError(f"job_id not found: {args.job_id}")

    job_row_idx = match[0]
    job_row = jobs_df.iloc[job_row_idx]
    query_vector = job_embeddings[job_row_idx]

    print(f"Job ID: {job_row['job_id']}")
    print(f"Job title: {job_row['job_title']}")
    print(f"Top K: {args.top_k}")
    print(f"Num candidates: {args.num_candidates}")

    es = connect_es()
    response = knn_search(
        es=es,
        index_name=INDEX_NAME,
        query_vector=query_vector,
        top_k=args.top_k,
        num_candidates=args.num_candidates,
    )

    hits = response["hits"]["hits"]
    print(f"Retrieved hits: {len(hits)}")

    rows = []
    for rank, hit in enumerate(hits, start=1):
        src = hit["_source"]
        rows.append(
            {
                "job_id": str(job_row["job_id"]),
                "job_title": str(job_row["job_title"]),
                "job_skills_norm": job_row["job_skills_norm"],
                "job_years_required": float(job_row["job_years_required"]),
                "retrieval_rank": rank,
                "elastic_score": float(hit["_score"]),
                "resume_id": src.get("resume_id", ""),
                "resume_text": src.get("resume_text", ""),
                "resume_skills_norm": src.get("resume_skills_norm", []),
                "resume_titles_norm": src.get("resume_titles_norm", []),
                "resume_years_experience": float(src.get("resume_years_experience", 0.0)),
            }
        )

    out_df = pd.DataFrame(rows)

    output_path = OUTPUT_DIR / f"retrieved_candidates_{args.job_id}.csv"
    out_df.to_csv(output_path, index=False)

    print(f"Saved retrieval results to: {output_path}")
    print()
    if not out_df.empty:
        print(out_df[["retrieval_rank", "elastic_score", "resume_id", "resume_years_experience"]].head(10).to_string(index=False))
    else:
        print("No results returned.")


if __name__ == "__main__":
    main()
