from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from elasticsearch import Elasticsearch

from backend.app.config import Settings, get_settings
from backend.app.services.errors import ElasticsearchUnavailableError
from backend.app.services.runtime_utils import parse_list_col, to_float

logger = logging.getLogger(__name__)


class ElasticsearchRetrievalService:
    """Retrieves top-K candidate resumes from Elasticsearch kNN index."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _connect(self) -> Elasticsearch:
        kwargs: dict[str, Any] = {
            "hosts": [self.settings.elasticsearch_url],
            "request_timeout": 60,
            "verify_certs": False,
        }
        if self.settings.elasticsearch_username and self.settings.elasticsearch_password:
            kwargs["basic_auth"] = (
                self.settings.elasticsearch_username,
                self.settings.elasticsearch_password,
            )

        try:
            client = Elasticsearch(**kwargs)
            if not client.ping():
                raise ElasticsearchUnavailableError(
                    f"Could not connect to Elasticsearch at {self.settings.elasticsearch_url}"
                )
            return client
        except ElasticsearchUnavailableError:
            raise
        except Exception as exc:
            raise ElasticsearchUnavailableError(
                f"Elasticsearch connection failed: {exc}"
            ) from exc

    def retrieve_hits(
        self,
        *,
        query_vector: np.ndarray,
        top_k: int,
        num_candidates: int,
        index_name: str | None = None,
    ) -> list[dict[str, Any]]:
        index = index_name or self.settings.elasticsearch_index_name

        try:
            client = self._connect()
            response = client.search(
                index=index,
                knn={
                    "field": "embedding",
                    "query_vector": query_vector.tolist(),
                    "k": top_k,
                    "num_candidates": max(num_candidates, top_k),
                },
                _source=[
                    "resume_id",
                    "resume_text",
                    "resume_skills_norm",
                    "resume_titles_norm",
                    "resume_years_experience",
                ],
                size=top_k,
            )
            hits = response.get("hits", {}).get("hits", [])
            for hit in hits:
                hit["retrieval_score_raw"] = to_float(hit.get("_score", 0.0), default=0.0)
            logger.info("Elasticsearch retrieval completed: %s hits", len(hits))
            return hits
        except ElasticsearchUnavailableError:
            raise
        except Exception as exc:
            raise ElasticsearchUnavailableError(f"Elasticsearch query failed: {exc}") from exc

    @staticmethod
    def retrieve_hits_from_csv(retrieved_csv: Path, top_k: int) -> list[dict[str, Any]]:
        df = pd.read_csv(retrieved_csv).copy()
        if "resume_id" not in df.columns:
            raise ValueError(f"retrieved csv is missing required column resume_id: {retrieved_csv}")
        if "retrieval_rank" not in df.columns:
            df["retrieval_rank"] = np.arange(1, len(df) + 1)

        df["retrieval_rank"] = pd.to_numeric(df["retrieval_rank"], errors="coerce").fillna(999999)
        df = df.sort_values("retrieval_rank", ascending=True).head(top_k).reset_index(drop=True)

        hits: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            hits.append(
                {
                    "_score": to_float(row.get("elastic_score", 0.0), default=0.0),
                    "retrieval_score_raw": to_float(row.get("elastic_score", 0.0), default=0.0),
                    "_source": {
                        "resume_id": str(row.get("resume_id", "")),
                        "resume_text": str(row.get("resume_text", "")),
                        "resume_skills_norm": parse_list_col(row.get("resume_skills_norm", [])),
                        "resume_titles_norm": parse_list_col(row.get("resume_titles_norm", [])),
                        "resume_years_experience": to_float(row.get("resume_years_experience", 0.0), default=0.0),
                    },
                }
            )
        return hits
