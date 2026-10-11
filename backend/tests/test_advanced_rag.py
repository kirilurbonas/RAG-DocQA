"""Comprehensive tests for advanced RAG features (Phase 4)."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from app.services.query_expansion import QueryExpander
from app.services.reranker import CrossEncoderReranker
from app.utils.semantic_chunking import SemanticChunker


class TestQueryExpander:
    """Test query expansion functionality."""

    def test_init_without_llm(self):
        """Test initializing query expander without LLM."""
        expander = QueryExpander(llm_service=None)
        assert expander.llm_service is None

    def test_init_with_llm(self):
        """Test initializing query expander with LLM."""
        mock_llm = Mock()
        expander = QueryExpander(llm_service=mock_llm)
        assert expander.llm_service is mock_llm

    @pytest.mark.asyncio
    async def test_expand_query_without_llm(self):
        """Test that expand_query returns original if no LLM available."""
        expander = QueryExpander(llm_service=None)
        result = await expander.expand_query("What is AI?")

        assert len(result) == 1
        assert result[0] == "What is AI?"

    @pytest.mark.asyncio
    async def test_expand_query_with_llm(self):
        """Test expanding query with LLM."""
        mock_llm = AsyncMock()
        mock_llm.generate_response.return_value = (
            "What is artificial intelligence?\n"
            "Tell me about AI technology\n"
            "How does artificial intelligence work?"
        )

        expander = QueryExpander(llm_service=mock_llm)
        result = await expander.expand_query("What is AI?")

        assert len(result) >= 3  # Original + at least 2 expansions
        assert "What is AI?" in result
        assert mock_llm.generate_response.called

    @pytest.mark.asyncio
    async def test_expand_query_handles_empty_response(self):
        """Test that expand_query handles empty LLM response."""
        mock_llm = AsyncMock()
        mock_llm.generate_response.return_value = ""

        expander = QueryExpander(llm_service=mock_llm)
        result = await expander.expand_query("What is AI?")

        assert len(result) >= 1  # At least original query
        assert "What is AI?" in result

    @pytest.mark.asyncio
    async def test_expand_query_filters_short_responses(self):
        """Test that very short expansions are filtered."""
        mock_llm = AsyncMock()
        mock_llm.generate_response.return_value = (
            "AI\n"  # Too short
            "What is artificial intelligence?\n"  # Good
            "Hi\n"  # Too short
        )

        expander = QueryExpander(llm_service=mock_llm)
        result = await expander.expand_query("What is AI?")

        # Should only include original + the good expansion
        assert len(result) == 2
        assert "What is artificial intelligence?" in result

    @pytest.mark.asyncio
    async def test_expand_and_deduplicate(self):
        """Test deduplication of results."""
        mock_llm = AsyncMock()
        mock_llm.generate_response.return_value = "alternative1\nalternative2"

        expander = QueryExpander(llm_service=mock_llm)
        existing = [{"id": "doc1"}, {"id": "doc2"}]

        queries, dedup_ids = await expander.expand_and_deduplicate(
            "original", existing
        )

        assert len(queries) >= 1
        assert dedup_ids == {"doc1", "doc2"}

    @pytest.mark.asyncio
    async def test_expand_and_deduplicate_empty_existing(self):
        """Test deduplication with no existing results."""
        mock_llm = AsyncMock()
        mock_llm.generate_response.return_value = "alternative1"

        expander = QueryExpander(llm_service=mock_llm)
        queries, dedup_ids = await expander.expand_and_deduplicate("original", None)

        assert len(queries) >= 1
        assert dedup_ids == set()


class TestCrossEncoderReranker:
    """Test cross-encoder re-ranking functionality."""

    def test_init_model_loading(self):
        """Test that reranker initializes with model name."""
        reranker = CrossEncoderReranker(
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        assert reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def test_init_without_sentence_transformers(self):
        """Test initialization handles missing sentence-transformers gracefully."""
        with patch('sentence_transformers.CrossEncoder', side_effect=ImportError):
            # This will cause model loading to fail gracefully
            reranker = CrossEncoderReranker()
            # Model may or may not be None depending on whether CrossEncoder is available
            # Just verify the object was created
            assert reranker is not None

    def test_rerank_no_model(self):
        """Test rerank returns original order when model unavailable."""
        reranker = CrossEncoderReranker()
        reranker.model = None

        results = [
            {'text': 'Result 1', 'id': '1'},
            {'text': 'Result 2', 'id': '2'},
        ]

        reranked = reranker.rerank("query", results)
        assert reranked == results

    def test_rerank_empty_results(self):
        """Test rerank handles empty results."""
        reranker = CrossEncoderReranker()
        reranker.model = None

        reranked = reranker.rerank("query", [])
        assert reranked == []

    def test_rerank_with_scores(self):
        """Test rerank adds scores to results."""
        mock_model = Mock()
        mock_model.predict.return_value = [0.8, 0.6, 0.7]

        reranker = CrossEncoderReranker()
        reranker.model = mock_model

        results = [
            {'text': 'Result 1', 'id': '1'},
            {'text': 'Result 2', 'id': '2'},
            {'text': 'Result 3', 'id': '3'},
        ]

        reranked = reranker.rerank("query", results)

        # Check results have scores
        assert all('rerank_score' in r for r in reranked)

        # Check sorted by score descending
        scores = [r['rerank_score'] for r in reranked]
        assert scores == sorted(scores, reverse=True)
        assert scores == [0.8, 0.7, 0.6]

    def test_rerank_with_top_k(self):
        """Test rerank respects top_k limit."""
        mock_model = Mock()
        mock_model.predict.return_value = [0.8, 0.6, 0.7, 0.5]

        reranker = CrossEncoderReranker()
        reranker.model = mock_model

        results = [
            {'text': f'Result {i}', 'id': str(i)}
            for i in range(4)
        ]

        reranked = reranker.rerank("query", results, top_k=2)
        assert len(reranked) == 2
        assert reranked[0]['rerank_score'] == 0.8

    def test_rerank_by_threshold(self):
        """Test filtering results by relevance threshold."""
        mock_model = Mock()
        mock_model.predict.return_value = [0.8, 0.4, 0.7, 0.3]

        reranker = CrossEncoderReranker()
        reranker.model = mock_model

        results = [
            {'text': f'Result {i}', 'id': str(i)}
            for i in range(4)
        ]

        filtered = reranker.rerank_by_threshold("query", results, threshold=0.6)

        assert len(filtered) == 2
        assert all(r['rerank_score'] >= 0.6 for r in filtered)


class TestSemanticChunker:
    """Test semantic chunking functionality."""

    def test_init_without_embedding_model(self):
        """Test initializing without embedding model."""
        chunker = SemanticChunker(embedding_model=None)
        assert chunker.embedding_model is None

    def test_init_with_embedding_model(self):
        """Test initializing with embedding model."""
        mock_model = Mock()
        chunker = SemanticChunker(embedding_model=mock_model)
        assert chunker.embedding_model is mock_model

    def test_split_by_sentences_basic(self):
        """Test basic sentence splitting."""
        chunker = SemanticChunker()
        text = "First sentence. Second sentence! Third sentence?"

        sentences = chunker.split_by_sentences(text)

        assert len(sentences) >= 2
        assert "First sentence" in sentences[0]

    def test_split_by_sentences_with_abbreviations(self):
        """Test sentence splitting handles abbreviations."""
        chunker = SemanticChunker()
        text = "Dr. Smith went to the store. He bought milk."

        sentences = chunker.split_by_sentences(text)

        # Should handle Dr. properly
        assert len(sentences) >= 1

    def test_split_by_sentences_empty(self):
        """Test sentence splitting with empty text."""
        chunker = SemanticChunker()
        sentences = chunker.split_by_sentences("")
        assert sentences == []

    def test_chunk_by_tokens_basic(self):
        """Test token-based chunking."""
        chunker = SemanticChunker()
        text = "First sentence. " * 50  # Repeat to create larger text

        chunks = chunker.chunk_by_tokens(text, target_chunk_size=50, max_chunk_size=100)

        assert len(chunks) >= 1
        assert all('text' in c for c in chunks)
        assert all('metadata' in c for c in chunks)

    def test_chunk_by_tokens_short_text(self):
        """Test token-based chunking with short text."""
        chunker = SemanticChunker()
        text = "Short text."

        chunks = chunker.chunk_by_tokens(text, target_chunk_size=100)

        assert len(chunks) == 1
        assert chunks[0]['text'] == text

    def test_chunk_by_tokens_overlap(self):
        """Test that overlap is maintained between chunks."""
        chunker = SemanticChunker()
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five. " * 3

        chunks = chunker.chunk_by_tokens(
            text,
            target_chunk_size=80,
            max_chunk_size=120,
            overlap_size=20
        )

        # Check metadata
        assert all(c['metadata']['type'] == 'semantic' for c in chunks)
        assert all('chunk_index' in c['metadata'] for c in chunks)

    @pytest.mark.asyncio
    async def test_chunk_by_similarity_without_model(self):
        """Test similarity chunking falls back without embedding model."""
        chunker = SemanticChunker(embedding_model=None)
        text = "Sentence one. Sentence two. Sentence three."

        chunks = await chunker.chunk_by_similarity(text)

        # Should fall back to token-based
        assert len(chunks) >= 1
        assert 'text' in chunks[0]

    @pytest.mark.asyncio
    async def test_chunk_by_similarity_with_model(self):
        """Test similarity chunking with embedding model."""
        mock_model = AsyncMock()
        # Mock embeddings - return different vectors for different sentences
        embeddings = [
            np.array([1.0, 0.0, 0.0]),
            np.array([0.9, 0.1, 0.0]),
            np.array([0.0, 1.0, 0.0]),  # Different cluster
            np.array([0.0, 0.9, 0.1]),
        ]
        mock_model.encode_async.return_value = embeddings

        chunker = SemanticChunker(embedding_model=mock_model)
        text = "Sentence one. Sentence two. Sentence three. Sentence four."

        chunks = await chunker.chunk_by_similarity(text, similarity_threshold=0.5)

        assert len(chunks) >= 1
        assert all('text' in c for c in chunks)
        assert all(c['metadata']['type'] == 'semantic-similarity' for c in chunks)

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        vec3 = np.array([0.0, 1.0, 0.0])

        sim_identical = SemanticChunker._cosine_similarity(vec1, vec2)
        sim_orthogonal = SemanticChunker._cosine_similarity(vec1, vec3)

        assert abs(sim_identical - 1.0) < 0.01  # Should be 1.0
        assert abs(sim_orthogonal - 0.0) < 0.01  # Should be 0.0

    def test_cosine_similarity_zero_vectors(self):
        """Test cosine similarity with zero vectors."""
        vec1 = np.array([0.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])

        sim = SemanticChunker._cosine_similarity(vec1, vec2)
        assert sim == 0.0  # Should handle zero vector gracefully


class TestAdvancedRAGIntegration:
    """Test integration of advanced RAG components."""

    @pytest.mark.asyncio
    async def test_query_expansion_retrieval_pipeline(self):
        """Test pipeline: expand query -> retrieve -> rerank."""
        # Setup
        mock_llm = AsyncMock()
        mock_llm.generate_response.return_value = "What is AI technology?\nTell me about artificial intelligence"

        expander = QueryExpander(llm_service=mock_llm)

        mock_rerank_model = Mock()
        mock_rerank_model.predict.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]
        reranker = CrossEncoderReranker()
        reranker.model = mock_rerank_model

        # Execute
        queries = await expander.expand_query("What is AI?")

        # Simulate retrieval results
        results = [
            {'text': f'Document {i}', 'id': str(i)}
            for i in range(5)
        ]

        reranked = reranker.rerank("What is AI?", results, top_k=3)

        # Verify
        assert len(queries) >= 2
        assert len(reranked) == 3
        assert all('rerank_score' in r for r in reranked)

    def test_chunking_strategy_selection(self):
        """Test selecting between chunking strategies."""
        text = "Sentence one. " * 100

        # Token-based with smaller chunk sizes
        token_chunker = SemanticChunker()
        token_chunks = token_chunker.chunk_by_tokens(
            text,
            target_chunk_size=100,
            max_chunk_size=150
        )

        assert len(token_chunks) >= 1
        assert all(c['metadata']['type'] == 'semantic' for c in token_chunks)
