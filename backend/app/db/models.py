"""SQLAlchemy models for RAG-DocQA database."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, Index, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User account table."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # argon2
    is_active = Column(Boolean, nullable=False, default=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    teams = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    usage_events = relationship("UsageEvent", back_populates="user", cascade="all, delete-orphan")


class Team(Base):
    """Team/organization table."""

    __tablename__ = "teams"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    name = Column(String(255), nullable=False)
    owner_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_teams_owner', 'owner_id'),
    )


class TeamMember(Base):
    """Team membership table."""

    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(36), ForeignKey('teams.id'), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    role = Column(String(20), nullable=False, default='member')  # owner, admin, member
    joined_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="teams")

    __table_args__ = (
        Index('ix_team_members_team_user', 'team_id', 'user_id'),
    )


class Share(Base):
    """Document/conversation sharing table."""

    __tablename__ = "shares"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    resource_type = Column(String(20), nullable=False)  # document, conversation
    resource_id = Column(String(36), nullable=False)
    owner_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    shared_with_user_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    shared_with_team_id = Column(String(36), ForeignKey('teams.id'), nullable=True)
    permission = Column(String(20), nullable=False, default='read')  # read, write
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships - specify foreign_keys to disambiguate
    owner = relationship("User", foreign_keys=[owner_id], viewonly=True)
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])

    __table_args__ = (
        Index('ix_shares_resource', 'resource_type', 'resource_id'),
        Index('ix_shares_owner', 'owner_id'),
        Index('ix_shares_user', 'shared_with_user_id'),
        Index('ix_shares_team', 'shared_with_team_id'),
    )


class UsageEvent(Base):
    """Usage tracking table."""

    __tablename__ = "usage_events"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # ask, upload, export, etc
    resource_type = Column(String(20), nullable=True)  # document, conversation
    token_count = Column(Integer, nullable=True, default=0)
    latency_ms = Column(Float, nullable=True)  # milliseconds
    success = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="usage_events")

    __table_args__ = (
        Index('ix_usage_events_user', 'user_id'),
        Index('ix_usage_events_type', 'event_type'),
        Index('ix_usage_events_created', 'created_at'),
    )


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


class FineTuningJob(Base):
    """Fine-tuning job tracking table for Phase 10."""

    __tablename__ = "fine_tuning_jobs"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    owner_id = Column(String(255), nullable=False, index=True)  # Multi-tenant isolation
    job_name = Column(String(255), nullable=False)
    model_type = Column(String(50), nullable=False)  # "llm" | "embedding" | "local_llm"
    base_model = Column(String(255), nullable=False)  # e.g., gpt-3.5-turbo, all-MiniLM-L6-v2
    provider = Column(String(50), nullable=False)  # "openai" | "anthropic" | "local" | "huggingface"
    status = Column(String(50), nullable=False, default="pending")  # pending|training|completed|failed
    dataset_source = Column(String(255), nullable=False, default="both")  # "documents"|"conversations"|"both"
    document_ids = Column(JSON, nullable=True)  # Array of document UUIDs used for training
    training_params = Column(JSON, nullable=False)  # {epochs, learning_rate, batch_size, max_tokens}
    metrics = Column(JSON, nullable=True)  # {final_loss, accuracy, examples_trained}
    external_job_id = Column(String(255), nullable=True)  # OpenAI/Anthropic job ID
    artifact_path = Column(String(255), nullable=True)  # Local path or S3 URL
    is_active = Column(Boolean, nullable=False, default=False)  # Model in use for RAG
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Temporary models

    # Relationships
    training_examples = relationship("TrainingExample", back_populates="job", cascade="all, delete-orphan")
    training_metrics = relationship("TrainingMetric", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_fine_tuning_jobs_owner', 'owner_id'),
        Index('ix_fine_tuning_jobs_status', 'status'),
        Index('ix_fine_tuning_jobs_active', 'owner_id', 'is_active'),
    )


class TrainingExample(Base):
    """Training examples extracted from documents/conversations."""

    __tablename__ = "training_examples"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    job_id = Column(String(36), ForeignKey('fine_tuning_jobs.id'), nullable=False, index=True)
    example_type = Column(String(50), nullable=False)  # "prompt_completion"|"instruction"|"embedding_pair"
    input_text = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=True)
    source_document_id = Column(String(36), nullable=True)
    source_conversation_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    job = relationship("FineTuningJob", back_populates="training_examples")

    __table_args__ = (
        Index('ix_training_examples_job', 'job_id'),
        Index('ix_training_examples_type', 'example_type'),
    )


class TrainingMetric(Base):
    """Track fine-tuning progress metrics (loss, accuracy, etc.)."""

    __tablename__ = "training_metrics"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    job_id = Column(String(36), ForeignKey('fine_tuning_jobs.id'), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)  # "loss"|"accuracy"|"validation_loss"
    epoch = Column(Integer, nullable=False)
    value = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    job = relationship("FineTuningJob", back_populates="training_metrics")

    __table_args__ = (
        Index('ix_training_metrics_job_epoch', 'job_id', 'epoch'),
    )
