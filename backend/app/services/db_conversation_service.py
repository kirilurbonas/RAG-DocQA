"""Database-backed conversation service (Phase 2+)."""

import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.orm import Session
from app.db.models import Conversation, Message

logger = logging.getLogger(__name__)


class DbConversationService:
    """Conversation management using SQLite database backend."""

    def __init__(self, db: Session):
        """
        Initialize database conversation service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_conversation(self, owner_id: str, title: Optional[str] = None) -> str:
        """
        Create a new conversation.

        Args:
            owner_id: Owner/tenant ID
            title: Optional conversation title

        Returns:
            Conversation ID (UUID)
        """
        conv_id = str(uuid4())
        conversation = Conversation(
            id=conv_id,
            owner_id=owner_id,
            title=title or f"Conversation {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        )
        self.db.add(conversation)
        self.db.commit()
        logger.info(f"Created conversation {conv_id} for owner {owner_id}")
        return conv_id

    def list_conversations(
        self, owner_id: str, limit: int = 10, offset: int = 0
    ) -> List[Dict]:
        """
        List conversations for owner with pagination.

        Args:
            owner_id: Owner/tenant ID
            limit: Max results
            offset: Pagination offset

        Returns:
            List of conversation dicts
        """
        conversations = self.db.query(Conversation).filter(
            Conversation.owner_id == owner_id
        ).order_by(
            Conversation.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "message_count": len(conv.messages)
            }
            for conv in conversations
        ]

    def get_conversation(self, owner_id: str, conversation_id: str) -> Optional[Dict]:
        """
        Get conversation with full message history.

        Args:
            owner_id: Owner/tenant ID
            conversation_id: Conversation ID

        Returns:
            Conversation dict with messages, or None if not found
        """
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.owner_id == owner_id
        ).first()

        if not conversation:
            return None

        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                }
                for msg in sorted(conversation.messages, key=lambda m: m.timestamp or datetime.now())
            ]
        }

    def add_message(
        self,
        owner_id: str,
        conversation_id: str,
        role: str,
        content: str
    ) -> bool:
        """
        Add message to conversation.

        Args:
            owner_id: Owner/tenant ID
            conversation_id: Conversation ID
            role: "user" or "assistant"
            content: Message content

        Returns:
            True if successful, False if conversation not found
        """
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.owner_id == owner_id
        ).first()

        if not conversation:
            return False

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        self.db.add(message)
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return True

    def delete_conversation(self, owner_id: str, conversation_id: str) -> bool:
        """
        Delete conversation and all its messages.

        Args:
            owner_id: Owner/tenant ID
            conversation_id: Conversation ID

        Returns:
            True if deleted, False if not found
        """
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.owner_id == owner_id
        ).first()

        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()

        return True
