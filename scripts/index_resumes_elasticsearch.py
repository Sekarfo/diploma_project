from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path

import numpy as np
import pandas as pd
from elasticsearch import Elasticsearch, helpers

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATASET_OUTPUTS_DIR = PROCESSED_DIR / "dataset_outputs"
PARQUET_DIR = DATASET_OUTPUTS_DIR / "parquet"
EMBEDDINGS_DIR = DATASET_OUTPUTS_DIR / "embeddings"

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
RESUME_EMBEDDINGS_CANDIDATES = (
    PROCESSED_DIR / "resume_embeddings.npy",
    DATASET_OUTPUTS_DIR / "resume_embeddings.npy",
    EMBEDDINGS_DIR / "resume_embeddings.npy",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index resumes into Elasticsearch dense vector index.")
    parser.add_argument(
        "--index-name",
        default=os.getenv("ELASTICSEARCH_INDEX", "resumes_index"),
        help="Elasticsearch index name.",
    )
    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help="Delete and recreate the index before indexing.",
    )
    parser.add_argument("--chunk-size", type=int, default=500)
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


def load_array(candidates: tuple[Path, ...], label: str) -> np.ndarray:
    for path in candidates:
        if path.exists():
            return np.load(path)
    searched = "\n- ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Could not load {label}. Checked:\n- {searched}")


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
            parts = [part.strip(" '\"") for part in text.split(",")]
            return [part for part in parts if part]
    return [str(value).strip()] if str(value).strip() else []


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

    df["resume_id"] = df["resume_id"].astype(str)
    df["resume_text"] = df["resume_text"].fillna("").astype(str)
    df["resume_skills_norm"] = df["resume_skills_norm"].apply(parse_list_col)
    df["resume_titles_norm"] = df["resume_titles_norm"].apply(parse_list_col)
    df["resume_years_experience"] = pd.to_numeric(df["resume_years_experience"], errors="coerce").fillna(0.0)
    return df


def connect_elasticsearch() -> Elasticsearch:
    es_url = os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200")
    es_username = os.getenv("ELASTICSEARCH_USERNAME")
    es_password = os.getenv("ELASTICSEARCH_PASSWORD")

    kwargs: dict = {
        "hosts": [es_url],
        "request_timeout": 60,
        "verify_certs": False,
    }
    if es_username and es_password:
        kwargs["basic_auth"] = (es_username, es_password)

    client = Elasticsearch(**kwargs)
    if not client.ping():
        raise ConnectionError(f"Could not connect to Elasticsearch at {es_url}")
    return client


def recreate_or_create_index(client: Elasticsearch, index_name: str, dims: int, recreate: bool) -> None:
    exists = client.indices.exists(index=index_name)
    if recreate and exists:
        client.indices.delete(index=index_name)
        exists = False

    if exists:
        return

    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "properties": {
                "resume_id": {"type": "keyword"},
                "resume_text": {"type": "text"},
                "resume_skills_norm": {"type": "keyword"},
                "resume_titles_norm": {"type": "keyword"},
                "resume_years_experience": {"type": "float"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": dims,
                    "index": True,
                    "similarity": "cosine",
                },
            }
        },
    }
    client.indices.create(index=index_name, body=mapping)


def generate_actions(df: pd.DataFrame, embeddings: np.ndarray, index_name: str):
    for index, row in df.iterrows():
        yield {
            "_op_type": "index",
            "_index": index_name,
            "_id": str(row["resume_id"]),
            "_source": {
                "resume_id": str(row["resume_id"]),
                "resume_text": str(row["resume_text"]),
                "resume_skills_norm": row["resume_skills_norm"],
                "resume_titles_norm": row["resume_titles_norm"],
                "resume_years_experience": float(row["resume_years_experience"]),
                "embedding": embeddings[index].tolist(),
            },
        }


def main() -> None:
    args = parse_args()
    resumes_df = normalize_resumes_df(load_dataframe(RESUMES_PARQUET_CANDIDATES, RESUMES_CSV_CANDIDATES, "resumes"))
    resume_embeddings = load_array(RESUME_EMBEDDINGS_CANDIDATES, "resume embeddings")

    if len(resumes_df) != len(resume_embeddings):
        raise ValueError(
            f"Row count mismatch: resumes={len(resumes_df)} embeddings={len(resume_embeddings)}"
        )

    dims = int(resume_embeddings.shape[1]) if len(resume_embeddings) else 0
    if dims <= 0:
        raise ValueError("Invalid embedding dimensions. Did embedding generation run successfully?")

    client = connect_elasticsearch()
    recreate_or_create_index(
        client=client,
        index_name=args.index_name,
        dims=dims,
        recreate=args.recreate_index,
    )

    actions = generate_actions(resumes_df, resume_embeddings, args.index_name)
    success, errors = helpers.bulk(
        client,
        actions,
        chunk_size=args.chunk_size,
        request_timeout=120,
        raise_on_error=False,
        stats_only=False,
    )
    client.indices.refresh(index=args.index_name)
    indexed_count = client.count(index=args.index_name)["count"]

    print("Indexing complete.")
    print(f"index_name={args.index_name}")
    print(f"recreate_index={args.recreate_index}")
    print(f"resumes={len(resumes_df)}")
    print(f"embedding_dim={dims}")
    print(f"bulk_success={success}")
    print(f"indexed_docs={indexed_count}")
    if errors:
        print(f"bulk_errors={len(errors)}")
        print(f"first_error={errors[0]}")
    else:
        print("bulk_errors=0")


if __name__ == "__main__":
    main()
