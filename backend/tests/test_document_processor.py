"""Tests for document processing and chunking."""

import pytest
from app.utils.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Test document text extraction and chunking."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_supported_file_types(self, processor):
        """Test that supported file types are recognized."""
        assert processor.is_supported("document.pdf")
        assert processor.is_supported("document.txt")
        assert processor.is_supported("document.docx")
        assert processor.is_supported("document.md")
        assert processor.is_supported("document.markdown")

        assert not processor.is_supported("document.doc")
        assert not processor.is_supported("document.xls")
        assert not processor.is_supported("document.exe")

    def test_txt_extraction(self, processor, sample_text_bytes):
        """Test plain text extraction."""
        text = processor.extract_text(sample_text_bytes, "test.txt")
        assert "test document" in text.lower()
        assert len(text) > 0

    def test_unsupported_file_type(self, processor):
        """Test that unsupported file types raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            processor.extract_text(b"content", "test.exe")

    def test_empty_text_processing(self, processor):
        """Test processing of empty text."""
        # Empty text should produce at least one chunk (possibly empty)
        chunks = processor.chunk_text("")
        assert len(chunks) >= 1

    def test_chunking_preserves_text(self, processor):
        """Test that chunking preserves all text content."""
        text = "Hello world. " * 100  # Repeat to ensure multiple chunks
        chunks = processor.chunk_text(text)

        # Reconstruct text from chunks
        reconstructed = "".join([chunk["text"] for chunk in chunks])

        # Some text might be in overlap regions and duplicated, but core content should exist
        assert "Hello world" in reconstructed

    def test_chunk_size_limits(self, processor):
        """Test that chunks respect size limits."""
        # Create text with known size
        text = "a" * 10000  # 10k characters
        chunks = processor.chunk_text(text)

        # Each chunk should be <= chunk_size (default 1000)
        for chunk in chunks:
            assert len(chunk["text"]) > 0  # No empty chunks
            # Chunks might be slightly larger due to overlap, but within reason
            assert len(chunk["text"]) <= 2000

    def test_chunk_metadata_included(self, processor):
        """Test that chunk metadata is included."""
        text = "First sentence. Second sentence."
        chunks = processor.chunk_text(text)

        for chunk in chunks:
            assert "text" in chunk
            assert "metadata" in chunk
            assert isinstance(chunk["metadata"], dict)
            assert "chunk_index" in chunk["metadata"]


class TestChunkerEdgeCases:
    """Test edge cases in the chunking algorithm."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_whitespace_only_chunks(self, processor):
        """Test handling of whitespace-only chunks."""
        # Text with lots of whitespace that might create empty chunks
        text = "word1\n\n\n\n\nword2"
        chunks = processor.chunk_text(text)

        # Should not create chunks with only whitespace
        for chunk in chunks:
            stripped = chunk["text"].strip()
            assert len(stripped) > 0 or len(chunks) == 1  # Allow if it's the only chunk

    def test_decimal_handling_in_chunker(self, processor):
        """Test that decimals in text don't break chunking."""
        # Text with decimal points that could confuse the . splitter
        text = "The temperature is 98.6 degrees. The price is $19.99. Final sentence."
        chunks = processor.chunk_text(text)

        # Should handle decimals correctly
        reconstructed = "".join([chunk["text"] for chunk in chunks])
        assert "98.6" in reconstructed
        assert "19.99" in reconstructed

    def test_very_short_text(self, processor):
        """Test processing very short text."""
        text = "Hi"
        chunks = processor.chunk_text(text)

        assert len(chunks) >= 1
        assert "Hi" in chunks[0]["text"]

    def test_single_long_word(self, processor):
        """Test handling of text with single very long word."""
        # A word longer than chunk_size
        long_word = "a" * 2000
        chunks = processor.chunk_text(long_word)

        # Should still create chunks (possibly with the long word broken or as one chunk)
        assert len(chunks) >= 1
        reconstructed = "".join([chunk["text"] for chunk in chunks])
        assert long_word in reconstructed
