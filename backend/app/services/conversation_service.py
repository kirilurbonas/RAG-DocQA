"""Conversation history persistence service."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConversationService:
    """Manages conversation history persistence."""

    def __init__(self, data_dir: str = "./conversations"):
        """Initialize conversation service with data directory."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_owner_dir(self, owner_id: str) -> Path:
        """Get directory for owner's conversations."""
        owner_dir = self.data_dir / owner_id
        owner_dir.mkdir(parents=True, exist_ok=True)
        return owner_dir

    def create_conversation(self, owner_id: str, title: Optional[str] = None) -> str:
        """
        Create a new conversation.

        Args:
            owner_id: Owner ID for access control
            title: Optional conversation title

        Returns:
            Conversation ID
        """
        conv_id = str(uuid.uuid4())
        owner_dir = self._get_owner_dir(owner_id)
        conv_path = owner_dir / f"{conv_id}.json"

        conversation = {
            "id": conv_id,
            "owner_id": owner_id,
            "title": title or f"Conversation {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": []
        }

        with open(conv_path, 'w') as f:
            json.dump(conversation, f, indent=2)

        logger.debug(f"Created conversation {conv_id} for owner {owner_id}")
        return conv_id

    def add_message(self, owner_id: str, conversation_id: str, role: str, content: str) -> bool:
        """
        Add a message to conversation.

        Args:
            owner_id: Owner ID for access control
            conversation_id: Conversation ID
            role: Message role (user, assistant)
            content: Message content

        Returns:
            True if successful, False if conversation not found
        """
        conv_path = self._get_owner_dir(owner_id) / f"{conversation_id}.json"

        if not conv_path.exists():
            logger.warning(f"Conversation {conversation_id} not found for owner {owner_id}")
            return False

        try:
            with open(conv_path, 'r') as f:
                conversation = json.load(f)

            # Verify ownership
            if conversation.get("owner_id") != owner_id:
                logger.warning(f"Ownership mismatch for conversation {conversation_id}")
                return False

            conversation["messages"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            conversation["updated_at"] = datetime.now(timezone.utc).isoformat()

            with open(conv_path, 'w') as f:
                json.dump(conversation, f, indent=2)

            return True
        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            return False

    def get_conversation(self, owner_id: str, conversation_id: str) -> Optional[Dict]:
        """Get conversation details."""
        conv_path = self._get_owner_dir(owner_id) / f"{conversation_id}.json"

        if not conv_path.exists():
            return None

        try:
            with open(conv_path, 'r') as f:
                conversation = json.load(f)

            # Verify ownership
            if conversation.get("owner_id") != owner_id:
                return None

            return conversation
        except Exception as e:
            logger.error(f"Failed to read conversation {conversation_id}: {e}")
            return None

    def get_conversation_history(self, owner_id: str, conversation_id: str) -> List[Dict]:
        """
        Get message history in OpenAI format.

        Args:
            owner_id: Owner ID
            conversation_id: Conversation ID

        Returns:
            List of messages with role and content, or empty list if not found
        """
        conversation = self.get_conversation(owner_id, conversation_id)
        if not conversation:
            return []

        # Return in OpenAI format (role, content)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in conversation.get("messages", [])
        ]

    def list_conversations(self, owner_id: str, limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        List conversations for owner.

        Args:
            owner_id: Owner ID
            limit: Max conversations to return
            offset: Offset for pagination

        Returns:
            List of conversation summaries (no message history)
        """
        owner_dir = self._get_owner_dir(owner_id)
        conversations = []

        try:
            for conv_file in sorted(owner_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                with open(conv_file, 'r') as f:
                    conv = json.load(f)

                # Return summary (no full message history)
                conversations.append({
                    "id": conv["id"],
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "updated_at": conv["updated_at"],
                    "message_count": len(conv.get("messages", []))
                })
        except Exception as e:
            logger.error(f"Failed to list conversations for owner {owner_id}: {e}")

        return conversations[offset:offset + limit]

    def delete_conversation(self, owner_id: str, conversation_id: str) -> bool:
        """Delete conversation."""
        conv_path = self._get_owner_dir(owner_id) / f"{conversation_id}.json"

        if not conv_path.exists():
            return False

        try:
            # Verify ownership before deleting
            with open(conv_path, 'r') as f:
                conversation = json.load(f)

            if conversation.get("owner_id") != owner_id:
                return False

            conv_path.unlink()
            logger.info(f"Deleted conversation {conversation_id} for owner {owner_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return False
