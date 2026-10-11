"""Comprehensive UAT tests for all phases working together."""

import pytest
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, User, Document, Conversation, Message
from app.services.user_service import UserService
from app.services.analytics_service import AnalyticsService
from app.services.conversation_exporter import ConversationExporter
from app.services.rag_service import RAGService
from app.utils.semantic_chunking import SemanticChunker


@pytest.fixture
def db_session():
    """Create in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def user_service(db_session):
    """User service fixture."""
    return UserService(db_session)


@pytest.fixture
def analytics_service(db_session):
    """Analytics service fixture."""
    return AnalyticsService(db_session)


@pytest.fixture
def rag_service():
    """RAG service fixture."""
    return RAGService()


class TestEndToEndDocumentWorkflow:
    """Test complete document upload → search → answer workflow."""

    def test_document_upload_and_retrieval(self, rag_service, db_session):
        """Test uploading document and retrieving relevant chunks."""
        owner_id = str(uuid4())
        doc_content = "Python is a high-level programming language. It was created by Guido van Rossum."

        # Upload document
        doc_id = str(uuid4())
        document = Document(
            id=doc_id,
            owner_id=owner_id,
            filename="python_intro.txt",
            version=1,
            is_latest=True,
            chunk_count=1,
            text_length=len(doc_content),
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(document)
        db_session.commit()

        # Verify document persisted
        retrieved = db_session.query(Document).filter(
            Document.id == doc_id,
            Document.owner_id == owner_id
        ).first()

        assert retrieved is not None
        assert retrieved.filename == "python_intro.txt"
        assert retrieved.is_latest is True

    def test_document_versioning(self, db_session):
        """Test document versioning workflow."""
        owner_id = str(uuid4())
        filename = "important_doc.txt"

        # Create version 1
        doc_v1 = Document(
            id=str(uuid4()),
            owner_id=owner_id,
            filename=filename,
            version=1,
            is_latest=True,
            chunk_count=5,
            text_length=1000,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(doc_v1)
        db_session.commit()

        # Upload version 2 - mark v1 as not latest
        doc_v1.is_latest = False
        doc_v2 = Document(
            id=str(uuid4()),
            owner_id=owner_id,
            filename=filename,
            version=2,
            is_latest=True,
            chunk_count=6,
            text_length=1200,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(doc_v2)
        db_session.commit()

        # Verify only v2 is latest
        latest = db_session.query(Document).filter(
            Document.owner_id == owner_id,
            Document.filename == filename,
            Document.is_latest == True
        ).first()

        assert latest.version == 2

        # Verify v1 still exists
        all_versions = db_session.query(Document).filter(
            Document.owner_id == owner_id,
            Document.filename == filename
        ).order_by(Document.version).all()

        assert len(all_versions) == 2
        assert all_versions[0].version == 1
        assert all_versions[1].version == 2


class TestMultiUserWorkflow:
    """Test multi-user scenarios with isolation and sharing."""

    def test_user_isolation(self, user_service, db_session):
        """Test that users cannot see each other's documents."""
        user1 = user_service.create_user(
            email="user1@example.com",
            username="user1",
            password="SecurePass123"
        )
        user2 = user_service.create_user(
            email="user2@example.com",
            username="user2",
            password="SecurePass123"
        )

        owner1_id = user1['id']
        owner2_id = user2['id']

        # User1 uploads document
        doc1 = Document(
            id=str(uuid4()),
            owner_id=owner1_id,
            filename="user1_private.txt",
            version=1,
            is_latest=True,
            chunk_count=1,
            text_length=100
        )
        db_session.add(doc1)
        db_session.commit()

        # User2 tries to access user1's document
        user2_docs = db_session.query(Document).filter(
            Document.owner_id == owner2_id
        ).all()

        assert len(user2_docs) == 0

        # User1 can access their own
        user1_docs = db_session.query(Document).filter(
            Document.owner_id == owner1_id
        ).all()

        assert len(user1_docs) == 1

    def test_resource_sharing_workflow(self, user_service, db_session):
        """Test complete sharing workflow."""
        user1 = user_service.create_user(
            email="owner@example.com",
            username="owner",
            password="SecurePass123"
        )
        user2 = user_service.create_user(
            email="shared_user@example.com",
            username="shared_user",
            password="SecurePass123"
        )

        # Share document
        share = user_service.share_resource(
            resource_type="document",
            resource_id="doc-123",
            owner_id=user1['id'],
            shared_with_user_id=user2['id'],
            permission="read"
        )

        assert share is not None
        assert share['permission'] == "read"

        # Revoke share
        revoked = user_service.revoke_share(share['id'])
        assert revoked is True

    def test_team_collaboration_workflow(self, user_service, db_session):
        """Test team creation and collaboration."""
        owner = user_service.create_user(
            email="team_owner@example.com",
            username="owner",
            password="SecurePass123"
        )
        member1 = user_service.create_user(
            email="member1@example.com",
            username="member1",
            password="SecurePass123"
        )
        member2 = user_service.create_user(
            email="member2@example.com",
            username="member2",
            password="SecurePass123"
        )

        # Create team
        team = user_service.create_team(owner['id'], "Engineering Team")
        assert team is not None

        # Add members
        user_service.add_team_member(team['id'], member1['id'], role='member')
        user_service.add_team_member(team['id'], member2['id'], role='admin')

        # Verify team composition
        owner_teams = user_service.get_user_teams(owner['id'])
        member1_teams = user_service.get_user_teams(member1['id'])
        member2_teams = user_service.get_user_teams(member2['id'])

        assert len(owner_teams) == 1
        assert len(member1_teams) == 1
        assert len(member2_teams) == 1

        assert owner_teams[0]['role'] == 'owner'
        assert member1_teams[0]['role'] == 'member'
        assert member2_teams[0]['role'] == 'admin'


