from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any

import numpy as np

from backend.app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class CrossEncoderService:
    """Wraps a sentence-transformers CrossEncoder for runtime feature generation.

    Used by `FeatureBuilderService` to populate the `ce_score` column on retrieved
    candidates. The score is sigmoid-mapped to [0, 1] so the runtime distribution
    matches the offline labels produced by `data/generate_labels.py`.
    """

    def __init__(self, model_name: str, max_length: int, device: str | None = None) -> None:
        try:
            import torch  # type: ignore
            from sentence_transformers import CrossEncoder  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Cross-encoder dependencies missing. Install torch + sentence-transformers."
            ) from exc

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(
            "Loading cross-encoder model=%s device=%s max_length=%s",
            model_name, device, max_length,
        )
        self._model = CrossEncoder(model_name, max_length=max_length, device=device)
        self._device = device
        self._max_length = max_length
        self._model_name = model_name

    @property
    def device(self) -> str:
        return self._device

    @property
    def model_name(self) -> str:
        return self._model_name

    def score_pairs(
        self,
        pairs: list[tuple[str, str]],
        batch_size: int = 64,
        progress_cb: Callable[[int, int], Any] | None = None,
    ) -> np.ndarray:
        if not pairs:
            return np.zeros(0, dtype=np.float32)

        total = len(pairs)
        all_scores: list[np.ndarray] = []

        for start in range(0, total, batch_size):
            batch = [[j, r] for j, r in pairs[start: start + batch_size]]
            raw_batch = self._model.predict(
                batch,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            all_scores.append(np.asarray(raw_batch, dtype=np.float64))
            if progress_cb is not None:
                progress_cb(min(start + batch_size, total), total)

        raw_arr = np.concatenate(all_scores)

        if raw_arr.min() < -0.01 or raw_arr.max() > 1.01:
            clipped = np.clip(raw_arr, -50.0, 50.0)
            raw_arr = 1.0 / (1.0 + np.exp(-clipped))

        return raw_arr.astype(np.float32)


@lru_cache(maxsize=1)
def get_cross_encoder_service(settings: Settings | None = None) -> CrossEncoderService:
    s = settings or get_settings()
    return CrossEncoderService(
        model_name=s.cross_encoder_model,
        max_length=s.cross_encoder_max_length,
    )
