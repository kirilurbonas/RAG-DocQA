"""Re-ranking service for improved relevance scoring."""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Re-rank search results using cross-encoder model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize cross-encoder reranker.

        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        """Lazily load cross-encoder model."""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            logger.info(f"Loaded cross-encoder model: {self.model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers not available for cross-encoder. "
                "Install with: pip install sentence-transformers"
            )
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            self.model = None

    def rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        Re-rank search results using cross-encoder.

        Args:
            query: Query string
            results: List of search results with 'text' and optionally 'id', 'metadata'
            top_k: Optional limit for re-ranked results

        Returns:
            Re-ranked results sorted by relevance score
        """
        if not self.model or not results:
            logger.warning("Cross-encoder not available or no results, returning original order")
            return results[:top_k] if top_k else results

        try:
            # Prepare pairs for cross-encoder scoring
            pairs = [
                [query, result.get('text', '')]
                for result in results
            ]

            # Score all pairs
            scores = self.model.predict(pairs)

            # Attach scores to results
            scored_results = [
                {**result, 'rerank_score': float(score)}
                for result, score in zip(results, scores)
            ]

            # Sort by rerank score (descending)
            reranked = sorted(
                scored_results,
                key=lambda x: x['rerank_score'],
                reverse=True
            )

            # Return top_k if specified
            if top_k:
                reranked = reranked[:top_k]

            logger.info(f"Re-ranked {len(results)} results, top score: {reranked[0]['rerank_score']:.3f}")
            return reranked
        except Exception as e:
            logger.error(f"Failed to rerank results: {e}")
            return results[:top_k] if top_k else results

    def rerank_by_threshold(
        self,
        query: str,
        results: List[Dict],
        threshold: float = 0.5
    ) -> List[Dict]:
        """
        Filter and re-rank results by relevance threshold.

        Args:
            query: Query string
            results: List of search results
            threshold: Minimum relevance score (0-1)

        Returns:
            Re-ranked and filtered results above threshold
        """
        reranked = self.rerank(query, results)
        filtered = [r for r in reranked if r.get('rerank_score', 0) >= threshold]

        logger.info(
            f"Filtered {len(reranked)} results by threshold {threshold}, "
            f"kept {len(filtered)}"
        )
        return filtered
