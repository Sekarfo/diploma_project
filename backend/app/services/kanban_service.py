from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from backend.app.config import Settings, get_settings
from backend.app.services.db_service import db_connection
from backend.app.services.errors import HistoryNotFoundError, HistoryPersistenceError

# Maps recruiter decision → kanban status
DECISION_TO_KANBAN: dict[str, str] = {
    "accept": "screened",
    "interview": "interview",
    "reject": "rejected",
    "maybe": "new",
}

VALID_STATUSES = ("new", "screened", "interview", "offer", "hired", "rejected")


class KanbanService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def upsert_from_feedback(
        self,
        *,
        user_id: str,
        run_id: str,
        resume_id: str,
        decision: str,
        job_title: str,
        final_rank: int | None,
        score: float | None,
        note: str | None,
        candidate_snapshot: dict[str, Any] | None,
    ) -> str:
        kanban_status = DECISION_TO_KANBAN.get(decision, "new")
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        snapshot_json = json.dumps(candidate_snapshot or {})

        try:
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO kanban_entries (
                            id, user_id, run_id, resume_id, job_title,
                            final_rank, score, kanban_status, note,
                            candidate_snapshot, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                        ON CONFLICT (user_id, run_id, resume_id) DO UPDATE SET
                            kanban_status = EXCLUDED.kanban_status,
                            note          = EXCLUDED.note,
                            updated_at    = EXCLUDED.updated_at
                        RETURNING id
                        """,
                        (
                            entry_id, user_id, run_id, resume_id, job_title,
                            final_rank, score, kanban_status, note,
                            snapshot_json, now, now,
                        ),
                    )
                    row = cur.fetchone()
                    return str(row[0]) if row else entry_id
        except Exception as exc:
            raise HistoryPersistenceError(f"Kanban upsert failed: {exc}") from exc

    def list_board(self, *, user_id: str) -> list[dict[str, Any]]:
        try:
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, run_id, resume_id, job_title, final_rank,
                               score, kanban_status, note, candidate_snapshot,
                               created_at, updated_at
                        FROM kanban_entries
                        WHERE user_id = %s
                        ORDER BY updated_at DESC
                        """,
                        (user_id,),
                    )
                    rows = cur.fetchall()
        except Exception as exc:
            raise HistoryPersistenceError(f"Kanban list failed: {exc}") from exc

        return [
            {
                "id": str(r[0]),
                "run_id": str(r[1]) if r[1] else None,
                "resume_id": str(r[2]),
                "job_title": str(r[3]),
                "final_rank": int(r[4]) if r[4] is not None else None,
                "score": float(r[5]) if r[5] is not None else None,
                "kanban_status": str(r[6]),
                "note": str(r[7]) if r[7] else None,
                "candidate_snapshot": r[8] if r[8] else {},
                "created_at": r[9].isoformat() if r[9] else None,
                "updated_at": r[10].isoformat() if r[10] else None,
            }
            for r in rows
        ]

    def update_status(self, *, user_id: str, entry_id: str, kanban_status: str) -> dict[str, Any]:
        if kanban_status not in VALID_STATUSES:
            raise ValueError(f"Invalid kanban_status: {kanban_status!r}")
        now = datetime.now(timezone.utc)
        try:
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE kanban_entries
                        SET kanban_status = %s, updated_at = %s
                        WHERE id = %s AND user_id = %s
                        RETURNING id, kanban_status, updated_at
                        """,
                        (kanban_status, now, entry_id, user_id),
                    )
                    row = cur.fetchone()
            if row is None:
                raise HistoryNotFoundError(f"Kanban entry not found: {entry_id}")
            return {"id": str(row[0]), "kanban_status": str(row[1]), "updated_at": row[2].isoformat()}
        except (HistoryNotFoundError, ValueError):
            raise
        except Exception as exc:
            raise HistoryPersistenceError(f"Kanban status update failed: {exc}") from exc

    def delete_entry(self, *, user_id: str, entry_id: str) -> bool:
        try:
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM kanban_entries WHERE id = %s AND user_id = %s",
                        (entry_id, user_id),
                    )
                    return cur.rowcount > 0
        except Exception as exc:
            raise HistoryPersistenceError(f"Kanban delete failed: {exc}") from exc


@lru_cache(maxsize=1)
def get_kanban_service() -> KanbanService:
    return KanbanService()
