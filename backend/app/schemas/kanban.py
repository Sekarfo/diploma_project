from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class KanbanEntry(BaseModel):
    id: str
    run_id: str | None
    resume_id: str
    job_title: str
    final_rank: int | None
    score: float | None
    kanban_status: str
    note: str | None
    candidate_snapshot: dict[str, Any]
    created_at: str | None
    updated_at: str | None


class KanbanBoardResponse(BaseModel):
    entries: list[KanbanEntry]


class KanbanStatusUpdate(BaseModel):
    kanban_status: str


class KanbanStatusResponse(BaseModel):
    id: str
    kanban_status: str
    updated_at: str