class TestConversationWorkflow:
    """Test conversation persistence and multi-turn interactions."""

    def test_create_and_retrieve_conversation(self, db_session):
        """Test creating conversation and retrieving history."""
        owner_id = str(uuid4())
        conv_id = str(uuid4())

        # Create conversation
        conversation = Conversation(
            id=conv_id,
            owner_id=owner_id,
            title="My First Conversation"
        )
        db_session.add(conversation)
        db_session.commit()

        # Add messages
        for i, (role, content) in enumerate([
            ("user", "What is Python?"),
            ("assistant", "Python is a programming language."),
            ("user", "Tell me more"),
            ("assistant", "It's high-level, dynamic, and popular.")
        ]):
            msg = Message(
                conversation_id=conv_id,
                role=role,
                content=content,
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
            db_session.add(msg)
        db_session.commit()

        # Retrieve conversation with messages
        conv = db_session.query(Conversation).filter(
            Conversation.id == conv_id
        ).first()

        assert conv is not None
        assert conv.title == "My First Conversation"
        assert len(conv.messages) == 4

        # Verify message order
        messages = sorted(conv.messages, key=lambda m: m.timestamp)
        assert messages[0].role == "user"
        assert messages[0].content == "What is Python?"

    def test_conversation_isolation_by_owner(self, db_session):
        """Test that conversations are isolated by owner."""
        user1_id = str(uuid4())
        user2_id = str(uuid4())

        # User1 creates conversation
        conv1 = Conversation(
            id=str(uuid4()),
            owner_id=user1_id,
            title="User1 Conversation"
        )
        db_session.add(conv1)

        # User2 creates conversation
        conv2 = Conversation(
            id=str(uuid4()),
            owner_id=user2_id,
            title="User2 Conversation"
        )
        db_session.add(conv2)
        db_session.commit()

        # User1 sees only their conversation
        user1_convs = db_session.query(Conversation).filter(
            Conversation.owner_id == user1_id
        ).all()

        assert len(user1_convs) == 1
        assert user1_convs[0].title == "User1 Conversation"


class TestAnalyticsWorkflow:
    """Test comprehensive analytics tracking."""

    def test_usage_tracking_across_operations(self, analytics_service):
        """Test tracking different operation types."""
        user_id = str(uuid4())

        # Track various operations
        analytics_service.track_event(user_id, "upload", token_count=0, latency_ms=1500)
        analytics_service.track_event(user_id, "ask", token_count=150, latency_ms=2000)
        analytics_service.track_event(user_id, "ask", token_count=200, latency_ms=2500)
        analytics_service.track_event(user_id, "export", token_count=0, latency_ms=500)
        analytics_service.track_event(user_id, "ask", token_count=100, latency_ms=1800, success=False)

        # Get stats
        stats = analytics_service.get_user_stats(user_id)

        assert stats['total_events'] == 5
        assert stats['events_by_type']['upload'] == 1
        assert stats['events_by_type']['ask'] == 3
        assert stats['events_by_type']['export'] == 1
        assert stats['total_tokens'] == 450
        assert abs(stats['success_rate'] - 0.8) < 0.01

    def test_aggregate_analytics(self, analytics_service):
        """Test aggregate statistics across users."""
        users = [str(uuid4()) for _ in range(3)]

        # Simulate activity
        for user_id in users:
            for _ in range(5):
                analytics_service.track_event(user_id, "ask", token_count=100, latency_ms=2000)
            analytics_service.track_event(user_id, "upload", token_count=0, latency_ms=1000)

        # Get aggregate
        agg = analytics_service.get_aggregate_stats()

        assert agg['total_events'] == 18
        assert agg['unique_users'] == 3
        assert agg['total_tokens'] == 1500
        assert agg['events_by_type']['ask'] == 15
        assert agg['events_by_type']['upload'] == 3

    def test_top_users_ranking(self, analytics_service):
        """Test ranking of top users."""
        user1 = str(uuid4())
        user2 = str(uuid4())
        user3 = str(uuid4())

        # User1: 10 events, 1000 tokens
        for i in range(10):
            analytics_service.track_event(user1, "ask", token_count=100, latency_ms=2000)

        # User2: 5 events, 500 tokens
        for i in range(5):
            analytics_service.track_event(user2, "ask", token_count=100, latency_ms=2000)

        # User3: 8 events, 800 tokens
        for i in range(8):
            analytics_service.track_event(user3, "ask", token_count=100, latency_ms=2000)

        # Get top by events
        top_events = analytics_service.get_top_users(metric='events', limit=3)
        assert top_events[0]['user_id'] == user1
        assert top_events[0]['event_count'] == 10

        # Get top by tokens
        top_tokens = analytics_service.get_top_users(metric='tokens', limit=3)
        assert top_tokens[0]['user_id'] == user1
        assert top_tokens[0]['total_tokens'] == 1000


class TestConversationExportWorkflow:
    """Test conversation export in multiple formats."""

    def test_export_workflow(self):
        """Test exporting conversation in multiple formats."""
        # Create conversation dict
        conv = {
            "id": str(uuid4()),
            "title": "Export Test",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": [
                {"role": "user", "content": "What is AI?", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "assistant", "content": "AI is Artificial Intelligence, a field of computer science.", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "user", "content": "Give examples", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "assistant", "content": "Examples: ChatGPT, image recognition, recommendation systems.", "timestamp": datetime.now(timezone.utc).isoformat()},
            ]
        }

        # Export to markdown
        markdown = ConversationExporter.to_markdown(conv)

        assert "Export Test" in markdown
        assert "What is AI?" in markdown
        assert "Artificial Intelligence" in markdown

        # Export to JSON
        json_export = ConversationExporter.to_json(conv)

        assert json_export is not None
        assert isinstance(json_export, str)

        # Parse JSON string to verify content
        parsed = json.loads(json_export)
        assert "messages" in parsed
        assert len(parsed['messages']) == 4


