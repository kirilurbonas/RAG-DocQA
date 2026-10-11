"""Tests for Phase 10 - Fine-tuning Service.

Tests cover:
- Training data extraction from documents and conversations
- Fine-tuning job creation and management
- Multi-tenant isolation
- API endpoints
"""

import pytest
import json
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.models import Base, User, Document, Conversation, Message, FineTuningJob, TrainingExample
from app.services.fine_tuning_service import FineTuningService


@pytest.fixture
def db_session():
    """Create in-memory SQLite test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user_data():
    """Create test user data."""
    return {
        "user1": str(uuid4()),
        "user2": str(uuid4()),
    }


@pytest.fixture
def populate_db(db_session, test_user_data):
    """Populate database with test data."""
    # Create documents for user1
    doc1 = Document(
        id=str(uuid4()),
        owner_id=test_user_data["user1"],
        filename="document1.pdf",
        version=1,
        is_latest=True,
        chunk_count=10,
        text_length=5000
    )
    doc2 = Document(
        id=str(uuid4()),
        owner_id=test_user_data["user1"],
        filename="document2.pdf",
        version=1,
        is_latest=True,
        chunk_count=8,
        text_length=4000
    )

    # Create conversation for user1
    conv1 = Conversation(
        id=str(uuid4()),
        owner_id=test_user_data["user1"],
        title="Test Conversation"
    )
    db_session.add_all([doc1, doc2, conv1])
    db_session.flush()

    # Add messages to conversation
    msg1 = Message(
        conversation_id=conv1.id,
        role="user",
        content="What is machine learning?"
    )
    msg2 = Message(
        conversation_id=conv1.id,
        role="assistant",
        content="Machine learning is a field of AI that enables systems to learn from data."
    )
    db_session.add_all([msg1, msg2])
    db_session.commit()

    return {
        "docs": [doc1, doc2],
        "conversations": [conv1],
        "user1_id": test_user_data["user1"],
        "user2_id": test_user_data["user2"]
    }


class TestFineTuningService:
    """Test FineTuningService methods."""

    def test_extract_training_data_llm(self, db_session, populate_db):
        """Test extracting LLM training data from conversations and documents."""
        service = FineTuningService(db_session)

        training_data = db_session.run_sync(
            service.extract_training_data,
            owner_id=populate_db["user1_id"],
            model_type="llm"
        )

        # Should have conversation pairs
        assert len(training_data) > 0

        # Check format
        assert "prompt" in training_data[0] or "source" in training_data[0]

    @pytest.mark.asyncio
    async def test_extract_training_data_embedding(self, db_session, populate_db):
        """Test extracting embedding training data."""
        service = FineTuningService(db_session)

        training_data = await service.extract_training_data(
            owner_id=populate_db["user1_id"],
            model_type="embedding"
        )

        # Should have positive/negative pairs
        assert len(training_data) > 0
        assert "text1" in training_data[0]
        assert "text2" in training_data[0]
        assert "label" in training_data[0]
        assert training_data[0]["label"] in [0.0, 1.0]

    @pytest.mark.asyncio
    async def test_create_fine_tuning_job(self, db_session, populate_db):
        """Test creating a fine-tuning job."""
        service = FineTuningService(db_session)

        training_data = [
            {"prompt": "What is X?", "completion": "X is..."},
            {"prompt": "How does Y work?", "completion": "Y works by..."}
        ]

        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Test Job",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=training_data,
            training_params={"epochs": 2, "learning_rate": 1e-4},
            document_ids=None
        )

        assert job.id is not None
        assert job.job_name == "Test Job"
        assert job.model_type == "llm"
        assert job.base_model == "gpt-3.5-turbo"
        assert job.provider == "openai"
        assert job.status == "pending"
        assert job.owner_id == populate_db["user1_id"]
        assert job.is_active is False

        # Check training examples were created
        examples = db_session.query(TrainingExample).filter(
            TrainingExample.job_id == job.id
        ).all()
        assert len(examples) == len(training_data)

    @pytest.mark.asyncio
    async def test_get_job_status(self, db_session, populate_db):
        """Test retrieving job status."""
        service = FineTuningService(db_session)

        # Create a job
        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Status Test",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )

        # Get status
        retrieved_job = await service.get_job_status(
            owner_id=populate_db["user1_id"],
            job_id=job.id
        )

        assert retrieved_job.id == job.id
        assert retrieved_job.job_name == "Status Test"

    @pytest.mark.asyncio
    async def test_get_job_status_cross_tenant(self, db_session, populate_db):
        """Test that users cannot access other users' jobs."""
        service = FineTuningService(db_session)

        # Create job for user1
        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="User1 Job",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )

        # Try to access with user2 - should fail
        with pytest.raises(ValueError, match="not found or access denied"):
            await service.get_job_status(
                owner_id=populate_db["user2_id"],
                job_id=job.id
            )

    @pytest.mark.asyncio
    async def test_list_jobs(self, db_session, populate_db):
        """Test listing jobs for a user."""
        service = FineTuningService(db_session)

        # Create multiple jobs
        for i in range(3):
            await service.create_fine_tuning_job(
                owner_id=populate_db["user1_id"],
                job_name=f"Job {i}",
                model_type="llm",
                base_model="gpt-3.5-turbo",
                provider="openai",
                training_data=[{"prompt": "test", "completion": "test"}],
                training_params={}
            )

        # List jobs
        jobs = await service.list_jobs(owner_id=populate_db["user1_id"])

        assert len(jobs) == 3
        assert all(job.owner_id == populate_db["user1_id"] for job in jobs)

    @pytest.mark.asyncio
    async def test_list_jobs_by_status(self, db_session, populate_db):
        """Test filtering jobs by status."""
        service = FineTuningService(db_session)

        # Create jobs with different statuses
        job1 = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Pending Job",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )

        job2 = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Training Job",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )
        job2.status = "training"
        db_session.commit()

        # Filter by status
        pending_jobs = await service.list_jobs(
            owner_id=populate_db["user1_id"],
            status="pending"
        )

        assert len(pending_jobs) == 1
        assert pending_jobs[0].status == "pending"

    @pytest.mark.asyncio
    async def test_activate_job(self, db_session, populate_db):
        """Test activating a completed job."""
        service = FineTuningService(db_session)

        # Create and complete a job
        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Complete Job",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )
        job.status = "completed"
        db_session.commit()

        # Activate
        activated = await service.activate_job(
            owner_id=populate_db["user1_id"],
            job_id=job.id
        )

        assert activated.is_active is True

    @pytest.mark.asyncio
    async def test_activate_job_not_completed(self, db_session, populate_db):
        """Test that only completed jobs can be activated."""
        service = FineTuningService(db_session)

        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Pending Job",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )

        # Try to activate pending job
        with pytest.raises(ValueError, match="Cannot activate"):
            await service.activate_job(
                owner_id=populate_db["user1_id"],
                job_id=job.id
            )

    @pytest.mark.asyncio
    async def test_deactivate_job(self, db_session, populate_db):
        """Test deactivating an active job."""
        service = FineTuningService(db_session)

        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Active Job",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )
        job.status = "completed"
        job.is_active = True
        db_session.commit()

        # Deactivate
        deactivated = await service.deactivate_job(
            owner_id=populate_db["user1_id"],
            job_id=job.id
        )

        assert deactivated.is_active is False

    @pytest.mark.asyncio
    async def test_delete_job(self, db_session, populate_db):
        """Test deleting a job."""
        service = FineTuningService(db_session)

        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Delete Me",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )
        job_id = job.id

        # Delete
        await service.delete_job(
            owner_id=populate_db["user1_id"],
            job_id=job_id
        )

        # Verify deletion
        with pytest.raises(ValueError):
            await service.get_job_status(
                owner_id=populate_db["user1_id"],
                job_id=job_id
            )

    @pytest.mark.asyncio
    async def test_record_metric(self, db_session, populate_db):
        """Test recording training metrics."""
        service = FineTuningService(db_session)

        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Metric Job",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )

        # Record metrics
        metric = await service.record_metric(
            job_id=job.id,
            metric_type="loss",
            epoch=1,
            value=0.5
        )

        assert metric.metric_type == "loss"
        assert metric.epoch == 1
        assert metric.value == 0.5

    @pytest.mark.asyncio
    async def test_get_active_job(self, db_session, populate_db):
        """Test retrieving the active job for a user."""
        service = FineTuningService(db_session)

        # Create and activate a job
        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Active Model",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )
        job.status = "completed"
        db_session.commit()

        await service.activate_job(
            owner_id=populate_db["user1_id"],
            job_id=job.id
        )

        # Get active job
        active = await service.get_active_job(owner_id=populate_db["user1_id"])

        assert active is not None
        assert active.id == job.id
        assert active.is_active is True


