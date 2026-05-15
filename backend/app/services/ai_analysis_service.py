from __future__ import annotations

import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Generator

from backend.app.config import Settings, get_settings
from backend.app.config.settings import _load_env_file
from backend.app.services.db_service import db_connection

logger = logging.getLogger(__name__)

# Matches "Recommendation: interview Candidate #N first." with tolerance for
# stray markdown asterisks, surrounding whitespace, and minor punctuation
# variants that small 8B models occasionally emit (e.g. "Candidate 1", "Cand. #1").
_RECOMMENDATION_PATTERN = re.compile(
    r"\**\s*Recommendation:\s*interview\s+(?:Candidate\s*#?\s*)?(\d)\s*(?:first)?\.?\s*\**",
    re.IGNORECASE,
)


def _normalize_compare_verdict(text: str) -> str:
    """Ensure compare-mode output ends with the canonical recommendation line.

    Llama 3.1 8B occasionally wraps the line in markdown bold (`**Recommendation:
    ...**`), drops the candidate number, or buries it mid-paragraph. We strip
    all matches, then re-append the cleanest version found, so the frontend can
    reliably regex it.
    """
    if not text:
        return text

    matches = list(_RECOMMENDATION_PATTERN.finditer(text))
    if not matches:
        return text.rstrip()

    # Use the LAST candidate digit the model produced — that's the verdict.
    final_digit = matches[-1].group(1)
    canonical = f"Recommendation: interview Candidate #{final_digit} first."

    # Strip every recommendation-like fragment from the body, then append the
    # canonical line on its own paragraph.
    body = _RECOMMENDATION_PATTERN.sub("", text).rstrip(" \t\n*.").rstrip()
    return f"{body}\n\n{canonical}" if body else canonical

# Prompts are deliberately strict: HR users want consistent structure across runs,
# and a small 8B model needs explicit "do X for each candidate" instructions to
# avoid skipping cases or wandering off-format.

_EXPLAIN_SYSTEM = (
    "You are a senior HR analyst. You receive 3 candidate cards with structured "
    "ML signals (matched skills, missing skills, experience gap, score). Your job: "
    "produce one independent assessment per candidate. Do not compare candidates "
    "against each other in this mode. Write in plain prose, no markdown headers, "
    "no bullets. Be direct and concrete; refer to specific skills and numbers from "
    "the candidate card. Keep each assessment 3-4 sentences."
)

_COMPARE_SYSTEM = (
    "You are a senior HR analyst. You receive 3 candidate cards with structured "
    "ML signals. Your job: directly compare these three candidates against the "
    "vacancy requirements and pick the single best fit. Write in plain prose, no "
    "markdown headers, no bullets, no asterisks. Refer to specific skills and "
    "experience numbers when comparing.\n\n"
    "CRITICAL FORMAT RULE — read carefully:\n"
    "The VERY LAST line of your response MUST be exactly this template, "
    "with no markdown, no extra punctuation, no surrounding text:\n"
    "Recommendation: interview Candidate #N first.\n"
    "Replace #N with the digit of the best candidate (1, 2 or 3). "
    "This sentence must appear once, at the end, on its own line."
)


def _format_candidate_block(cand: dict[str, Any], index: int) -> str:
    expl = cand.get("explanation") or {}
    feat = cand.get("feature_snapshot") or {}
    rank = cand.get("final_rank", index)
    score = cand.get("final_fusion_score", 0.0)

    matched = expl.get("matched_skills") or feat.get("matched_skills") or []
    missing = expl.get("missing_skills") or feat.get("missing_skills") or []
    exp_summary = expl.get("experience_summary") or ""

    pos_factors = expl.get("top_positive_factors") or []
    neg_factors = expl.get("top_negative_factors") or []

    yrs_exp = feat.get("resume_years_experience")
    yrs_req = feat.get("job_years_required")
    skill_ratio = feat.get("skill_overlap_ratio")

    lines: list[str] = [f"Candidate #{rank}  (score: {score*100:.1f}%)"]
    if yrs_exp is not None and yrs_req is not None:
        lines.append(f"  Experience: {yrs_exp:.1f} yrs  (required: {yrs_req:.1f} yrs)")
    if skill_ratio is not None:
        lines.append(f"  Skill coverage: {skill_ratio*100:.0f}%")
    if matched:
        lines.append(f"  Matched skills: {', '.join(matched[:8])}")
    if missing:
        lines.append(f"  Missing skills: {', '.join(missing[:6])}")
    if exp_summary:
        lines.append(f"  {exp_summary}")
    if pos_factors:
        labels = ", ".join(f["label"] for f in pos_factors[:3])
        lines.append(f"  Strengths: {labels}")
    if neg_factors:
        labels = ", ".join(f["label"] for f in neg_factors[:2])
        lines.append(f"  Weaknesses: {labels}")

    return "\n".join(lines)


