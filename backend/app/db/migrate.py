"""Database migration utilities to load existing JSON data."""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.models import Document, Conversation, Message

logger = logging.getLogger(__name__)


def migrate_document_registry(db: Session, registry_path: str = "./document_registry.json"):
    """
    Migrate documents from JSON registry to database.

    Args:
        db: Database session
        registry_path: Path to document_registry.json file
    """
    registry_file = Path(registry_path)

    if not registry_file.exists():
        logger.info(f"No document registry found at {registry_path}, skipping migration")
        return

    try:
        with open(registry_file, 'r') as f:
            registry = json.load(f)

        migrated = 0
        for doc_id, doc_data in registry.items():
            # Check if already migrated
            existing = db.query(Document).filter(Document.id == doc_id).first()
            if existing:
                continue

            # Create document record
            doc = Document(
                id=doc_id,
                owner_id=doc_data.get('owner_id', 'anonymous'),
                filename=doc_data.get('filename', 'unknown'),
                version=doc_data.get('version', 1),
                is_latest=doc_data.get('is_latest', True),
                chunk_count=doc_data.get('chunk_count', 0),
                text_length=doc_data.get('text_length', 0),
                uploaded_at=parse_isoformat(doc_data.get('uploaded_at')),
            )
            db.add(doc)
            migrated += 1

        if migrated > 0:
            db.commit()
            logger.info(f"Migrated {migrated} documents from JSON registry to database")
    except Exception as e:
        logger.error(f"Failed to migrate document registry: {e}")
        db.rollback()
        raise


def migrate_conversations(db: Session, conversations_dir: str = "./conversations"):
    """
    Migrate conversations from JSON files to database.

    Args:
        db: Database session
        conversations_dir: Path to conversations directory
    """
    conv_path = Path(conversations_dir)

    if not conv_path.exists():
        logger.info(f"No conversations directory found at {conversations_dir}, skipping migration")
        return

    try:
        migrated = 0
        # Iterate through owner directories
        for owner_dir in conv_path.iterdir():
            if not owner_dir.is_dir():
                continue

            owner_id = owner_dir.name

            # Iterate through conversation files
            for conv_file in owner_dir.glob("*.json"):
                conv_id = conv_file.stem

                # Check if already migrated
                existing = db.query(Conversation).filter(Conversation.id == conv_id).first()
                if existing:
                    continue

                try:
                    with open(conv_file, 'r') as f:
                        conv_data = json.load(f)

                    # Create conversation record
                    conversation = Conversation(
                        id=conv_id,
                        owner_id=owner_id,
                        title=conv_data.get('title'),
                        created_at=parse_isoformat(conv_data.get('created_at')),
                        updated_at=parse_isoformat(conv_data.get('updated_at')),
                    )
                    db.add(conversation)

                    # Add messages
                    for msg in conv_data.get('messages', []):
                        message = Message(
                            conversation_id=conv_id,
                            role=msg.get('role', 'user'),
                            content=msg.get('content', ''),
                            timestamp=parse_isoformat(msg.get('timestamp')),
                        )
                        db.add(message)

                    migrated += 1
                except Exception as e:
                    logger.error(f"Failed to migrate conversation {conv_id}: {e}")
                    continue

        if migrated > 0:
            db.commit()
            logger.info(f"Migrated {migrated} conversations from JSON to database")
    except Exception as e:
        logger.error(f"Failed to migrate conversations: {e}")
        db.rollback()
        raise


def parse_isoformat(date_str: str) -> datetime:
    """Parse ISO format datetime string with timezone awareness."""
    if not date_str:
        return datetime.now(timezone.utc)

    try:
        # Try parsing with timezone first
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        # Fallback to current time
        return datetime.now(timezone.utc)


def run_migrations(db: Session):
    """Run all database migrations."""
    logger.info("Starting database migrations...")

    migrate_document_registry(db)
    migrate_conversations(db)

    logger.info("Database migrations completed")
