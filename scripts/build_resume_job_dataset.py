from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RESUME_PATH = BASE_DIR / "data" / "raw" / "resume_data.csv"
DEFAULT_JOBS_PATH = BASE_DIR / "data" / "raw" / "job_title_des.csv"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "processed" / "dataset_outputs"

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

SKILL_SYNONYMS = {
    "js": "javascript",
    "node.js": "nodejs",
    "node js": "nodejs",
    "react.js": "react",
    "react js": "react",
    "next.js": "nextjs",
    "next js": "nextjs",
    "vue.js": "vue",
    "vue js": "vue",
    "c sharp": "c#",
    "golang": "go",
    "postgresql": "postgres",
    "ms sql": "sql server",
    "mssql": "sql server",
    "power bi": "powerbi",
    "scikit learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "amazon web services": "aws",
    "gcp": "google cloud",
    "ml": "machine learning",
    "nlp": "natural language processing",
    "ai": "artificial intelligence",
    "tf": "tensorflow",
    "k8s": "kubernetes",
}

ROLE_SYNONYMS = {
    "sde": "software engineer",
    "software developer": "software engineer",
    "frontend developer": "frontend engineer",
    "front end developer": "frontend engineer",
    "backend developer": "backend engineer",
    "back end developer": "backend engineer",
    "full stack developer": "fullstack engineer",
    "full-stack developer": "fullstack engineer",
    "machine learning engineer": "ml engineer",
    "dev ops engineer": "devops engineer",
    "quality assurance engineer": "qa engineer",
}

SKILL_VOCAB = {
    "python",
    "java",
    "javascript",
    "typescript",
    "go",
    "php",
    "ruby",
    "c++",
    "c#",
    "scala",
    "kotlin",
    "django",
    "flask",
    "fastapi",
    "spring",
    "spring boot",
    "nodejs",
    "express",
    "laravel",
    "dotnet",
    "rest",
    "rpc",
    "json",
    "graphql",
    "react",
    "angular",
    "vue",
    "nextjs",
    "html",
    "css",
    "sass",
    "tailwind",
    "bootstrap",
    "flutter",
    "android",
    "ios",
    "swift",
    "react native",
    "machine learning",
    "deep learning",
    "natural language processing",
    "computer vision",
    "data science",
    "data analysis",
    "statistics",
    "tableau",
    "powerbi",
    "pandas",
    "numpy",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "spark",
    "hadoop",
    "hive",
    "mapreduce",
    "airflow",
    "sql",
    "mysql",
    "postgres",
    "mongodb",
    "redis",
    "elasticsearch",
    "kafka",
    "aws",
    "azure",
    "google cloud",
    "docker",
    "kubernetes",
    "linux",
    "git",
    "ci/cd",
    "terraform",
    "ansible",
    "jenkins",
    "selenium",
    "pytest",
    "junit",
    "unit testing",
    "automation testing",
    "api",
    "microservices",
    "oop",
    "dbms",
    "rdbms",
    "agile",
    "scrum",
    "etl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build clean jobs/resumes datasets and observed weak labels from raw files. "
            "This is stage-0 preprocessing before embeddings and ranker training."
        )
    )
    parser.add_argument("--resume-path", type=Path, default=DEFAULT_RESUME_PATH)
    parser.add_argument("--jobs-path", type=Path, default=DEFAULT_JOBS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--exclude-paired-jobs",
        action="store_true",
        help="Do not append paired jobs extracted from resume_data.csv.",
    )
    return parser.parse_args()


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\ufeff", " ").lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"[^a-z0-9+#./\s-]", " ", text)
    text = text.replace("/", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_list_like(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = value
    else:
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return []
        try:
            parsed = ast.literal_eval(text)
            raw = parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            raw = re.split(r"[,\n;|]", text)

    out: list[str] = []
    for item in raw:
        norm = clean_text(item)
        if not norm or norm in {"none", "null", "nan", "n a", "na"}:
            continue
        out.append(norm)
    return dedupe_keep_order(out)


def dedupe_keep_order(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out


def normalize_skill(skill: str) -> str:
    base = clean_text(skill)
    if base in SKILL_SYNONYMS:
        base = SKILL_SYNONYMS[base]
    return re.sub(r"\s+", " ", base).strip()


def normalize_title(title: str) -> str:
    base = clean_text(title)
    if base in ROLE_SYNONYMS:
        base = ROLE_SYNONYMS[base]
    return re.sub(r"\s+", " ", base).strip()


def extract_year_requirement(text: object) -> float:
    normalized = clean_text(text)
    if not normalized:
        return 0.0

    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*years?",
        r"(\d+(?:\.\d+)?)\+?\s*yrs?",
        r"at least\s*(\d+(?:\.\d+)?)",
        r"minimum\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            try:
                years = float(match.group(1))
                if 0.0 <= years <= 60.0:
                    return years
            except Exception:
                continue
    return 0.0


def parse_date_to_year_fraction(value: object) -> float | None:
    normalized = clean_text(value)
    if not normalized:
        return None
    if normalized in {"present", "current", "till date", "till now"}:
        return 2026.0

    year_match = re.search(r"(19|20)\d{2}", normalized)
    if not year_match:
        return None
    year = int(year_match.group())
    month = 6
    for month_name, month_number in MONTHS.items():
        if month_name in normalized:
            month = month_number
            break
    return year + (month - 1) / 12.0


def estimate_years_from_dates(starts: list[str], ends: list[str]) -> float:
    if not starts:
        return 0.0

    total_years = 0.0
    valid = 0
    for index, start in enumerate(starts):
        end = ends[index] if index < len(ends) else "present"
        start_year = parse_date_to_year_fraction(start)
        end_year = parse_date_to_year_fraction(end)
        if start_year is None:
            continue
        if end_year is None:
            end_year = 2026.0
        if end_year < start_year:
            continue
        total_years += end_year - start_year
        valid += 1
    if valid == 0:
        return 0.0
    return round(total_years, 2)


def extract_skills_from_text(text: str) -> list[str]:
    body = f" {clean_text(text)} "
    found: list[str] = []
    for skill in sorted(SKILL_VOCAB, key=len, reverse=True):
        pattern = rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])"
        if re.search(pattern, body):
            found.append(skill)
    return dedupe_keep_order(found)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).replace("\ufeff", "").strip() for col in df.columns]
    rename_map = {
        "job_position_name": "paired_job_title",
        "educationaL_requirements": "education_requirements",
        "experiencere_requirement": "experience_requirement",
        "responsibilities.1": "job_responsibilities",
    }
    return df.rename(columns=rename_map)


