from __future__ import annotations


class ArtifactLoadError(RuntimeError):
    """Raised when required runtime artifacts cannot be loaded."""


class JobNotFoundError(ValueError):
    """Raised when the requested job_id does not exist in loaded artifacts."""


class ElasticsearchUnavailableError(RuntimeError):
    """Raised when Elasticsearch cannot be reached or queried."""


class EmptyRetrievalError(RuntimeError):
    """Raised when retrieval returns no candidates."""


class RankingError(RuntimeError):
    """Raised when ranking cannot be completed."""


class AuthenticationError(ValueError):
    """Raised when credentials or auth token are invalid."""


class AuthorizationError(ValueError):
    """Raised when a user is authenticated but not allowed to perform action."""


class DatabaseUnavailableError(RuntimeError):
    """Raised when PostgreSQL is unavailable or misconfigured."""


class HistoryPersistenceError(RuntimeError):
    """Raised when shortlist history cannot be persisted or fetched."""


class HistoryNotFoundError(ValueError):
    """Raised when requested history run does not belong to current user or does not exist."""
