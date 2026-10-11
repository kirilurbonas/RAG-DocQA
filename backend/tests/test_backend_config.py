"""Tests for backend configuration and migrations (Phase 2E)."""

import os
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backend_config import BackendType, is_database_backend, is_json_backend, BACKEND
from app.db.models import Base, Document, Conversation, Message
from app.db.migrate import migrate_document_registry, migrate_conversations, parse_isoformat


class TestBackendConfig:
    """Test backend configuration."""

    def test_database_backend_enum(self):
        """Test BackendType enum."""
        assert BackendType.JSON.value == "json"
        assert BackendType.DATABASE.value == "database"

    def test_backend_helpers(self, monkeypatch):
        """Test backend helper functions."""
        # Mock BACKEND to test both functions
        assert isinstance(BACKEND, BackendType)

        # is_database_backend and is_json_backend should sum to True
        assert is_database_backend() or is_json_backend()
        assert not (is_database_backend() and is_json_backend())


class TestMigrationParsing:
    """Test migration parsing utilities."""

    def test_parse_isoformat_with_timezone(self):
        """Test parsing ISO format datetime with timezone."""
        date_str = "2024-10-11T12:00:00+00:00"
        result = parse_isoformat(date_str)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_parse_isoformat_with_z(self):
        """Test parsing ISO format with Z suffix."""
        date_str = "2024-10-11T12:00:00Z"
        result = parse_isoformat(date_str)
        assert result is not None
        assert isinstance(result, datetime)

    def test_parse_isoformat_empty(self):
        """Test parsing empty string returns current time."""
        result = parse_isoformat("")
        assert result is not None
        assert isinstance(result, datetime)

    def test_parse_isoformat_invalid(self):
        """Test parsing invalid string returns current time."""
        result = parse_isoformat("invalid date")
        assert result is not None
        assert isinstance(result, datetime)


class TestDocumentMigration:
    """Test migration from JSON document registry to database."""

    def test_migrate_document_registry_no_file(self):
        """Test migration when registry file doesn't exist."""
        # Should not raise error, just skip
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        # This should not raise
        migrate_document_registry(db, "./nonexistent.json")
        db.close()

    def test_migrate_document_registry_from_json(self):
        """Test migration from JSON registry file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "document_registry.json"

            # Create test registry
            registry = {
                "doc1": {
                    "filename": "test.pdf",
                    "owner_id": "user123",
                    "version": 1,
                    "is_latest": True,
                    "chunk_count": 10,
                    "text_length": 5000,
                    "uploaded_at": "2024-10-11T12:00:00Z"
                },
                "doc2": {
                    "filename": "report.docx",
                    "owner_id": "user456",
                    "version": 1,
                    "is_latest": True,
                    "chunk_count": 8,
                    "text_length": 3000,
                    "uploaded_at": "2024-10-10T12:00:00Z"
                }
            }

            with open(registry_path, "w") as f:
                json.dump(registry, f)

            # Migrate to database
            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            migrate_document_registry(db, str(registry_path))

            # Verify documents were migrated
            docs = db.query(Document).all()
            assert len(docs) == 2

            doc_by_filename = {d.filename: d for d in docs}
            assert doc_by_filename["test.pdf"].owner_id == "user123"
            assert doc_by_filename["report.docx"].owner_id == "user456"

            db.close()

    def test_migrate_document_registry_skips_duplicates(self):
        """Test that migration skips already-migrated documents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "document_registry.json"

            registry = {
                "doc1": {
                    "filename": "test.pdf",
                    "owner_id": "user123",
                    "version": 1,
                    "is_latest": True,
                    "chunk_count": 10,
                    "text_length": 5000,
                    "uploaded_at": "2024-10-11T12:00:00Z"
                }
            }

            with open(registry_path, "w") as f:
                json.dump(registry, f)

            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            # First migration
            migrate_document_registry(db, str(registry_path))
            docs1 = db.query(Document).all()
            assert len(docs1) == 1

            # Second migration should skip duplicate
            migrate_document_registry(db, str(registry_path))
            docs2 = db.query(Document).all()
            assert len(docs2) == 1

            db.close()


