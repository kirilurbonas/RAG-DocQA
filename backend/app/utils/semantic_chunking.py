"""Semantic-aware chunking for better document segmentation."""

from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Segment documents semantically based on sentence boundaries and embeddings."""

    def __init__(self, embedding_model=None):
        """
        Initialize semantic chunker.

        Args:
            embedding_model: Optional embedding model for similarity-based splitting
        """
        self.embedding_model = embedding_model

    def split_by_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences intelligently.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Split by periods, question marks, exclamation marks
        # But be careful with abbreviations and numbers
        pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(pattern, text)

        # Filter out empty sentences and strip whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def chunk_by_tokens(
        self,
        text: str,
        target_chunk_size: int = 500,
        max_chunk_size: int = 1000,
        overlap_size: int = 100
    ) -> List[Dict[str, any]]:
        """
        Chunk text by token-like units (words + sentences).

        Args:
            text: Text to chunk
            target_chunk_size: Target approximate chunk size in characters
            max_chunk_size: Maximum chunk size in characters
            overlap_size: Overlap size in characters

        Returns:
            List of chunks with metadata
        """
        sentences = self.split_by_sentences(text)

        if not sentences:
            return [{'text': text, 'metadata': {'chunk_index': 0, 'type': 'semantic'}}]

        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        overlap_text = ""

        for sentence in sentences:
            sentence_size = len(sentence) + 1  # +1 for space

            # If adding this sentence would exceed max, finalize current chunk
            if current_size + sentence_size > max_chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    'text': chunk_text.strip(),
                    'metadata': {
                        'chunk_index': chunk_index,
                        'type': 'semantic',
                        'sentence_count': len(current_chunk)
                    }
                })

                # Prepare overlap for next chunk
                overlap_text = chunk_text[-overlap_size:] if len(chunk_text) > overlap_size else chunk_text
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(overlap_text) + 1
                chunk_index += 1

            # Add sentence if we haven't reached target size yet, or if chunk is empty
            if current_size < target_chunk_size or not current_chunk:
                current_chunk.append(sentence)
                current_size += sentence_size

        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                'text': chunk_text.strip(),
                'metadata': {
                    'chunk_index': chunk_index,
                    'type': 'semantic',
                    'sentence_count': len(current_chunk)
                }
            })

        logger.info(f"Created {len(chunks)} semantic chunks from {len(sentences)} sentences")
        return chunks

    async def chunk_by_similarity(
        self,
        text: str,
        target_chunk_size: int = 500,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, any]]:
        """
        Chunk text by detecting semantic boundaries using embeddings.

        Args:
            text: Text to chunk
            target_chunk_size: Target chunk size in characters
            similarity_threshold: Minimum similarity to keep sentences together

        Returns:
            List of chunks with semantic boundaries
        """
        if not self.embedding_model:
            logger.warning("Embedding model not available, using token-based chunking")
            return self.chunk_by_tokens(text, target_chunk_size=target_chunk_size)

        sentences = self.split_by_sentences(text)

        if len(sentences) < 2:
            return [{'text': text, 'metadata': {'chunk_index': 0, 'type': 'semantic'}}]

        try:
            # Embed all sentences
            embeddings = await self.embedding_model.encode_async(sentences)

            # Find boundaries where similarity drops below threshold
            chunks = []
            current_chunk = [sentences[0]]
            current_size = len(sentences[0])
            chunk_index = 0

            for i in range(1, len(sentences)):
                sentence = sentences[i]
                sentence_size = len(sentence)

                # Calculate similarity with previous sentence
                similarity = self._cosine_similarity(embeddings[i], embeddings[i-1])

                # Check if we should break
                should_break = (
                    current_size + sentence_size > target_chunk_size and similarity < similarity_threshold
                ) or current_size > target_chunk_size * 2

                if should_break and current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunks.append({
                        'text': chunk_text.strip(),
                        'metadata': {
                            'chunk_index': chunk_index,
                            'type': 'semantic-similarity',
                            'sentence_count': len(current_chunk)
                        }
                    })
                    current_chunk = [sentence]
                    current_size = sentence_size
                    chunk_index += 1
                else:
                    current_chunk.append(sentence)
                    current_size += sentence_size + 1

            # Add final chunk
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    'text': chunk_text.strip(),
                    'metadata': {
                        'chunk_index': chunk_index,
                        'type': 'semantic-similarity',
                        'sentence_count': len(current_chunk)
                    }
                })

            logger.info(
                f"Created {len(chunks)} similarity-based chunks from {len(sentences)} sentences"
            )
            return chunks
        except Exception as e:
            logger.error(f"Failed to create similarity-based chunks: {e}")
            return self.chunk_by_tokens(text, target_chunk_size=target_chunk_size)

    @staticmethod
    def _cosine_similarity(vec1, vec2) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        vec1 = np.array(vec1).flatten()
        vec2 = np.array(vec2).flatten()

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
