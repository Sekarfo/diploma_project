from __future__ import annotations

import asyncio
import json
import logging
import time
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from backend.app.schemas import (
    AuthMeResponse,
    AuthResponse,
    FairnessReport,
    FeedbackListResponse,
    FeedbackRequest,
    FeedbackResponse,
    GlobalModelExplanationResponse,
    HistoryDetailResponse,
    HistoryListResponse,
    JobDetailResponse,
    JobsResponse,
    KanbanBoardResponse,
    KanbanStatusResponse,
    KanbanStatusUpdate,
    ParsedVacancyResponse,
    RuntimeStatsResponse,
    ShortlistRequest,
    ShortlistResponse,
    SignInRequest,
    SignOutResponse,
    SignUpRequest,
    StatsResponse,
    VacancyListResponse,
    VacancyShortlistRequest,
    VacancyShortlistResponse,
)
from backend.app.limiter import limiter
from backend.app.services import (
    AuthenticatedUser,
    AuthService,
    FairnessService,
    HistoryService,
    KanbanService,
    ShortlistService,
    get_auth_service,
    get_current_user,
    get_fairness_service,
    get_history_service,
    get_kanban_service,
    get_model_explanation_service,
    get_runtime_metrics_service,
)
from backend.app.services.db_service import db_connection
from backend.app.services.errors import (
    ArtifactLoadError,
    AuthenticationError,
    DatabaseUnavailableError,
    ElasticsearchUnavailableError,
    EmptyRetrievalError,
    HistoryNotFoundError,
    HistoryPersistenceError,
    JobNotFoundError,
    RankingError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@lru_cache(maxsize=1)
def get_shortlist_service() -> ShortlistService:
    return ShortlistService()


def _model_to_dict(model_obj) -> dict:
    if hasattr(model_obj, "model_dump"):
        return model_obj.model_dump()
    return model_obj.dict()


def _map_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, AuthenticationError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    if isinstance(exc, JobNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, HistoryNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, EmptyRetrievalError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ElasticsearchUnavailableError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, (DatabaseUnavailableError,)):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, (ArtifactLoadError, RankingError, FileNotFoundError, HistoryPersistenceError)):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unexpected server error: {exc}",
    )


@router.get("/health")
def health() -> dict:
    checks: dict[str, str] = {}

    # Database check
    try:
        with db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("Health check: database unavailable — %s", exc)
        checks["database"] = "unavailable"

    # ML artifacts check
    try:
        get_shortlist_service().artifact_service.get_artifacts()
        checks["artifacts"] = "ok"
    except Exception as exc:
        logger.warning("Health check: artifacts unavailable — %s", exc)
        checks["artifacts"] = "unavailable"

    # Cross-encoder device probe — does NOT trigger model load.
    # Reports the actual loaded device if the CE singleton is already warm,
    # otherwise reports what device the next load would pick.
    ce_info: dict[str, Any] = {"loaded": False}
    try:
        import torch  # type: ignore
        ce_info["cuda_available"] = bool(torch.cuda.is_available())
        if ce_info["cuda_available"]:
            ce_info["cuda_device_name"] = torch.cuda.get_device_name(0)
    except Exception as exc:
        logger.warning("Health check: torch probe failed — %s", exc)
        ce_info["cuda_available"] = False

    try:
        from backend.app.services.cross_encoder_service import get_cross_encoder_service
        cache_info = get_cross_encoder_service.cache_info()
        if cache_info.currsize > 0:
            svc = get_cross_encoder_service()
            ce_info["loaded"] = True
            ce_info["device"] = svc.device
            ce_info["model"] = svc.model_name
    except Exception as exc:
        logger.warning("Health check: cross-encoder probe failed — %s", exc)

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, **checks, "cross_encoder": ce_info}


