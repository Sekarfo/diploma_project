"""
Remove duplicate phrases from resume_text in resumes_clean.csv.

Resume texts are built by concatenating job titles with 2+ spaces as separator.
Many resumes have the same job title listed multiple times (e.g. "project manager"
appearing 8 times in a row). This script deduplicates those segments while
preserving the original order and the full free-text description at the end.

Usage:
    python data/clean_resume_duplicates.py
    python data/clean_resume_duplicates.py --dry-run   # preview stats only, no write
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).parent / "Clear" / "resumes_clean.csv"


def dedup_resume(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return text

    # Split on 2+ consecutive spaces — that's the segment delimiter in resume_text
    parts = re.split(r"  +", text)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) <= 1:
        return text

    seen: set[str] = set()
    unique: list[str] = []
    for part in parts:
        key = part.lower()
        if key not in seen:
            seen.add(key)
            unique.append(part)

    return "   ".join(unique)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print stats without saving")
    args = parser.parse_args()

    print(f"Reading {CSV_PATH} …")
    df = pd.read_csv(CSV_PATH)
    total = len(df)
    print(f"  Loaded {total:,} resumes")

    cleaned = df["resume_text"].apply(dedup_resume)

    changed_mask = cleaned != df["resume_text"]
    changed_count = int(changed_mask.sum())

    before_chars = int(df["resume_text"].str.len().sum())
    after_chars = int(cleaned.str.len().sum())
    removed_chars = before_chars - after_chars

    print(f"  Resumes with duplicates removed : {changed_count:,} / {total:,}")
    print(f"  Characters before               : {before_chars:,}")
    print(f"  Characters after                : {after_chars:,}")
    print(f"  Characters removed              : {removed_chars:,} ({removed_chars / before_chars * 100:.1f}%)")

    if args.dry_run:
        print("\n[dry-run] No file written.")
        # Show a few examples
        examples = df.loc[changed_mask, "resume_text"].head(3).index
        for idx in examples:
            before = df.at[idx, "resume_text"]
            after = cleaned.at[idx]
            print(f"\n--- person_id={df.at[idx, 'person_id']} ---")
            print(f"BEFORE ({len(before)} chars): {before[:300]}")
            print(f"AFTER  ({len(after)} chars): {after[:300]}")
        return

    df["resume_text"] = cleaned
    df.to_csv(CSV_PATH, index=False)
    print(f"\nSaved cleaned CSV to {CSV_PATH}")
    print("NOTE: Re-index Elasticsearch after this change so the search index reflects clean texts.")
    print("      Run: python src/embeddings/index_elasticsearch.py")


if __name__ == "__main__":
    main()