def _build_explain_prompt(
    job_title: str,
    job_description: str,
    candidates: list[dict[str, Any]],
) -> str:
    blocks = [_format_candidate_block(c, i + 1) for i, c in enumerate(candidates)]
    joined = "\n\n".join(blocks)
    desc_preview = (job_description or "")[:400].strip()
    count = len(candidates)
    return (
        f"Vacancy: {job_title}\n"
        f"Description: {desc_preview}\n\n"
        f"Top {count} candidates (independent assessment for each):\n\n"
        f"{joined}\n\n"
        f"For EACH of the {count} candidates above, write exactly one paragraph "
        f"(3-4 sentences) covering:\n"
        f"  1) what the candidate has — matched skills, relevant experience;\n"
        f"  2) what is missing relative to the vacancy — gaps in skills or years;\n"
        f"  3) one concrete suggestion: what they could improve or what to verify "
        f"in the interview.\n"
        f"Start every paragraph with the literal label \"Candidate #1:\", "
        f"\"Candidate #2:\", \"Candidate #3:\" so the output is parseable. "
        f"Do not compare candidates with each other in this mode."
    )


def _build_compare_prompt(
    job_title: str,
    job_description: str,
    candidates: list[dict[str, Any]],
) -> str:
    blocks = [_format_candidate_block(c, i + 1) for i, c in enumerate(candidates)]
    joined = "\n\n".join(blocks)
    desc_preview = (job_description or "")[:400].strip()
    count = len(candidates)
    return (
        f"Vacancy: {job_title}\n"
        f"Description: {desc_preview}\n\n"
        f"Top {count} candidates to compare head-to-head:\n\n"
        f"{joined}\n\n"
        f"Compare these {count} candidates directly against the vacancy "
        f"requirements above. In 4-6 sentences, name which candidate best matches "
        f"the requirements and why, referencing specific skills, experience years "
        f"and gaps from the cards. Then briefly state the second-best and why the "
        f"others fall behind.\n\n"
        f"Then add a blank line and finish with EXACTLY this final line and "
        f"nothing after it (no period changes, no extra words, no asterisks):\n"
        f"Recommendation: interview Candidate #N first.\n"
        f"Substitute #N with the digit (1, 2, or 3) of the candidate you just "
        f"named as the best match."
    )


