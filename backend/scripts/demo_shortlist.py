from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib import error, request


def load_payload(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Payload file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def call_shortlist_api(base_url: str, endpoint: str, payload: dict) -> dict:
    endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = f"{base_url.rstrip('/')}{endpoint}"
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        with request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"API returned HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not connect to API: {exc}") from exc


def print_result(result: dict) -> None:
    candidates = result.get("candidates", [])
    print(f"\nJob: {result.get('job_id', '<unknown>')} | {result.get('job_title', '')}")
    print(f"Retrieved: {result.get('retrieved_count', 0)} | Ranked: {result.get('total_candidates', 0)}")
    print("-" * 120)
    print(
        f"{'Rank':>4} {'Resume':<18} {'Model':>9} {'Retr':>5} {'Cos':>8} "
        f"{'SkillCnt':>8} {'SkillRat':>8} {'YearsGap':>8}"
    )
    print("-" * 120)
    for item in candidates:
        print(
            f"{int(item.get('final_rank', 0)):>4} "
            f"{str(item.get('resume_id', '')):<18} "
            f"{float(item.get('model_score', 0.0)):>9.4f} "
            f"{int(item.get('retrieval_rank', 0)):>5} "
            f"{float(item.get('embedding_cosine', 0.0)):>8.4f} "
            f"{int(item.get('skill_overlap_count', 0)):>8} "
            f"{float(item.get('skill_overlap_ratio', 0.0)):>8.2f} "
            f"{float(item.get('years_gap', 0.0)):>8.2f}"
        )
        explanation = item.get("explanation", {}) or {}
        print(
            "      explanation: matched="
            f"{', '.join(explanation.get('matched_skills', [])) or 'none'}; "
            f"missing={', '.join(explanation.get('missing_skills', [])) or 'none'}; "
            f"{explanation.get('experience_summary', '')} "
            f"{explanation.get('title_summary', '')}"
        )
    print("-" * 120)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local shortlist API demo request.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL.")
    parser.add_argument(
        "--endpoint",
        default="/shortlist",
        help="API endpoint: /shortlist or /shortlist/vacancy",
    )
    parser.add_argument(
        "--request-file",
        default="backend/examples/shortlist_request.json",
        help="Path to JSON request payload.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = load_payload(Path(args.request_file))
    result = call_shortlist_api(args.base_url, args.endpoint, payload)
    print_result(result)


if __name__ == "__main__":
    main()
