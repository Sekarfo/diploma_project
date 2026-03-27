from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Ensure repo root is importable when running via `python scripts/rerank_candidates_elasticsearch.py`.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services import ShortlistService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Runtime reranking: Elasticsearch retrieval -> feature rebuild -> XGBRanker scoring."
    )
    parser.add_argument("--job-id", required=True, help="job_id from jobs_clean dataset")
    parser.add_argument("--top-k", type=int, default=20, help="How many candidates to retrieve from ES")
    parser.add_argument("--num-candidates", type=int, default=100, help="kNN candidate pool size in ES")
    parser.add_argument("--index-name", default=None, help="Override Elasticsearch index name")
    parser.add_argument(
        "--retrieved-csv",
        default=None,
        help="Optional retrieval CSV path to skip Elasticsearch (offline smoke mode).",
    )
    parser.add_argument(
        "--allow-elastic-score-fallback",
        action="store_true",
        help="Use ES _score only if a retrieved resume_id is missing in local embeddings.",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Output shortlist CSV path. Default: data/processed/final_shortlist_<job_id>.csv",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Output shortlist JSON path. Default: data/processed/final_shortlist_<job_id>.json",
    )
    parser.add_argument("--print-top", type=int, default=10, help="Rows to print in summary table")
    return parser.parse_args()


def shortlist_to_dataframe(shortlist_payload: dict) -> pd.DataFrame:
    rows: list[dict] = []
    for candidate in shortlist_payload.get("candidates", []):
        explanation = candidate.get("explanation", {}) or {}
        rows.append(
            {
                "job_id": shortlist_payload.get("job_id"),
                "final_rank": candidate.get("final_rank"),
                "resume_id": candidate.get("resume_id"),
                "model_score": candidate.get("model_score"),
                "retrieval_rank": candidate.get("retrieval_rank"),
                "embedding_cosine": candidate.get("embedding_cosine"),
                "skill_overlap_count": candidate.get("skill_overlap_count"),
                "skill_overlap_ratio": candidate.get("skill_overlap_ratio"),
                "title_overlap_ratio": candidate.get("title_overlap_ratio"),
                "resume_years_experience": candidate.get("resume_years_experience"),
                "job_years_required": candidate.get("job_years_required"),
                "years_gap": candidate.get("years_gap"),
                "experience_match_flag": candidate.get("experience_match_flag"),
                "matched_skills": explanation.get("matched_skills", []),
                "missing_skills": explanation.get("missing_skills", []),
                "experience_summary": explanation.get("experience_summary", ""),
                "title_summary": explanation.get("title_summary", ""),
            }
        )
    return pd.DataFrame(rows)


def save_outputs(
    *,
    shortlist_payload: dict,
    output_csv: Path,
    output_json: Path,
) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    df = shortlist_to_dataframe(shortlist_payload)
    df.to_csv(output_csv, index=False)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **shortlist_payload,
    }
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    retrieved_csv = Path(args.retrieved_csv) if args.retrieved_csv else None

    default_csv = ROOT_DIR / "data" / "processed" / f"final_shortlist_{args.job_id}.csv"
    default_json = ROOT_DIR / "data" / "processed" / f"final_shortlist_{args.job_id}.json"
    output_csv = Path(args.output_csv) if args.output_csv else default_csv
    output_json = Path(args.output_json) if args.output_json else default_json

    service = ShortlistService()
    shortlist_payload = service.shortlist(
        job_id=args.job_id,
        top_k=args.top_k,
        num_candidates=args.num_candidates,
        index_name=args.index_name,
        retrieved_csv=retrieved_csv,
        allow_elastic_score_fallback=args.allow_elastic_score_fallback,
    )

    save_outputs(
        shortlist_payload=shortlist_payload,
        output_csv=output_csv,
        output_json=output_json,
    )

    print(f"Job ID: {shortlist_payload['job_id']}")
    print(f"Job title: {shortlist_payload['job_title']}")
    print(f"Ranked candidates: {shortlist_payload['total_candidates']}")
    print(f"Saved CSV: {output_csv}")
    print(f"Saved JSON: {output_json}")

    df = shortlist_to_dataframe(shortlist_payload)
    preview_cols = [
        "final_rank",
        "resume_id",
        "model_score",
        "retrieval_rank",
        "embedding_cosine",
        "skill_overlap_count",
        "skill_overlap_ratio",
        "title_overlap_ratio",
        "years_gap",
    ]
    if not df.empty and args.print_top > 0:
        print()
        print(df[preview_cols].head(args.print_top).to_string(index=False))


if __name__ == "__main__":
    main()