class AIAnalysisService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    # ── OpenRouter / OpenAI-compatible client ────────────────────────────────

    def _get_client(self):
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "openai SDK not installed. Run: pip install openai"
            ) from exc

        api_key = self.settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            env_path = Path(__file__).resolve().parents[3] / ".env"
            if env_path.exists():
                _load_env_file(env_path)
                api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OpenRouter_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Add it to your .env file at the project root "
                "and restart the backend (settings are cached at startup)."
            )

        return OpenAI(
            api_key=api_key,
            base_url=self.settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": self.settings.ai_app_url,
                "X-Title": self.settings.ai_app_title,
            },
        )

    # ── Persistence ──────────────────────────────────────────────────────────

    @staticmethod
    def get_cached_analysis(*, run_id: str, mode: str) -> dict[str, Any] | None:
        try:
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, model, content, tokens_estimate, created_at
                        FROM ai_analyses
                        WHERE run_id = %s AND mode = %s
                        LIMIT 1
                        """,
                        (run_id, mode),
                    )
                    row = cur.fetchone()
        except Exception as exc:
            logger.warning("AI cache lookup failed (run_id=%s mode=%s): %s", run_id, mode, exc)
            return None
        if row is None:
            return None
        return {
            "id": str(row[0]),
            "model": str(row[1]),
            "content": str(row[2]),
            "tokens_estimate": int(row[3]) if row[3] is not None else None,
            "created_at": row[4].isoformat() if row[4] else None,
        }

    @staticmethod
    def list_for_run(*, run_id: str) -> dict[str, dict[str, Any]]:
        """Return all stored analyses for a run keyed by mode ({'explain': {...}, 'compare': {...}})."""
        out: dict[str, dict[str, Any]] = {}
        try:
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT mode, model, content, tokens_estimate, created_at
                        FROM ai_analyses
                        WHERE run_id = %s
                        """,
                        (run_id,),
                    )
                    for mode, model, content, tokens, created_at in cur.fetchall():
                        out[str(mode)] = {
                            "model": str(model),
                            "content": str(content),
                            "tokens_estimate": int(tokens) if tokens is not None else None,
                            "created_at": created_at.isoformat() if created_at else None,
                        }
        except Exception as exc:
            logger.warning("AI list_for_run failed (run_id=%s): %s", run_id, exc)
        return out

    def _save_analysis(
        self,
        *,
        run_id: str,
        user_id: str,
        mode: str,
        content: str,
    ) -> None:
        # Approximate token usage (~4 chars/token for English). Good enough for
        # quota/cost dashboards without pulling exact usage from the API.
        tokens_estimate = max(1, len(content) // 4)
        try:
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ai_analyses (id, run_id, user_id, mode, model, content, tokens_estimate)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (run_id, mode) DO UPDATE SET
                            content = EXCLUDED.content,
                            tokens_estimate = EXCLUDED.tokens_estimate,
                            model = EXCLUDED.model,
                            created_at = now()
                        """,
                        (
                            str(uuid.uuid4()),
                            run_id,
                            user_id,
                            mode,
                            self.settings.ai_model,
                            content,
                            tokens_estimate,
                        ),
                    )
        except Exception as exc:
            logger.warning("AI analysis save failed (run_id=%s mode=%s): %s", run_id, mode, exc)

    # ── Streaming ────────────────────────────────────────────────────────────

    def stream_analysis(
        self,
        *,
        mode: str,
        run_id: str,
        user_id: str,
        run_detail: dict[str, Any],
    ) -> Generator[str, None, None]:
        # Cache check: if this run already has a saved analysis for this mode,
        # replay it from DB instead of hitting the LLM again. This is the
        # backend half of the "one-click" guard the user asked for.
        cached = self.get_cached_analysis(run_id=run_id, mode=mode)
        if cached is not None:
            yield _sse("text", cached["content"])
            yield _sse("done", "")
            return

        top_k = self.settings.ai_analysis_top_k
        candidates = sorted(
            run_detail.get("candidates", []),
            key=lambda c: c.get("final_rank", 999),
        )[:top_k]

        if not candidates:
            yield _sse("error", "No candidates found for this run.")
            return

        job_title = (
            run_detail.get("vacancy_title")
            or run_detail.get("request_payload", {}).get("vacancy_title")
            or run_detail.get("existing_job_id")
            or "Unknown vacancy"
        )
        job_description = (
            run_detail.get("vacancy_description")
            or run_detail.get("request_payload", {}).get("vacancy_description")
            or ""
        )

        if mode == "compare":
            system = _COMPARE_SYSTEM
            prompt = _build_compare_prompt(job_title, job_description, candidates)
        else:
            system = _EXPLAIN_SYSTEM
            prompt = _build_explain_prompt(job_title, job_description, candidates)

        try:
            client = self._get_client()
        except RuntimeError as exc:
            yield _sse("error", str(exc))
            return

        full_text_chunks: list[str] = []
        try:
            stream = client.chat.completions.create(
                model=self.settings.ai_model,
                max_tokens=self.settings.ai_max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )
            for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", None) or ""
                if text:
                    full_text_chunks.append(text)
                    yield _sse("text", text)
            full_text = "".join(full_text_chunks).strip()
            # For compare mode we enforce the canonical verdict line so the
            # frontend can reliably bold it. If the model already produced a
            # clean line, _normalize_compare_verdict is a no-op rewrite.
            if mode == "compare" and full_text:
                normalized = _normalize_compare_verdict(full_text)
                if normalized != full_text:
                    full_text = normalized
                    # Tell the frontend to replace the streamed buffer with the
                    # canonical version — picks up after `text` events.
                    yield _sse("replace", full_text)
            if full_text:
                self._save_analysis(
                    run_id=run_id,
                    user_id=user_id,
                    mode=mode,
                    content=full_text,
                )
            yield _sse("done", "")
        except Exception as exc:
            logger.exception("AI analysis streaming failed: %s", exc)
            yield _sse("error", str(exc))


def _sse(event: str, data: str) -> str:
    payload = json.dumps({"type": event, "text": data})
    return f"data: {payload}\n\n"
