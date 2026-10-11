"""Query expansion for improved RAG retrieval."""

from typing import List, Optional, AsyncIterator
import logging

logger = logging.getLogger(__name__)


class QueryExpander:
    """Expand queries using LLM to generate paraphrases and related questions."""

    EXPANSION_PROMPT = """Generate 3 alternative phrasings of this question that would help find the same information in documents.
Each phrasing should be a complete, natural question. Do not number them or add explanations.
Return only the questions, one per line.

Original question: {question}

Alternative questions:"""

    def __init__(self, llm_service=None):
        """
        Initialize query expander.

        Args:
            llm_service: LLM service instance for generating expansions
        """
        self.llm_service = llm_service

    async def expand_query(self, query: str) -> List[str]:
        """
        Expand a query into paraphrases using LLM.

        Args:
            query: Original query string

        Returns:
            List of alternative query formulations including original
        """
        if not self.llm_service:
            logger.warning("LLM service not available for query expansion, using original query only")
            return [query]

        try:
            prompt = self.EXPANSION_PROMPT.format(question=query)

            # Generate expansions with empty context (no RAG context needed)
            expansion_text = await self.llm_service.generate_response(
                query=prompt,
                context=[],
                conversation_history=None
            )

            # Parse expansions - expect one per line, filter empty lines
            expanded_queries = [
                q.strip()
                for q in expansion_text.split('\n')
                if q.strip() and len(q.strip()) > 10
            ]

            # Include original query
            queries = [query] + expanded_queries

            logger.info(f"Expanded query into {len(queries)} variants")
            return queries
        except Exception as e:
            logger.error(f"Failed to expand query: {e}")
            return [query]

    async def expand_and_deduplicate(
        self, query: str, existing_results: Optional[List[dict]] = None
    ) -> tuple:
        """
        Expand query and track coverage of existing results.

        Args:
            query: Original query
            existing_results: Existing search results to deduplicate against

        Returns:
            Tuple of (expanded_queries, dedup_ids)
        """
        queries = await self.expand_query(query)

        dedup_ids = set()
        if existing_results:
            for result in existing_results:
                dedup_ids.add(result.get('id'))

        return queries, dedup_ids
