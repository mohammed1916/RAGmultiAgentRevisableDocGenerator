"""Cross-encoder reranker for retrieval results.

Reorders vector-search candidates with a cross-encoder that scores each
(query, passage) pair jointly, which is far more accurate than the bi-encoder
cosine similarity used for the first-stage recall. The model is loaded lazily so
importing this module is cheap and does not require network access.
"""

from typing import Any, Dict, List, Optional

from ...base.logger import setup_logger

logger = setup_logger(__name__)

_DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker:
    """Rerank retrieval candidates by cross-encoder relevance score."""

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model = None
        self._unavailable = False

    def _load(self) -> None:
        if self._model is not None or self._unavailable:
            return
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
            logger.info("Reranker loaded: %s", self.model_name)
        except Exception as error:
            logger.warning("Reranker unavailable (%s); returning vector order", error)
            self._unavailable = True

    @property
    def available(self) -> bool:
        self._load()
        return self._model is not None

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
        content_key: str = "content",
    ) -> List[Dict[str, Any]]:
        """Return the ``top_k`` candidates ordered by cross-encoder relevance.

        Each returned item gets a ``rerank_score`` field. If the model cannot be
        loaded, the original vector-search order is preserved (truncated to
        ``top_k``) rather than fabricating scores.
        """
        if not candidates:
            return []
        self._load()
        if self._model is None:
            return candidates[:top_k]

        pairs = [(query, candidate.get(content_key, "") or "") for candidate in candidates]
        scores = self._model.predict(pairs)
        for candidate, score in zip(candidates, scores):
            candidate["rerank_score"] = float(score)
        reranked = sorted(candidates, key=lambda item: item["rerank_score"], reverse=True)
        return reranked[:top_k]
