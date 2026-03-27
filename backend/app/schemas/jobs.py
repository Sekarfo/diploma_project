from __future__ import annotations

from pydantic import BaseModel


class JobSummary(BaseModel):
    job_id: str
    job_title: str
    job_years_required: float
    description_preview: str
    job_skills_norm: list[str]


class JobsResponse(BaseModel):
    jobs: list[JobSummary]


class JobDetailResponse(BaseModel):
    job_id: str
    job_title: str
    job_description: str
    job_years_required: float
    job_skills_norm: list[str]