class TestAuthenticationWorkflow:
    """Test user authentication and session management."""

    def test_user_signup_and_login(self, user_service):
        """Test user registration and authentication."""
        # Sign up
        user = user_service.create_user(
            email="newuser@example.com",
            username="newuser",
            password="StrongPassword123"
        )

        assert user is not None
        assert user['email'] == "newuser@example.com"
        assert user['is_active'] is True

        # Login
        authenticated = user_service.authenticate_user(
            "newuser@example.com",
            "StrongPassword123"
        )

        assert authenticated is not None
        assert authenticated['id'] == user['id']
        assert authenticated['last_login'] is not None

    def test_password_change_workflow(self, user_service):
        """Test changing password."""
        # Create user
        user = user_service.create_user(
            email="user@example.com",
            username="user",
            password="OldPassword123"
        )

        # Change password
        success = user_service.update_password(
            user['id'],
            "OldPassword123",
            "NewPassword456"
        )

        assert success is True

        # Old password fails
        result = user_service.authenticate_user("user@example.com", "OldPassword123")
        assert result is None

        # New password works
        result = user_service.authenticate_user("user@example.com", "NewPassword456")
        assert result is not None

    def test_user_deactivation(self, user_service, db_session):
        """Test user account deactivation."""
        user = user_service.create_user(
            email="temp@example.com",
            username="temp",
            password="Password123"
        )

        # Deactivate
        success = user_service.deactivate_user(user['id'])
        assert success is True

        # Verify deactivated in DB
        db_user = db_session.query(User).filter(User.id == user['id']).first()
        assert db_user.is_active is False


