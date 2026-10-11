"""Tests for database-backed services (Phase 2E)."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from app.db.models import Base, Document, Conversation, Message
from app.services.db_rag_service import DbDocumentService
from app.services.db_conversation_service import DbConversationService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


class TestDbDocumentService:
    """Test database document service."""

    def test_create_document(self, db_session):
        """Test creating a document."""
        service = DbDocumentService(db_session)
        doc_id = str(uuid4())
        owner_id = "user123"

        result = service.create_document(
            document_id=doc_id,
            owner_id=owner_id,
            filename="test.pdf",
            chunk_count=10,
            text_length=5000,
            version=1
        )

        assert result["id"] == doc_id
        assert result["filename"] == "test.pdf"
        assert result["chunk_count"] == 10
        assert result["text_length"] == 5000
        assert result["version"] == 1
        assert result["is_latest"] is True

    def test_list_documents_filtering(self, db_session):
        """Test listing documents with filtering."""
        service = DbDocumentService(db_session)
        owner1 = "user1"
        owner2 = "user2"

        # Create documents for user1
        service.create_document(str(uuid4()), owner1, "doc1.pdf", 5, 1000)
        service.create_document(str(uuid4()), owner1, "doc2.txt", 3, 500)

        # Create documents for user2
        service.create_document(str(uuid4()), owner2, "doc3.pdf", 2, 200)

        # List user1's documents
        docs = service.list_documents(owner_id=owner1, latest_only=True)
        assert len(docs) == 2
        assert all(d["owner_id"] == owner1 for d in docs)

    def test_list_documents_search(self, db_session):
        """Test searching documents by filename."""
        service = DbDocumentService(db_session)
        owner = "user123"

        service.create_document(str(uuid4()), owner, "budget2024.pdf", 10, 5000)
        service.create_document(str(uuid4()), owner, "report2024.docx", 8, 4000)
        service.create_document(str(uuid4()), owner, "invoice.pdf", 2, 100)

        # Search for documents containing "2024"
        results = service.list_documents(owner, search_query="2024")
        assert len(results) == 2
        assert all("2024" in d["filename"] for d in results)

    def test_document_versioning(self, db_session):
        """Test document version tracking."""
        service = DbDocumentService(db_session)
        owner = "user123"
        filename = "report.pdf"

        # Create v1
        doc1_id = str(uuid4())
        service.create_document(doc1_id, owner, filename, 5, 1000, version=1)

        # Create v2 - should mark v1 as not latest
        doc2_id = str(uuid4())
        service.create_document(doc2_id, owner, filename, 6, 1200, version=2)

        # Get all versions
        all_versions = service.get_documents_by_filename(owner, filename)
        assert len(all_versions) == 2

        # Latest should be v2
        latest = [d for d in all_versions if d["is_latest"]]
        assert len(latest) == 1
        assert latest[0]["version"] == 2

    def test_get_document_ownership_check(self, db_session):
        """Test that users can only access their own documents."""
        service = DbDocumentService(db_session)
        doc_id = str(uuid4())

        service.create_document(doc_id, "user1", "private.pdf", 5, 1000)

        # User1 can access
        doc = service.get_document(doc_id, "user1")
        assert doc is not None
        assert doc["owner_id"] == "user1"

        # User2 cannot access
        doc = service.get_document(doc_id, "user2")
        assert doc is None

    def test_delete_document(self, db_session):
        """Test deleting a document."""
        service = DbDocumentService(db_session)
        doc_id = str(uuid4())
        owner = "user123"

        service.create_document(doc_id, owner, "temp.pdf", 1, 100)

        # Verify it exists
        doc = service.get_document(doc_id, owner)
        assert doc is not None

        # Delete it
        success = service.delete_document(doc_id, owner)
        assert success is True

        # Verify it's gone
        doc = service.get_document(doc_id, owner)
        assert doc is None

    def test_delete_non_existent_document(self, db_session):
        """Test deleting a document that doesn't exist."""
        service = DbDocumentService(db_session)
        success = service.delete_document(str(uuid4()), "user123")
        assert success is False