@router.post("/auth/signup", response_model=AuthResponse)
@limiter.limit("10/minute")
def signup(payload: SignUpRequest, request: Request) -> AuthResponse:
    logger.info("POST /auth/signup request started email=%s", payload.email)
    try:
        service: AuthService = get_auth_service()
        result = service.signup(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return AuthResponse(**result)
    except Exception as exc:
        logger.exception("POST /auth/signup failed email=%s: %s", payload.email, exc)
        raise _map_error_to_http(exc) from exc


@router.post("/auth/signin", response_model=AuthResponse)
def signin(payload: SignInRequest, request: Request) -> AuthResponse:
    logger.info("POST /auth/signin request started email=%s", payload.email)
    try:
        service: AuthService = get_auth_service()
        result = service.signin(
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return AuthResponse(**result)
    except Exception as exc:
        logger.exception("POST /auth/signin failed email=%s: %s", payload.email, exc)
        raise _map_error_to_http(exc) from exc


@router.get("/auth/me", response_model=AuthMeResponse)
def auth_me(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthMeResponse:
    return AuthMeResponse(
        id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.post("/auth/signout", response_model=SignOutResponse)
def signout(request: Request, current_user: AuthenticatedUser = Depends(get_current_user)) -> SignOutResponse:
    del current_user
    auth_header = str(request.headers.get("authorization", ""))
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    try:
        service: AuthService = get_auth_service()
        service.signout(token)
        return SignOutResponse(status="signed_out")
    except Exception as exc:
        logger.exception("POST /auth/signout failed: %s", exc)
        raise _map_error_to_http(exc) from exc


@router.get("/cabinet/history", response_model=HistoryListResponse)
def list_history(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> HistoryListResponse:
    logger.info("GET /cabinet/history request started user_id=%s limit=%s", current_user.user_id, limit)
    try:
        runs = history_service.list_history(user_id=current_user.user_id, limit=limit)
        return HistoryListResponse(runs=runs)
    except Exception as exc:
        logger.exception("GET /cabinet/history failed user_id=%s: %s", current_user.user_id, exc)
        raise _map_error_to_http(exc) from exc


@router.get("/cabinet/history/{run_id}", response_model=HistoryDetailResponse)
def get_history_detail(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> HistoryDetailResponse:
    logger.info("GET /cabinet/history/%s request started user_id=%s", run_id, current_user.user_id)
    try:
        detail = history_service.get_run_detail(user_id=current_user.user_id, run_id=run_id)
        return HistoryDetailResponse(**detail)
    except Exception as exc:
        logger.exception(
            "GET /cabinet/history/%s failed user_id=%s: %s",
            run_id,
            current_user.user_id,
            exc,
        )
        raise _map_error_to_http(exc) from exc


@router.get("/cabinet/vacancies", response_model=VacancyListResponse)
def list_vacancies(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> VacancyListResponse:
    logger.info("GET /cabinet/vacancies request started user_id=%s limit=%s", current_user.user_id, limit)
    try:
        vacancies = history_service.list_vacancies(user_id=current_user.user_id, limit=limit)
        return VacancyListResponse(vacancies=vacancies)
    except Exception as exc:
        logger.exception("GET /cabinet/vacancies failed user_id=%s: %s", current_user.user_id, exc)
        raise _map_error_to_http(exc) from exc


@router.get("/jobs", response_model=JobsResponse)
def list_jobs() -> JobsResponse:
    logger.info("GET /jobs request started")
    try:
        service = get_shortlist_service()
        jobs = service.list_jobs()
        return JobsResponse(jobs=jobs)
    except Exception as exc:
        logger.exception("GET /jobs failed: %s", exc)
        raise _map_error_to_http(exc) from exc


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str) -> JobDetailResponse:
    logger.info("GET /jobs/%s request started", job_id)
    try:
        service = get_shortlist_service()
        job = service.get_job(job_id=job_id)
        return JobDetailResponse(**job)
    except Exception as exc:
        logger.exception("GET /jobs/%s failed: %s", job_id, exc)
        raise _map_error_to_http(exc) from exc


@router.get("/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    logger.info("GET /stats request started")
    try:
        service = get_shortlist_service()
        stats = service.get_stats()
        return StatsResponse(**stats)
    except Exception as exc:
        logger.exception("GET /stats failed: %s", exc)
        raise _map_error_to_http(exc) from exc


@router.get("/stats/runtime", response_model=RuntimeStatsResponse)
def get_runtime_stats() -> RuntimeStatsResponse:
    logger.info("GET /stats/runtime request started")
    try:
        metrics_service = get_runtime_metrics_service()
        return RuntimeStatsResponse(**metrics_service.snapshot())
    except Exception as exc:
        logger.exception("GET /stats/runtime failed: %s", exc)
        raise _map_error_to_http(exc) from exc


@router.get("/stats/explanations/global", response_model=GlobalModelExplanationResponse)
def get_global_model_explanation() -> GlobalModelExplanationResponse:
    logger.info("GET /stats/explanations/global request started")
    try:
        service = get_model_explanation_service()
        return GlobalModelExplanationResponse(**service.get_global_explanation())
    except Exception as exc:
        logger.exception("GET /stats/explanations/global failed: %s", exc)
        raise _map_error_to_http(exc) from exc


@router.get("/stats/fairness", response_model=FairnessReport)
def get_fairness_report(
    group_by: str = Query(default="experience_bucket"),
    top_k_cutoff: int = Query(default=10, ge=1, le=200),
    run_id: str | None = Query(default=None),
    limit_runs: int = Query(default=200, ge=1, le=1000),
    current_user: AuthenticatedUser = Depends(get_current_user),
    fairness_service: FairnessService = Depends(get_fairness_service),
) -> FairnessReport:
    """Group-level selection-rate / score / feedback audit over historical runs.

    Supported `group_by` values: experience_bucket, experience_match, skill_overlap_bucket.
    When `run_id` is omitted, aggregates over the user's recent runs (capped by limit_runs).
    """
    logger.info(
        "GET /stats/fairness user_id=%s group_by=%s top_k=%s run_id=%s",
        current_user.user_id, group_by, top_k_cutoff, run_id,
    )
    try:
        report = fairness_service.compute(
            user_id=current_user.user_id,
            group_by=group_by,
            top_k_cutoff=top_k_cutoff,
            run_id=run_id,
            limit_runs=limit_runs,
        )
        return FairnessReport(**report)
    except Exception as exc:
        logger.exception(
            "GET /stats/fairness failed user_id=%s: %s", current_user.user_id, exc
        )
        raise _map_error_to_http(exc) from exc


@router.post("/shortlist", response_model=ShortlistResponse)
@limiter.limit("20/minute")
def shortlist(
    request: Request,
    payload: ShortlistRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> ShortlistResponse:
    logger.info(
        "POST /shortlist request started user_id=%s job_id=%s top_k=%s num_candidates=%s",
        current_user.user_id,
        payload.job_id,
        payload.top_k,
        payload.num_candidates,
    )
    started = time.perf_counter()
    try:
        service = get_shortlist_service()
        result = service.shortlist(
            job_id=payload.job_id,
            top_k=payload.top_k,
            num_candidates=payload.num_candidates,
        )
        latency_ms = int((time.perf_counter() - started) * 1000.0)
        run_id: str | None = None
        try:
            run_id = history_service.record_existing_job_shortlist(
                user_id=current_user.user_id,
                request_payload=_model_to_dict(payload),
                result_payload=result,
                latency_ms=latency_ms,
            )
        except Exception as history_exc:
            logger.warning(
                "POST /shortlist history persistence skipped user_id=%s job_id=%s: %s",
                current_user.user_id,
                payload.job_id,
                history_exc,
            )
        logger.info(
            "POST /shortlist completed user_id=%s job_id=%s retrieved=%s ranked=%s",
            current_user.user_id,
            payload.job_id,
            result["retrieved_count"],
            result["total_candidates"],
        )
        return ShortlistResponse(**result, run_id=run_id)
    except Exception as exc:
        logger.exception("POST /shortlist failed user_id=%s job_id=%s: %s", current_user.user_id, payload.job_id, exc)
        raise _map_error_to_http(exc) from exc


@router.post("/shortlist/vacancy", response_model=VacancyShortlistResponse)
@limiter.limit("20/minute")
def shortlist_for_vacancy(
    request: Request,
    payload: VacancyShortlistRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> VacancyShortlistResponse:
    logger.info(
        "POST /shortlist/vacancy request started user_id=%s title=%s top_k=%s num_candidates=%s",
        current_user.user_id,
        payload.vacancy_title,
        payload.top_k,
        payload.num_candidates,
    )
    started = time.perf_counter()
    try:
        service = get_shortlist_service()
        result = service.shortlist_for_vacancy(
            vacancy_title=payload.vacancy_title,
            vacancy_description=payload.vacancy_description,
            top_k=payload.top_k,
            num_candidates=payload.num_candidates,
            job_years_required=payload.job_years_required,
            job_skills_norm=payload.job_skills_norm,
        )
        latency_ms = int((time.perf_counter() - started) * 1000.0)
        run_id: str | None = None
        try:
            run_id = history_service.record_custom_vacancy_shortlist(
                user_id=current_user.user_id,
                request_payload=_model_to_dict(payload),
                result_payload=result,
                latency_ms=latency_ms,
            )
        except Exception as history_exc:
            logger.warning(
                "POST /shortlist/vacancy history persistence skipped user_id=%s title=%s: %s",
                current_user.user_id,
                payload.vacancy_title,
                history_exc,
            )
        logger.info(
            "POST /shortlist/vacancy completed user_id=%s retrieved=%s ranked=%s proxy_job=%s",
            current_user.user_id,
            result["retrieved_count"],
            result["total_candidates"],
            result["proxy_job_id"],
        )
        return VacancyShortlistResponse(**result, run_id=run_id)
    except Exception as exc:
        logger.exception("POST /shortlist/vacancy failed user_id=%s: %s", current_user.user_id, exc)
        raise _map_error_to_http(exc) from exc


# Feedback endpoints 

@router.post("/shortlist/{run_id}/feedback", response_model=FeedbackResponse)
@limiter.limit("60/minute")
def submit_feedback(
    request: Request,
    run_id: str,
    payload: FeedbackRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> FeedbackResponse:
    logger.info(
        "POST /shortlist/%s/feedback user_id=%s rank=%s decision=%s",
        run_id, current_user.user_id, payload.final_rank, payload.decision,
    )
    try:
        result = history_service.submit_feedback(
            user_id=current_user.user_id,
            run_id=run_id,
            final_rank=payload.final_rank,
            decision=payload.decision,
            rating=payload.rating,
            note=payload.note,
        )
        return FeedbackResponse(**result)
    except Exception as exc:
        logger.exception("POST /shortlist/%s/feedback failed: %s", run_id, exc)
        raise _map_error_to_http(exc) from exc


@router.delete("/shortlist/{run_id}/feedback/{final_rank}", status_code=204)
def delete_feedback(
    run_id: str,
    final_rank: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> None:
    logger.info(
        "DELETE /shortlist/%s/feedback/%s user_id=%s", run_id, final_rank, current_user.user_id
    )
    try:
        history_service.delete_feedback(
            user_id=current_user.user_id,
            run_id=run_id,
            final_rank=final_rank,
        )
    except Exception as exc:
        logger.exception("DELETE /shortlist/%s/feedback/%s failed: %s", run_id, final_rank, exc)
        raise _map_error_to_http(exc) from exc


@router.get("/shortlist/{run_id}/feedback", response_model=FeedbackListResponse)
def get_run_feedback(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> FeedbackListResponse:
    logger.info(
        "GET /shortlist/%s/feedback user_id=%s", run_id, current_user.user_id
    )
    try:
        feedbacks = history_service.list_run_feedback(
            user_id=current_user.user_id,
            run_id=run_id,
        )
        return FeedbackListResponse(run_id=run_id, feedbacks=feedbacks)
    except Exception as exc:
        logger.exception("GET /shortlist/%s/feedback failed: %s", run_id, exc)
        raise _map_error_to_http(exc) from exc


#  Vacancy file parser

@router.post("/vacancies/parse", response_model=ParsedVacancyResponse)
@limiter.limit("20/minute")
async def parse_vacancy_file(
    request: Request,
    file: UploadFile,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ParsedVacancyResponse:
    """
    Upload a PDF or DOCX vacancy file.
    Returns extracted title, description, years_required and skills.
    The caller should review the fields and pass them to POST /shortlist/vacancy.
    """
    logger.info(
        "POST /vacancies/parse user_id=%s filename=%s content_type=%s size=%s",
        current_user.user_id,
        file.filename,
        file.content_type,
        file.size,
    )
    from backend.app.services.vacancy_parser_service import VacancyParserService
    svc = VacancyParserService()
    try:
        content = await file.read()
        result = svc.parse(
            content=content,
            file_name=file.filename or "upload",
            content_type=file.content_type or "",
        )
        return ParsedVacancyResponse(
            title=result.title,
            description=result.description,
            years_required=result.years_required,
            skills=result.skills,
            file_name=result.file_name,
            char_count=result.char_count,
            page_count=result.page_count,
            parse_warnings=result.parse_warnings,
        )
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("POST /vacancies/parse failed user_id=%s: %s", current_user.user_id, exc)
        raise HTTPException(status_code=500, detail=f"File parsing failed: {exc}") from exc


# ── Kanban pipeline ──────────────────────────────────────────────────────────

@router.get("/kanban", response_model=KanbanBoardResponse)
def get_kanban_board(
    current_user: AuthenticatedUser = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service),
) -> KanbanBoardResponse:
    logger.info("GET /kanban user_id=%s", current_user.user_id)
    try:
        entries = kanban_service.list_board(user_id=current_user.user_id)
        return KanbanBoardResponse(entries=entries)
    except Exception as exc:
        logger.exception("GET /kanban failed user_id=%s: %s", current_user.user_id, exc)
        raise _map_error_to_http(exc) from exc


@router.patch("/kanban/{entry_id}/status", response_model=KanbanStatusResponse)
def update_kanban_status(
    entry_id: str,
    payload: KanbanStatusUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service),
) -> KanbanStatusResponse:
    logger.info("PATCH /kanban/%s/status user_id=%s status=%s",
                entry_id, current_user.user_id, payload.kanban_status)
    try:
        result = kanban_service.update_status(
            user_id=current_user.user_id,
            entry_id=entry_id,
            kanban_status=payload.kanban_status,
        )
        return KanbanStatusResponse(**result)
    except Exception as exc:
        logger.exception("PATCH /kanban/%s/status failed: %s", entry_id, exc)
        raise _map_error_to_http(exc) from exc


@router.delete("/kanban/{entry_id}", status_code=204)
def delete_kanban_entry(
    entry_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    kanban_service: KanbanService = Depends(get_kanban_service),
) -> None:
    logger.info("DELETE /kanban/%s user_id=%s", entry_id, current_user.user_id)
    try:
        kanban_service.delete_entry(user_id=current_user.user_id, entry_id=entry_id)
    except Exception as exc:
        logger.exception("DELETE /kanban/%s failed: %s", entry_id, exc)
        raise _map_error_to_http(exc) from exc


# ── AI candidate analysis (SSE) ──────────────────────────────────────────────

@router.get("/shortlist/{run_id}/ai-analysis")
def ai_analysis(
    run_id: str,
    mode: str = Query(default="explain", pattern="^(explain|compare)$"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> StreamingResponse:
    """Stream AI-generated candidate analysis as SSE.

    mode=explain  — individual assessment for each of the top 3 candidates.
    mode=compare  — head-to-head comparison with a single hiring recommendation.

    Per-user rate limit: 5 requests / 3 minutes. Repeated calls with the same
    (run_id, mode) replay the cached DB copy and do not count toward the limit.
    """
    from backend.app.services.ai_analysis_service import AIAnalysisService
    from backend.app.services.ai_rate_limit import ai_analysis_limiter

    logger.info(
        "GET /shortlist/%s/ai-analysis mode=%s user_id=%s",
        run_id, mode, current_user.user_id,
    )

    # If we already have a saved analysis, replay it from DB. This is free,
    # not counted toward the rate limit, and gives the frontend a fast path
    # for re-opening completed analyses.
    cached = AIAnalysisService.get_cached_analysis(run_id=run_id, mode=mode)
    if cached is None:
        decision = ai_analysis_limiter.check(current_user.user_id)
        if not decision.allowed:
            retry = max(1, int(decision.retry_after_seconds))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"AI analysis rate limit reached (5 requests / 3 minutes). "
                    f"Try again in {retry} seconds."
                ),
                headers={"Retry-After": str(retry)},
            )

    try:
        run_detail = history_service.get_run_detail(
            user_id=current_user.user_id,
            run_id=run_id,
        )
    except Exception as exc:
        raise _map_error_to_http(exc) from exc

    svc = AIAnalysisService()
    return StreamingResponse(
        svc.stream_analysis(
            mode=mode,
            run_id=run_id,
            user_id=current_user.user_id,
            run_detail=run_detail,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/shortlist/{run_id}/ai-analyses")
def list_ai_analyses(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    """Return all stored AI analyses for a run, keyed by mode.

    Used by the frontend to restore previously-generated explain/compare panels
    when the user reopens a shortlist from history.
    """
    from backend.app.services.ai_analysis_service import AIAnalysisService

    # Ownership check — get_run_detail raises HistoryNotFoundError if the run
    # doesn't belong to this user, preventing cross-user analysis leaks.
    try:
        history_service.get_run_detail(user_id=current_user.user_id, run_id=run_id)
    except Exception as exc:
        raise _map_error_to_http(exc) from exc

    return {"run_id": run_id, "analyses": AIAnalysisService.list_for_run(run_id=run_id)}


# ── WebSocket shortlist with real-time progress ──────────────────────────────

@router.websocket("/ws/shortlist")
async def ws_shortlist(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    await websocket.accept()
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    # Authenticate via token query param
    try:
        auth_svc = get_auth_service()
        current_user = auth_svc.get_user_from_token(token)
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": f"Unauthorized: {exc}"})
        await websocket.close(code=4001)
        return

    # Receive request params
    try:
        params = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
    except Exception:
        await websocket.send_json({"type": "error", "message": "Expected JSON params."})
        await websocket.close(code=4000)
        return

    def _progress_cb(event: dict) -> None:
        asyncio.run_coroutine_threadsafe(queue.put(event), loop)

    svc = get_shortlist_service()
    history_service = get_history_service()
    request_kind = params.get("type", "existing_job")

    def _run_pipeline() -> dict:
        if request_kind == "custom_vacancy":
            return svc.shortlist_for_vacancy(
                vacancy_title=str(params.get("vacancy_title", "")),
                vacancy_description=str(params.get("vacancy_description", "")),
                top_k=params.get("top_k"),
                num_candidates=params.get("num_candidates"),
                job_years_required=params.get("job_years_required"),
                job_skills_norm=params.get("job_skills_norm"),
                progress_cb=_progress_cb,
            )
        return svc.shortlist(
            job_id=str(params.get("job_id", "")),
            top_k=params.get("top_k"),
            num_candidates=params.get("num_candidates"),
            progress_cb=_progress_cb,
        )

    # Run blocking pipeline in thread pool
    future = loop.run_in_executor(None, _run_pipeline)

    # Stream progress events while pipeline runs
    try:
        while not future.done():
            try:
                event = await asyncio.wait_for(asyncio.shield(
                    asyncio.ensure_future(queue.get())
                ), timeout=0.1)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                future.cancel()
                return

        # Drain remaining queued events
        while not queue.empty():
            await websocket.send_json(queue.get_nowait())

        result = await future
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
        return

    # Persist to history (best-effort)
    run_id: str | None = None
    try:
        latency_ms = 0
        if request_kind == "custom_vacancy":
            run_id = history_service.record_custom_vacancy_shortlist(
                user_id=current_user.user_id,
                request_payload=params,
                result_payload=result,
                latency_ms=latency_ms,
            )
        else:
            run_id = history_service.record_existing_job_shortlist(
                user_id=current_user.user_id,
                request_payload=params,
                result_payload=result,
                latency_ms=latency_ms,
            )
    except Exception as hist_exc:
        logger.warning("WS /ws/shortlist history persistence skipped: %s", hist_exc)

    await websocket.send_json({"type": "done", "result": result, "run_id": run_id})
    await websocket.close()