class TestFineTuningMultiTenant:
    """Test multi-tenant isolation for fine-tuning."""

    @pytest.mark.asyncio
    async def test_isolation(self, db_session, populate_db):
        """Test that users cannot cross-access fine-tuning data."""
        service = FineTuningService(db_session)

        # User1 creates a job
        job = await service.create_fine_tuning_job(
            owner_id=populate_db["user1_id"],
            job_name="Isolated Job",
            model_type="llm",
            base_model="gpt-3.5-turbo",
            provider="openai",
            training_data=[{"prompt": "test", "completion": "test"}],
            training_params={}
        )

        # User1's list should include the job
        user1_jobs = await service.list_jobs(owner_id=populate_db["user1_id"])
        assert any(j.id == job.id for j in user1_jobs)

        # User2's list should not include it
        user2_jobs = await service.list_jobs(owner_id=populate_db["user2_id"])
        assert not any(j.id == job.id for j in user2_jobs)


class TestFineTuningDataTypes:
    """Test different model types."""

    @pytest.mark.asyncio
    async def test_llm_data_format(self, db_session, populate_db):
        """Test LLM training data format."""
        service = FineTuningService(db_session)

        data = await service.get_training_examples_llm(
            owner_id=populate_db["user1_id"]
        )

        if data:
            assert "prompt" in data[0]
            assert "completion" in data[0]

    @pytest.mark.asyncio
    async def test_embedding_data_format(self, db_session, populate_db):
        """Test embedding training data format."""
        service = FineTuningService(db_session)

        data = await service.get_training_examples_embedding(
            owner_id=populate_db["user1_id"]
        )

        if data:
            assert "text1" in data[0]
            assert "text2" in data[0]
            assert "label" in data[0]
            assert isinstance(data[0]["label"], float)
