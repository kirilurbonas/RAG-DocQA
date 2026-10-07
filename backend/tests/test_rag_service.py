"""Tests for RAG service functionality."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock
from app.services.rag_service import RAGService


class TestDocumentPersistence:
    """Test document registry persistence."""

    @pytest.mark.asyncio
    async def test_document_registry_persists(self, temp_vector_store, sample_text_bytes, mock_openai):
        """Test that document registry is saved to disk."""
        service = RAGService(vector_store_path=temp_vector_store)

        # Upload a document
        doc_info = await service.process_and_store_document_async(
            file_content=sample_text_bytes,
            filename="test.txt",
            owner_id="test-owner"
        )

        # Verify registry file exists
        registry_path = Path(temp_vector_store) / "document_registry.json"
        assert registry_path.exists()

        # Verify content
        with open(registry_path, 'r') as f:
            registry = json.load(f)

        assert doc_info["id"] in registry
        assert registry[doc_info["id"]]["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_document_registry_loads_on_startup(self, temp_vector_store, sample_text_bytes, mock_openai):
        """Test that document registry is loaded on service startup."""
        # Create first service and upload document
        service1 = RAGService(vector_store_path=temp_vector_store)
        doc_info = await service1.process_and_store_document_async(
            file_content=sample_text_bytes,
            filename="test.txt",
            owner_id="test-owner"
        )
        doc_id = doc_info["id"]

        # Create second service (simulating restart)
        service2 = RAGService(vector_store_path=temp_vector_store)

        # Verify document is still there
        documents = service2.get_documents(owner_id="test-owner")
        assert len(documents) == 1
        assert documents[0]["id"] == doc_id
        assert documents[0]["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_delete_updates_registry(self, temp_vector_store, sample_text_bytes, mock_openai):
        """Test that deleting a document updates the registry."""
        service = RAGService(vector_store_path=temp_vector_store)

        # Upload document
        doc_info = await service.process_and_store_document_async(
            file_content=sample_text_bytes,
            filename="test.txt",
            owner_id="test-owner"
        )
        doc_id = doc_info["id"]

        # Delete document
        success = service.delete_document(doc_id, owner_id="test-owner")
        assert success

        # Verify registry is updated
        registry_path = Path(temp_vector_store) / "document_registry.json"
        with open(registry_path, 'r') as f:
            registry = json.load(f)

        assert doc_id not in registry


class TestDocumentOwnershipIsolation:
    """Test that document ownership is properly enforced."""

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_documents(self, temp_vector_store, sample_text_bytes, mock_openai):
        """Test that users can only see their own documents."""
        service = RAGService(vector_store_path=temp_vector_store)

        # User 1 uploads a document
        doc1 = await service.process_and_store_document_async(
            file_content=sample_text_bytes,
            filename="user1_doc.txt",
            owner_id="user-1"
        )

        # User 2 uploads a document
        doc2 = await service.process_and_store_document_async(
            file_content=sample_text_bytes,
            filename="user2_doc.txt",
            owner_id="user-2"
        )

        # User 1 should only see their document
        user1_docs = service.get_documents(owner_id="user-1")
        assert len(user1_docs) == 1
        assert user1_docs[0]["id"] == doc1["id"]

        # User 2 should only see their document
        user2_docs = service.get_documents(owner_id="user-2")
        assert len(user2_docs) == 1
        assert user2_docs[0]["id"] == doc2["id"]

    @pytest.mark.asyncio
    async def test_cannot_delete_other_users_document(self, temp_vector_store, sample_text_bytes, mock_openai):
        """Test that a user cannot delete another user's document."""
        service = RAGService(vector_store_path=temp_vector_store)

        # User 1 uploads a document
        doc = await service.process_and_store_document_async(
            file_content=sample_text_bytes,
            filename="user1_doc.txt",
            owner_id="user-1"
        )

        # User 2 tries to delete User 1's document
        success = service.delete_document(doc["id"], owner_id="user-2")
        assert not success  # Should fail

        # Document should still exist for User 1
        user1_docs = service.get_documents(owner_id="user-1")
        assert len(user1_docs) == 1


class TestUnsupportedFileTypes:
    """Test handling of unsupported file types."""

    @pytest.mark.asyncio
    async def test_unsupported_file_type_raises_error(self, temp_vector_store):
        """Test that unsupported file types are rejected."""
        service = RAGService(vector_store_path=temp_vector_store)

        with pytest.raises(ValueError, match="Unsupported file type"):
            await service.process_and_store_document_async(
                file_content=b"content",
                filename="test.exe",
                owner_id="test-owner"
            )
