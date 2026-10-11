"""SQLAlchemy models for RAG-DocQA database."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Document(Base):
    """Document metadata table."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    owner_id = Column(String(255), nullable=False, index=True)  # Tenant/owner isolation
    filename = Column(String(255), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, nullable=False, default=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    text_length = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Indexes for common queries
    __table_args__ = (
        Index('ix_documents_owner_filename', 'owner_id', 'filename'),
        Index('ix_documents_owner_latest', 'owner_id', 'is_latest'),
    )


class Conversation(Base):
    """Conversation metadata table."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    owner_id = Column(String(255), nullable=False, index=True)  # Tenant/owner isolation
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    # Index for common queries
    __table_args__ = (
        Index('ix_conversations_owner_created', 'owner_id', 'created_at'),
    )


class Message(Base):
    """Conversation message table."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey('conversations.id'), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Index for message ordering
    __table_args__ = (
        Index('ix_messages_conversation_timestamp', 'conversation_id', 'timestamp'),
    )