class TestDbConversationService:
    """Test database conversation service."""

    def test_create_conversation(self, db_session):
        """Test creating a conversation."""
        service = DbConversationService(db_session)
        owner = "user123"

        conv_id = service.create_conversation(owner, title="Test Chat")
        assert conv_id is not None

        # Verify it exists
        conv = service.get_conversation(owner, conv_id)
        assert conv is not None
        assert conv["title"] == "Test Chat"
        assert conv["id"] == conv_id

    def test_list_conversations_pagination(self, db_session):
        """Test listing conversations with pagination."""
        service = DbConversationService(db_session)
        owner = "user123"

        # Create 15 conversations
        for i in range(15):
            service.create_conversation(owner, title=f"Chat {i}")

        # Get first page (10 items)
        page1 = service.list_conversations(owner, limit=10, offset=0)
        assert len(page1) == 10

        # Get second page (5 items)
        page2 = service.list_conversations(owner, limit=10, offset=10)
        assert len(page2) == 5

    def test_add_message(self, db_session):
        """Test adding messages to conversation."""
        service = DbConversationService(db_session)
        owner = "user123"

        conv_id = service.create_conversation(owner, title="Chat")

        # Add user message
        success = service.add_message(owner, conv_id, "user", "Hello")
        assert success is True

        # Add assistant message
        success = service.add_message(owner, conv_id, "assistant", "Hi there!")
        assert success is True

        # Verify messages
        conv = service.get_conversation(owner, conv_id)
        assert len(conv["messages"]) == 2
        assert conv["messages"][0]["content"] == "Hello"
        assert conv["messages"][1]["content"] == "Hi there!"

    def test_message_ordering(self, db_session):
        """Test that messages are ordered by timestamp."""
        service = DbConversationService(db_session)
        owner = "user123"
        conv_id = service.create_conversation(owner)

        service.add_message(owner, conv_id, "user", "First")
        service.add_message(owner, conv_id, "assistant", "Second")
        service.add_message(owner, conv_id, "user", "Third")

        conv = service.get_conversation(owner, conv_id)
        messages = conv["messages"]
        assert len(messages) == 3
        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"
        assert messages[2]["content"] == "Third"

    def test_conversation_ownership_isolation(self, db_session):
        """Test that users can only access their own conversations."""
        service = DbConversationService(db_session)

        conv_id = service.create_conversation("user1", "Private Chat")

        # User1 can access
        conv = service.get_conversation("user1", conv_id)
        assert conv is not None

        # User2 cannot access
        conv = service.get_conversation("user2", conv_id)
        assert conv is None

    def test_delete_conversation(self, db_session):
        """Test deleting a conversation."""
        service = DbConversationService(db_session)
        owner = "user123"

        conv_id = service.create_conversation(owner, "To Delete")
        service.add_message(owner, conv_id, "user", "Test message")

        # Verify it exists
        conv = service.get_conversation(owner, conv_id)
        assert conv is not None
        assert len(conv["messages"]) == 1

        # Delete it
        success = service.delete_conversation(owner, conv_id)
        assert success is True

        # Verify it and messages are gone
        conv = service.get_conversation(owner, conv_id)
        assert conv is None

    def test_delete_non_existent_conversation(self, db_session):
        """Test deleting a conversation that doesn't exist."""
        service = DbConversationService(db_session)
        success = service.delete_conversation("user123", str(uuid4()))
        assert success is False

    def test_add_message_to_non_existent_conversation(self, db_session):
        """Test adding a message to non-existent conversation fails."""
        service = DbConversationService(db_session)
        success = service.add_message("user123", str(uuid4()), "user", "Hi")
        assert success is False

    def test_conversation_updated_at_updates(self, db_session):
        """Test that conversation updated_at is updated when messages are added."""
        service = DbConversationService(db_session)
        owner = "user123"

        conv_id = service.create_conversation(owner)
        conv1 = service.get_conversation(owner, conv_id)
        created_at = datetime.fromisoformat(conv1["created_at"])

        # Add a message
        service.add_message(owner, conv_id, "user", "Hello")

        conv2 = service.get_conversation(owner, conv_id)
        updated_at = datetime.fromisoformat(conv2["updated_at"])

        # Updated should be >= created (or later if any time passed)
        assert updated_at >= created_at


class TestMultiTenantIsolation:
    """Test multi-tenant isolation across services."""

    def test_documents_isolated_by_owner(self, db_session):
        """Test that documents are isolated by owner_id."""
        service = DbDocumentService(db_session)

        doc1_id = str(uuid4())
        doc2_id = str(uuid4())

        service.create_document(doc1_id, "tenant_a", "file.pdf", 5, 1000)
        service.create_document(doc2_id, "tenant_b", "file.pdf", 5, 1000)

        # Each tenant only sees their documents
        tenant_a_docs = service.list_documents("tenant_a")
        tenant_b_docs = service.list_documents("tenant_b")

        assert len(tenant_a_docs) == 1
        assert len(tenant_b_docs) == 1
        assert tenant_a_docs[0]["id"] == doc1_id
        assert tenant_b_docs[0]["id"] == doc2_id

    def test_conversations_isolated_by_owner(self, db_session):
        """Test that conversations are isolated by owner_id."""
        service = DbConversationService(db_session)

        conv_a = service.create_conversation("tenant_a", "Chat A")
        conv_b = service.create_conversation("tenant_b", "Chat B")

        # Each tenant only sees their conversations
        tenant_a_convs = service.list_conversations("tenant_a")
        tenant_b_convs = service.list_conversations("tenant_b")

        assert len(tenant_a_convs) == 1
        assert len(tenant_b_convs) == 1
        assert tenant_a_convs[0]["id"] == conv_a
        assert tenant_b_convs[0]["id"] == conv_b