class TestConversationMigration:
    """Test migration from JSON conversations to database."""

    def test_migrate_conversations_no_directory(self):
        """Test migration when conversations directory doesn't exist."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        # Should not raise
        migrate_conversations(db, "./nonexistent")
        db.close()

    def test_migrate_conversations_from_json(self):
        """Test migration from JSON conversation files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversations_dir = Path(tmpdir) / "conversations"
            user_dir = conversations_dir / "user123"
            user_dir.mkdir(parents=True, exist_ok=True)

            # Create conversation JSON files
            conv1 = {
                "id": "conv1",
                "title": "Chat 1",
                "created_at": "2024-10-11T10:00:00Z",
                "updated_at": "2024-10-11T12:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello",
                        "timestamp": "2024-10-11T10:00:00Z"
                    },
                    {
                        "role": "assistant",
                        "content": "Hi there!",
                        "timestamp": "2024-10-11T10:01:00Z"
                    }
                ]
            }

            with open(user_dir / "conv1.json", "w") as f:
                json.dump(conv1, f)

            # Migrate to database
            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            migrate_conversations(db, str(conversations_dir))

            # Verify conversation was migrated
            convs = db.query(Conversation).all()
            assert len(convs) == 1

            conv = convs[0]
            assert conv.id == "conv1"
            assert conv.title == "Chat 1"
            assert conv.owner_id == "user123"
            assert len(conv.messages) == 2

            # Verify messages
            messages = sorted(conv.messages, key=lambda m: m.timestamp)
            assert messages[0].content == "Hello"
            assert messages[1].content == "Hi there!"

            db.close()

    def test_migrate_conversations_multiple_users(self):
        """Test migration with conversations from multiple users."""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversations_dir = Path(tmpdir) / "conversations"

            # Create conversations for user1
            user1_dir = conversations_dir / "user1"
            user1_dir.mkdir(parents=True, exist_ok=True)

            conv1 = {
                "title": "User1 Chat",
                "created_at": "2024-10-11T10:00:00Z",
                "updated_at": "2024-10-11T12:00:00Z",
                "messages": []
            }
            with open(user1_dir / "conv1.json", "w") as f:
                json.dump(conv1, f)

            # Create conversations for user2
            user2_dir = conversations_dir / "user2"
            user2_dir.mkdir(parents=True, exist_ok=True)

            conv2 = {
                "title": "User2 Chat",
                "created_at": "2024-10-11T10:00:00Z",
                "updated_at": "2024-10-11T12:00:00Z",
                "messages": []
            }
            with open(user2_dir / "conv2.json", "w") as f:
                json.dump(conv2, f)

            # Migrate
            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            migrate_conversations(db, str(conversations_dir))

            # Verify
            convs = db.query(Conversation).all()
            assert len(convs) == 2

            user1_convs = [c for c in convs if c.owner_id == "user1"]
            user2_convs = [c for c in convs if c.owner_id == "user2"]

            assert len(user1_convs) == 1
            assert len(user2_convs) == 1

            db.close()

    def test_migrate_conversations_with_invalid_files(self):
        """Test migration skips invalid conversation files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            conversations_dir = Path(tmpdir) / "conversations"
            user_dir = conversations_dir / "user1"
            user_dir.mkdir(parents=True, exist_ok=True)

            # Create valid conversation
            valid_conv = {
                "title": "Valid Chat",
                "created_at": "2024-10-11T10:00:00Z",
                "updated_at": "2024-10-11T12:00:00Z",
                "messages": []
            }
            with open(user_dir / "valid.json", "w") as f:
                json.dump(valid_conv, f)

            # Create invalid JSON file
            with open(user_dir / "invalid.json", "w") as f:
                f.write("{ invalid json }")

            # Migrate (should not raise, should skip invalid)
            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            migrate_conversations(db, str(conversations_dir))

            # Should have migrated only valid conversation
            convs = db.query(Conversation).all()
            assert len(convs) == 1
            assert convs[0].title == "Valid Chat"

            db.close()
