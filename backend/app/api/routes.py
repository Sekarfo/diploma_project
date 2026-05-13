from __future__ import annotations

import logging
import time
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.schemas import (
    AuthMeResponse,
    AuthResponse,
    GlobalModelExplanationResponse,
    HistoryDetailResponse,
    HistoryListResponse,
    JobDetailResponse,
    JobsResponse,
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
    HistoryService,
    ShortlistService,
    get_auth_service,
    get_current_user,
    get_history_service,
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

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, **checks}


@router.post("/auth/signup", response_model=AuthResponse)
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
        try:
            history_service.record_existing_job_shortlist(
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
        return ShortlistResponse(**result)
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
        try:
            history_service.record_custom_vacancy_shortlist(
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
        return VacancyShortlistResponse(**result)
    except Exception as exc:
        logger.exception("POST /shortlist/vacancy failed user_id=%s: %s", current_user.user_id, exc)
        raise _map_error_to_http(exc) from exc

