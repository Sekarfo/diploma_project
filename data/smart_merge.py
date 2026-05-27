import pandas as pd
import re

people     = pd.read_csv("01_people.csv")
abilities  = pd.read_csv("02_abilities.csv")
education  = pd.read_csv("03_education.csv")
experience = pd.read_csv("04_experience.csv")
skills     = pd.read_csv("05_person_skills.csv")

# spine: only person_id is trustworthy from 01_people
spine = people[["person_id"]].drop_duplicates().copy()

# --- 02 abilities: reconstruct paragraph per person ---
abilities_agg = (
    abilities.dropna(subset=["ability"])
    .astype({"ability": str})
    .groupby("person_id")["ability"]
    .agg(lambda s: " ".join(x.strip() for x in s))
    .reset_index()
    .rename(columns={"ability": "abilities_text"})
)

# --- 03 education: extract degree level ---
def degree_level(prog):
    if not isinstance(prog, str): return 0
    p = prog.lower()
    if any(k in p for k in ("phd", "ph.d", "doctor")):                 return 4
    if any(k in p for k in ("master", "msc", "m.sc", "m.s.", "mba")):  return 3
    if any(k in p for k in ("bachelor", "bsc", "b.sc", "b.s.",
                            "b.a.", "ba ", "bs in")):                  return 2
    if any(k in p for k in ("associate", "diploma")):                  return 1
    return 0

education["degree_level"] = education["program"].apply(degree_level)
edu_agg = (
    education.groupby("person_id")["degree_level"].max()
    .reset_index().rename(columns={"degree_level": "highest_education"})
)

# --- 04 experience: total years + titles/firms ---
def parse_date(x):
    if pd.isna(x): return pd.NaT
    s = str(x).strip()
    if s.lower() in {"present", "current", "till date", "now", ""}:
        return pd.Timestamp.today()
    
    # MM/YY → MM/20YY (or 19YY for older). Pandas can't infer this alone.
    m = re.fullmatch(r"(\d{1,2})/(\d{2})", s)
    if m:
        month, yy = m.group(1), int(m.group(2))
        full_year = 2000 + yy if yy <= 30 else 1900 + yy   # pivot at 2030
        s = f"{month}/{full_year}"
    
    return pd.to_datetime(s, errors="coerce", dayfirst=False)

experience["start_dt"] = experience["start_date"].apply(parse_date)
experience["end_dt"]   = experience["end_date"].apply(parse_date)
experience["years"] = ((experience["end_dt"] - experience["start_dt"])
                       .dt.days / 365.25)
# Drop physically impossible durations instead of clipping —
# clipping would still falsely credit someone with 60 years from a parse bug.
experience.loc[(experience["years"] < 0) | (experience["years"] > 60), "years"] = pd.NA

# diagnose parsing issues: if start_date is parseable but years is NA, it's likely an unparseable end_date or a very long duration
bad = experience[experience["years"].isna() & experience["start_date"].notna()]
print(f"Rows with unparseable or absurd dates: {len(bad)} / {len(experience)}")

print("\n--- sample of bad start_date values ---")
print(bad["start_date"].value_counts().head(30))

print("\n--- sample of bad end_date values ---")
print(bad["end_date"].value_counts().head(30))

exp_agg = (
    experience.groupby("person_id").agg(
        total_years_experience=("years", "sum"),
        num_past_roles=("years", "size"),
        past_titles=("title", lambda s: " | ".join(x.strip() for x in s.dropna().astype(str))),
        past_firms=("firm",   lambda s: " | ".join(x.strip() for x in s.dropna().astype(str))),
    ).reset_index()
)

exp_agg["total_years_experience"] = exp_agg["total_years_experience"].clip(upper=60)

# --- 05 skills: normalize and dedupe ---
SKILL_SYNONYMS = {
    "ms sql server": "sql server", "mssql": "sql server",
    "sklearn": "scikit-learn", "node.js": "nodejs", "react.js": "react",
    "amazon web services": "aws", "google cloud platform": "gcp",
    # extend with what you actually see in the data
}

def normalize_skill(s):
    if not isinstance(s, str): return ""
    s = s.strip().lower()
    s = re.sub(r"\s+\d{4}(\s+r\d)?$", "", s)   # strip "sql server 2008 r2" -> "sql server"
    s = re.sub(r"\s+", " ", s)
    return SKILL_SYNONYMS.get(s, s)

skills["skill_norm"] = skills["skill"].apply(normalize_skill)
skills = skills[skills["skill_norm"].astype(bool)]
skills_agg = (
    skills.drop_duplicates(["person_id", "skill_norm"])
    .groupby("person_id")["skill_norm"]
    .agg(lambda s: "|".join(sorted(set(s))))
    .reset_index().rename(columns={"skill_norm": "skills"})
)
skills_agg["num_skills"] = skills_agg["skills"].str.count(r"\|") + 1

# --- merge ---
resumes = (
    spine
    .merge(abilities_agg, on="person_id", how="left")
    .merge(edu_agg,       on="person_id", how="left")
    .merge(exp_agg,       on="person_id", how="left")
    .merge(skills_agg,    on="person_id", how="left")
)

# fill defaults
defaults = {
    "abilities_text": "", "highest_education": 0,
    "total_years_experience": 0.0, "num_past_roles": 0,
    "past_titles": "", "past_firms": "", "skills": "", "num_skills": 0,
}
resumes = resumes.fillna(defaults)
resumes["highest_education"] = resumes["highest_education"].astype(int)
resumes["num_past_roles"]    = resumes["num_past_roles"].astype(int)
resumes["num_skills"]        = resumes["num_skills"].astype(int)

# text blob for embeddings
resumes["resume_text"] = (
    resumes["past_titles"].str.replace("|", " ", regex=False) + " "
    + resumes["skills"].str.replace("|", " ", regex=False) + " "
    + resumes["abilities_text"]
).str.strip().str.lower()

# add this:
print("\n--- total_years_experience distribution ---")
print(resumes["total_years_experience"].describe())
print("Zeros:", (resumes["total_years_experience"] == 0).sum(), "/", len(resumes))

assert len(resumes) == people["person_id"].nunique(), "row count exploded — a groupby didn't collapse"
# Deduplicate by content. Two rows are considered the same resume if their
# titles, skills, and education are identical. We keep the row with the most
# work experience (proxy for "the more complete copy").
before = len(resumes)
resumes = (
    resumes.sort_values("total_years_experience", ascending=False)
           .drop_duplicates(subset=["past_titles", "skills", "highest_education"],
                            keep="first")
           .reset_index(drop=True)
)
print(f"Deduplicated: {before:,} -> {len(resumes):,} ({before - len(resumes):,} removed)")

resumes.to_csv("resumes_consolidated.csv", index=False)