def build_resume_text(row: pd.Series) -> str:
    pieces = [
        row.get("career_objective", ""),
        " ".join(row.get("resume_titles_norm", [])),
        " ".join(row.get("resume_skills_norm", [])),
        " ".join(row.get("degree_names_norm", [])),
        " ".join(row.get("major_fields_norm", [])),
        " ".join(row.get("professional_company_names_norm", [])),
        " ".join(row.get("certification_skills_norm", [])),
    ]
    return clean_text(" ".join(str(piece) for piece in pieces))


def build_resume_fingerprint(row: pd.Series) -> str:
    tokens = [
        clean_text(row.get("career_objective", "")),
        "|".join(row.get("resume_skills_norm", [])),
        "|".join(row.get("resume_titles_norm", [])),
        "|".join(row.get("degree_names_norm", [])),
        "|".join(row.get("major_fields_norm", [])),
        "|".join(row.get("professional_company_names_norm", [])),
        "|".join(row.get("passing_years_norm", [])),
        "|".join(row.get("start_dates_norm", [])),
        "|".join(row.get("end_dates_norm", [])),
    ]
    digest = hashlib.sha1(" || ".join(tokens).encode("utf-8")).hexdigest()
    return digest


def build_resumes_table(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = raw_df.copy()
    list_columns = [
        "skills",
        "degree_names",
        "passing_years",
        "major_field_of_studies",
        "professional_company_names",
        "positions",
        "start_dates",
        "end_dates",
        "certification_skills",
    ]
    for column in list_columns:
        if column in df.columns:
            df[column] = df[column].apply(parse_list_like)
        else:
            df[column] = [[] for _ in range(len(df))]

    text_columns = [
        "career_objective",
        "responsibilities",
        "paired_job_title",
        "education_requirements",
        "experience_requirement",
        "job_responsibilities",
        "skills_required",
    ]
    for column in text_columns:
        if column not in df.columns:
            df[column] = ""
        df[column] = df[column].fillna("").astype(str)

    df["resume_skills_norm"] = df["skills"].apply(
        lambda values: dedupe_keep_order(normalize_skill(x) for x in values if x)
    )
    df["resume_titles_norm"] = df["positions"].apply(
        lambda values: dedupe_keep_order(normalize_title(x) for x in values if x)
    )
    df["degree_names_norm"] = df["degree_names"].apply(
        lambda values: dedupe_keep_order(clean_text(x) for x in values if x)
    )
    df["major_fields_norm"] = df["major_field_of_studies"].apply(
        lambda values: dedupe_keep_order(clean_text(x) for x in values if x)
    )
    df["professional_company_names_norm"] = df["professional_company_names"].apply(
        lambda values: dedupe_keep_order(clean_text(x) for x in values if x)
    )
    df["passing_years_norm"] = df["passing_years"].apply(
        lambda values: dedupe_keep_order(clean_text(x) for x in values if x)
    )
    df["start_dates_norm"] = df["start_dates"].apply(
        lambda values: dedupe_keep_order(clean_text(x) for x in values if x)
    )
    df["end_dates_norm"] = df["end_dates"].apply(
        lambda values: dedupe_keep_order(clean_text(x) for x in values if x)
    )
    df["certification_skills_norm"] = df["certification_skills"].apply(
        lambda values: dedupe_keep_order(normalize_skill(x) for x in values if x)
    )

    df["resume_years_experience"] = df.apply(
        lambda row: estimate_years_from_dates(
            row.get("start_dates_norm", []),
            row.get("end_dates_norm", []),
        ),
        axis=1,
    )
    df["matched_score"] = pd.to_numeric(df.get("matched_score", 0.0), errors="coerce").fillna(0.0)
    df["resume_text"] = df.apply(build_resume_text, axis=1)
    df["resume_fingerprint"] = df.apply(build_resume_fingerprint, axis=1)

    fingerprints = pd.Series(df["resume_fingerprint"]).drop_duplicates().tolist()
    fingerprint_to_id = {
        fingerprint: f"resume_{index:05d}"
        for index, fingerprint in enumerate(fingerprints, start=1)
    }
    df["resume_id"] = df["resume_fingerprint"].map(fingerprint_to_id)

    resumes_df = (
        df.sort_values(["resume_fingerprint", "matched_score"], ascending=[True, False])
        .drop_duplicates(subset=["resume_fingerprint"], keep="first")
        .copy()
    )

    resumes_df = resumes_df[
        [
            "resume_id",
            "resume_text",
            "resume_skills_norm",
            "resume_titles_norm",
            "resume_years_experience",
        ]
    ].copy()

    return df, resumes_df


def build_external_jobs_table(raw_jobs_path: Path) -> pd.DataFrame:
    jobs = pd.read_csv(raw_jobs_path).copy()
    jobs.columns = [str(col).replace("\ufeff", "").strip() for col in jobs.columns]
    drop_columns = [col for col in jobs.columns if col.startswith("Unnamed:") or re.match(r"^H\d+$", col)]
    if drop_columns:
        jobs = jobs.drop(columns=drop_columns)

    jobs = jobs.rename(columns={"Job Title": "job_title", "Job Description": "job_description"})
    if "job_title" not in jobs.columns:
        jobs["job_title"] = ""
    if "job_description" not in jobs.columns:
        jobs["job_description"] = ""

    jobs["job_title"] = jobs["job_title"].fillna("").astype(str)
    jobs["job_description"] = jobs["job_description"].fillna("").astype(str)
    jobs["job_title_norm"] = jobs["job_title"].apply(normalize_title)
    jobs["job_text"] = (jobs["job_title"] + " " + jobs["job_description"]).apply(clean_text)
    jobs = jobs[jobs["job_text"] != ""].copy()
    jobs["job_key"] = jobs["job_title_norm"] + " || " + jobs["job_text"]
    jobs = jobs.drop_duplicates(subset=["job_key"]).reset_index(drop=True)

    jobs["job_skills_norm"] = jobs.apply(
        lambda row: extract_skills_from_text(f"{row['job_title']} {row['job_description']}"),
        axis=1,
    )
    jobs["job_years_required"] = jobs.apply(
        lambda row: extract_year_requirement(f"{row['job_title']} {row['job_description']}"),
        axis=1,
    )
    jobs["job_source"] = "external_jobs"
    jobs["job_id"] = [f"job_ext_{index:05d}" for index in range(1, len(jobs) + 1)]

    return jobs[
        [
            "job_id",
            "job_title",
            "job_description",
            "job_text",
            "job_title_norm",
            "job_skills_norm",
            "job_years_required",
            "job_key",
            "job_source",
        ]
    ].copy()


def build_paired_jobs_table(raw_pairs_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = [
        "paired_job_title",
        "education_requirements",
        "experience_requirement",
        "job_responsibilities",
        "skills_required",
    ]
    for column in required_columns:
        if column not in raw_pairs_df.columns:
            raw_pairs_df[column] = ""

    jobs = raw_pairs_df[required_columns].copy()
    for column in required_columns:
        jobs[column] = jobs[column].fillna("").astype(str)

    jobs["job_title"] = jobs["paired_job_title"].apply(lambda value: str(value).strip())
    jobs["job_description"] = (
        jobs["education_requirements"] + " "
        + jobs["experience_requirement"] + " "
        + jobs["job_responsibilities"] + " "
        + jobs["skills_required"]
    ).apply(clean_text)
    jobs["job_title_norm"] = jobs["job_title"].apply(normalize_title)
    jobs["job_text"] = (jobs["job_title"] + " " + jobs["job_description"]).apply(clean_text)
    jobs = jobs[(jobs["job_title"] != "") | (jobs["job_description"] != "")].copy()
    jobs["job_key"] = jobs["job_title_norm"] + " || " + jobs["job_text"]
    jobs = jobs.drop_duplicates(subset=["job_key"]).reset_index(drop=True)

    jobs["job_skills_norm"] = jobs.apply(
        lambda row: dedupe_keep_order(
            parse_list_like(row.get("skills_required", ""))
            + extract_skills_from_text(f"{row['job_title']} {row['job_description']}")
        ),
        axis=1,
    )
    jobs["job_years_required"] = jobs.apply(
        lambda row: extract_year_requirement(
            f"{row['experience_requirement']} {row['job_description']}"
        ),
        axis=1,
    )
    jobs["job_source"] = "paired_jobs"
    jobs["job_id"] = [f"job_pair_{index:05d}" for index in range(1, len(jobs) + 1)]

    return jobs[
        [
            "job_id",
            "job_title",
            "job_description",
            "job_text",
            "job_title_norm",
            "job_skills_norm",
            "job_years_required",
            "job_key",
            "job_source",
        ]
    ].copy()


def build_observed_pairs(raw_pairs_df: pd.DataFrame, jobs_df: pd.DataFrame) -> pd.DataFrame:
    job_id_by_key = {row.job_key: row.job_id for row in jobs_df.itertuples()}

    pair_rows = raw_pairs_df.copy()
    for column in [
        "paired_job_title",
        "education_requirements",
        "experience_requirement",
        "job_responsibilities",
        "skills_required",
    ]:
        if column not in pair_rows.columns:
            pair_rows[column] = ""
        pair_rows[column] = pair_rows[column].fillna("").astype(str)

    pair_rows["pair_job_title_norm"] = pair_rows["paired_job_title"].apply(normalize_title)
    pair_rows["pair_job_text"] = (
        pair_rows["paired_job_title"]
        + " "
        + pair_rows["education_requirements"]
        + " "
        + pair_rows["experience_requirement"]
        + " "
        + pair_rows["job_responsibilities"]
        + " "
        + pair_rows["skills_required"]
    ).apply(clean_text)
    pair_rows["pair_job_key"] = pair_rows["pair_job_title_norm"] + " || " + pair_rows["pair_job_text"]
    pair_rows["job_id"] = pair_rows["pair_job_key"].map(job_id_by_key)
    pair_rows["matched_score"] = pd.to_numeric(pair_rows.get("matched_score", 0.0), errors="coerce").fillna(0.0)
    pair_rows = pair_rows.dropna(subset=["job_id", "resume_id"]).copy()

    observed = (
        pair_rows.groupby(["job_id", "resume_id"], as_index=False)
        .agg(
            matched_score=("matched_score", "max"),
            observed_pair_count=("matched_score", "size"),
        )
        .copy()
    )
    observed["source"] = "observed_paired_score"
    observed = observed[
        ["source", "job_id", "resume_id", "matched_score", "observed_pair_count"]
    ].copy()
    return observed


def save_table(
    *,
    df: pd.DataFrame,
    name: str,
    output_dir: Path,
    csv_dir: Path,
    parquet_dir: Path,
    save_root_csv: bool,
) -> None:
    if save_root_csv:
        df.to_csv(output_dir / f"{name}.csv", index=False)
    df.to_csv(csv_dir / f"{name}.csv", index=False)
    parquet_path = parquet_dir / f"{name}.parquet"
    try:
        df.to_parquet(parquet_path, index=False)
    except Exception as exc:
        if parquet_path.exists():
            parquet_path.unlink()
        print(f"[warn] Skipped parquet for {name}: {exc}")


def main() -> None:
    args = parse_args()
    resume_path = args.resume_path.resolve()
    jobs_path = args.jobs_path.resolve()
    output_dir = args.output_dir.resolve()
    csv_dir = output_dir / "csv"
    parquet_dir = output_dir / "parquet"

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)
    parquet_dir.mkdir(parents=True, exist_ok=True)

    raw_pairs_df = pd.read_csv(resume_path)
    raw_pairs_df = normalize_columns(raw_pairs_df)
    enriched_pairs_df, resumes_df = build_resumes_table(raw_pairs_df)
    external_jobs_df = build_external_jobs_table(jobs_path)

    jobs_parts = [external_jobs_df]
    paired_jobs_count = 0
    if not args.exclude_paired_jobs:
        paired_jobs_df = build_paired_jobs_table(enriched_pairs_df)
        jobs_parts.append(paired_jobs_df)
        paired_jobs_count = len(paired_jobs_df)

    jobs_df = pd.concat(jobs_parts, ignore_index=True).drop_duplicates(subset=["job_key"], keep="first").copy()
    jobs_df = jobs_df[
        [
            "job_id",
            "job_title",
            "job_description",
            "job_text",
            "job_skills_norm",
            "job_years_required",
            "job_source",
            "job_key",
        ]
    ].copy()

    observed_pairs_df = build_observed_pairs(enriched_pairs_df, jobs_df)

    jobs_export_df = jobs_df.drop(columns=["job_key"]).copy()
    save_table(
        df=resumes_df,
        name="resumes_clean",
        output_dir=output_dir,
        csv_dir=csv_dir,
        parquet_dir=parquet_dir,
        save_root_csv=True,
    )
    save_table(
        df=jobs_export_df,
        name="jobs_clean",
        output_dir=output_dir,
        csv_dir=csv_dir,
        parquet_dir=parquet_dir,
        save_root_csv=True,
    )
    save_table(
        df=observed_pairs_df,
        name="observed_pairs",
        output_dir=output_dir,
        csv_dir=csv_dir,
        parquet_dir=parquet_dir,
        save_root_csv=False,
    )

    summary = {
        "raw_resume_rows": int(len(raw_pairs_df)),
        "unique_resumes_after_dedup": int(len(resumes_df)),
        "external_jobs": int(len(external_jobs_df)),
        "paired_jobs_added": int(paired_jobs_count),
        "final_jobs_after_union": int(len(jobs_export_df)),
        "observed_pairs": int(len(observed_pairs_df)),
        "paths": {
            "jobs_csv": str(output_dir / "jobs_clean.csv"),
            "resumes_csv": str(output_dir / "resumes_clean.csv"),
            "observed_pairs_csv": str(csv_dir / "observed_pairs.csv"),
        },
    }
    (output_dir / "dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Preprocessing complete.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
