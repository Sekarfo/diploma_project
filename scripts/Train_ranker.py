from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import ndcg_score
from sklearn.model_selection import GroupShuffleSplit


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "processed" / "dataset_outputs" / "parquet" / "ml_training_template.parquet"
MODEL_PATH = BASE_DIR / "models" / "xgb_ranker.joblib"
FEATURES_PATH = BASE_DIR / "models" / "ranker_features.joblib"

MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)


df = pd.read_parquet(DATA_PATH).copy()


feature_cols = [
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
]

required_cols = feature_cols + ["job_id", "resume_id", "final_label"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")


df = df.dropna(subset=["job_id", "resume_id", "final_label"]).copy()

for col in feature_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df[feature_cols] = df[feature_cols].fillna(0.0)
df["final_label"] = pd.to_numeric(df["final_label"], errors="coerce")

df = df.dropna(subset=["final_label"]).copy()
df["final_label"] = df["final_label"].astype(int)


job_counts = df["job_id"].value_counts()
valid_jobs = job_counts[job_counts >= 2].index
df = df[df["job_id"].isin(valid_jobs)].copy()

if df.empty:
    raise ValueError("No training data left after filtering. Need at least 2 candidates per job.")


label_var_by_job = df.groupby("job_id")["final_label"].nunique()
good_jobs = label_var_by_job[label_var_by_job >= 2].index
df = df[df["job_id"].isin(good_jobs)].copy()

if df.empty:
    raise ValueError("No jobs with label variation. Ranking training needs at least some jobs with multiple relevance labels.")

gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, valid_idx = next(gss.split(df, groups=df["job_id"]))

train_df = df.iloc[train_idx].copy()
valid_df = df.iloc[valid_idx].copy()

# Sort by query group as required for ranking
train_df = train_df.sort_values(["job_id", "retrieval_rank", "resume_id"]).reset_index(drop=True)
valid_df = valid_df.sort_values(["job_id", "retrieval_rank", "resume_id"]).reset_index(drop=True)

# -----------------------------
# Build matrices
# -----------------------------
X_train = train_df[feature_cols]
y_train = train_df["final_label"]

X_valid = valid_df[feature_cols]
y_valid = valid_df["final_label"]

# Group sizes per query/job
group_train = train_df.groupby("job_id").size().to_numpy()
group_valid = valid_df.groupby("job_id").size().to_numpy()

# Safety checks
if group_train.sum() != len(train_df):
    raise ValueError("Train group sizes do not sum to number of training rows.")
if group_valid.sum() != len(valid_df):
    raise ValueError("Valid group sizes do not sum to number of validation rows.")

print("Train rows:", len(train_df))
print("Valid rows:", len(valid_df))
print("Train jobs:", len(group_train))
print("Valid jobs:", len(group_valid))
print("Train label distribution:")
print(train_df["final_label"].value_counts().sort_index())
print("Valid label distribution:")
print(valid_df["final_label"].value_counts().sort_index())

# -----------------------------
# Train ranker
# -----------------------------
model = xgb.XGBRanker(
    objective="rank:ndcg",
    tree_method="hist",
    learning_rate=0.05,
    max_depth=6,
    n_estimators=300,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    random_state=42,
)

model.fit(
    X_train,
    y_train,
    group=group_train,
    eval_set=[(X_valid, y_valid)],
    eval_group=[group_valid],
    verbose=True,
)

# -----------------------------
# Save artifacts
# -----------------------------
joblib.dump(model, MODEL_PATH)
joblib.dump(feature_cols, FEATURES_PATH)

# -----------------------------
# Simple grouped nDCG check
# -----------------------------
valid_df = valid_df.copy()
valid_df["pred"] = model.predict(X_valid)

group_scores = []
for _, group in valid_df.groupby("job_id"):
    if group["final_label"].nunique() > 1:
        true_relevance = group["final_label"].to_numpy().reshape(1, -1)
        pred_scores = group["pred"].to_numpy().reshape(1, -1)
        group_scores.append(ndcg_score(true_relevance, pred_scores))

mean_ndcg = float(np.mean(group_scores)) if group_scores else None
print("Mean grouped nDCG:", mean_ndcg)
print(f"Saved model to: {MODEL_PATH}")
print(f"Saved features to: {FEATURES_PATH}")