class TestSemanticChunkingIntegration:
    """Test semantic chunking with various strategies."""

    def test_semantic_chunker_initialization(self):
        """Test chunker initializes correctly."""
        chunker = SemanticChunker()
        assert chunker is not None

    def test_sentence_splitting(self):
        """Test sentence splitting."""
        chunker = SemanticChunker()
        text = "This is sentence one. This is sentence two! And a third one?"

        sentences = chunker.split_by_sentences(text)

        assert len(sentences) >= 3
        assert any("sentence one" in s for s in sentences)

    def test_token_based_chunking(self):
        """Test token-based chunking."""
        chunker = SemanticChunker()
        text = " ".join(["word"] * 100)  # 100 words

        chunks = chunker.chunk_by_tokens(text, target_chunk_size=100, max_chunk_size=200)

        assert len(chunks) > 0
        assert all(chunk for chunk in chunks)


class TestDataConsistency:
    """Test data consistency across operations."""

    def test_transactional_consistency(self, db_session):
        """Test transactional operations are consistent."""
        owner_id = str(uuid4())

        # Create multiple documents atomically
        docs = []
        for i in range(5):
            doc = Document(
                id=str(uuid4()),
                owner_id=owner_id,
                filename=f"doc_{i}.txt",
                version=1,
                is_latest=True,
                chunk_count=10,
                text_length=1000
            )
            docs.append(doc)

        db_session.add_all(docs)
        db_session.commit()

        # Verify all were saved
        retrieved = db_session.query(Document).filter(
            Document.owner_id == owner_id
        ).all()

        assert len(retrieved) == 5

    def test_cascade_delete_on_conversation(self, db_session):
        """Test cascading deletes work correctly."""
        conv_id = str(uuid4())
        owner_id = str(uuid4())

        # Create conversation with messages
        conv = Conversation(
            id=conv_id,
            owner_id=owner_id,
            title="To Delete"
        )
        db_session.add(conv)

        for i in range(5):
            msg = Message(
                conversation_id=conv_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
            db_session.add(msg)

        db_session.commit()

        # Verify messages exist
        messages_before = db_session.query(Message).filter(
            Message.conversation_id == conv_id
        ).all()
        assert len(messages_before) == 5

        # Delete conversation
        db_session.delete(conv)
        db_session.commit()

        # Verify messages are deleted too
        messages_after = db_session.query(Message).filter(
            Message.conversation_id == conv_id
        ).all()
        assert len(messages_after) == 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_duplicate_user_creation(self, user_service):
        """Test preventing duplicate user creation."""
        user_service.create_user(
            email="duplicate@example.com",
            username="user1",
            password="Password123"
        )

        with pytest.raises(ValueError):
            user_service.create_user(
                email="duplicate@example.com",
                username="user2",
                password="Password123"
            )

    def test_invalid_password_handling(self, user_service):
        """Test invalid password rejection."""
        with pytest.raises(ValueError):
            user_service.create_user(
                email="user@example.com",
                username="user",
                password="short"  # Too short
            )

    def test_nonexistent_user_operations(self, user_service):
        """Test operations on nonexistent users."""
        fake_id = str(uuid4())

        # Getting teams for nonexistent user
        teams = user_service.get_user_teams(fake_id)
        assert teams == []

        # Authenticating nonexistent user
        result = user_service.authenticate_user("fake@example.com", "password")
        assert result is None


class TestPerformanceBaseline:
    """Test performance baseline metrics."""

    def test_large_conversation_retrieval(self, db_session):
        """Test retrieving conversations with many messages."""
        conv_id = str(uuid4())
        owner_id = str(uuid4())

        conv = Conversation(
            id=conv_id,
            owner_id=owner_id,
            title="Large Conversation"
        )
        db_session.add(conv)

        # Add 100 messages
        for i in range(100):
            msg = Message(
                conversation_id=conv_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}" * 10,  # Longer content
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
            db_session.add(msg)

        db_session.commit()

        # Retrieve conversation
        conv = db_session.query(Conversation).filter(
            Conversation.id == conv_id
        ).first()

        assert conv is not None
        assert len(conv.messages) == 100

    def test_document_listing_with_many_documents(self, db_session):
        """Test listing performance with many documents."""
        owner_id = str(uuid4())

        # Create 50 documents
        for i in range(50):
            doc = Document(
                id=str(uuid4()),
                owner_id=owner_id,
                filename=f"document_{i}.txt",
                version=1,
                is_latest=True,
                chunk_count=10,
                text_length=1000
            )
            db_session.add(doc)

        db_session.commit()

        # List documents
        docs = db_session.query(Document).filter(
            Document.owner_id == owner_id,
            Document.is_latest == True
        ).all()

        assert len(docs) == 50
