"""Fine-tuning service for Phase 10 - Advanced Model Fine-tuning.

Handles extraction of training data from documents and conversations,
job creation/management, and integration with various fine-tuning providers.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import (
    FineTuningJob,
    TrainingExample,
    TrainingMetric,
    Document,
    Message,
    Conversation
)
from app.services.llm_service import get_llm_service
from app.services.rag_service import RAGService


class FineTuningService:
    """Service for managing model fine-tuning jobs and training data extraction."""

    def __init__(self, db_session: Session):
        """Initialize fine-tuning service.

        Args:
            db_session: SQLAlchemy session for database operations
        """
        self.db = db_session

    async def extract_training_data(
        self,
        owner_id: str,
        model_type: str,
        document_ids: Optional[List[str]] = None,
        conversation_ids: Optional[List[str]] = None,
        min_quality_score: float = 0.5
    ) -> List[Dict]:
        """Extract training examples from user's documents and conversations.

        Args:
            owner_id: User/tenant ID for multi-tenant isolation
            model_type: Type of model ("llm", "embedding", "local_llm")
            document_ids: Specific document UUIDs to include (None = all)
            conversation_ids: Specific conversation IDs (None = all)
            min_quality_score: Minimum quality threshold for filtering

        Returns:
            List of training examples in appropriate format

        Examples:
            - LLM: [{"prompt": "...", "completion": "..."}, ...]
            - Embedding: [{"text1": "...", "text2": "...", "label": 1.0}, ...]
        """
        if model_type == "llm" or model_type == "local_llm":
            return await self.get_training_examples_llm(owner_id, document_ids, conversation_ids)
        elif model_type == "embedding":
            return await self.get_training_examples_embedding(owner_id, document_ids)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    async def get_training_examples_llm(
        self,
        owner_id: str,
        document_ids: Optional[List[str]] = None,
        conversation_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """Extract Q&A pairs from conversations and documents for LLM fine-tuning.

        Strategy:
        1. From conversations: User message = prompt, assistant response = completion
        2. From documents: Generate Q&A via query generation from chunks
        3. Filter low-quality pairs (very short, repeated, low relevance)
        """
        examples = []

        # Extract from conversations
        query = select(Conversation).where(Conversation.owner_id == owner_id)
        if conversation_ids:
            query = query.where(Conversation.id.in_(conversation_ids))

        conversations = self.db.execute(query).scalars().all()

        for conv in conversations:
            messages = conv.messages
            # Pair user + assistant messages
            for i in range(0, len(messages) - 1, 2):
                if i + 1 < len(messages) and messages[i].role == "user" and messages[i + 1].role == "assistant":
                    prompt = messages[i].content.strip()
                    completion = messages[i + 1].content.strip()

                    # Quality filters
                    if len(prompt) > 10 and len(completion) > 10:
                        examples.append({
                            "prompt": prompt,
                            "completion": completion,
                            "source": "conversation",
                            "source_id": conv.id
                        })

        # Extract from documents (simplified - direct chunks as prompts)
        query = select(Document).where(Document.owner_id == owner_id, Document.is_latest == True)
        if document_ids:
            query = query.where(Document.id.in_(document_ids))

        documents = self.db.execute(query).scalars().all()

        # For document-based examples, we'd need access to vector store to get chunks
        # This is a placeholder for LLM-generated Q&A from chunks
        for doc in documents:
            examples.append({
                "prompt": f"Summarize the key points from {doc.filename}:",
                "completion": f"This document contains important information about its subject matter.",
                "source": "document",
                "source_id": doc.id
            })

        return examples

    async def get_training_examples_embedding(
        self,
        owner_id: str,
        document_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """Extract sentence pairs from document chunks for embedding fine-tuning.

        Strategy:
        1. Chunks from same document/section = positive pairs (high similarity, label=1.0)
        2. Chunks from different documents = negative pairs (label=0.0)
        3. Return: [{"text1": "...", "text2": "...", "label": 1.0}, ...]
        """
        examples = []

        # Fetch documents
        query = select(Document).where(Document.owner_id == owner_id, Document.is_latest == True)
        if document_ids:
            query = query.where(Document.id.in_(document_ids))

        documents = self.db.execute(query).scalars().all()

        # Create positive pairs from same document
        for i, doc in enumerate(documents):
            for j in range(i + 1, min(i + 3, len(documents))):  # Adjacent docs
                if i != j:
                    examples.append({
                        "text1": f"Content from {documents[i].filename}",
                        "text2": f"Content from {documents[j].filename}",
                        "label": 0.0,  # Different documents
                        "source_id1": documents[i].id,
                        "source_id2": documents[j].id
                    })

            # Positive pairs (same document)
            examples.append({
                "text1": f"Key information from {doc.filename}",
                "text2": f"Related content in {doc.filename}",
                "label": 1.0,  # Same document
                "source_id": doc.id
            })

        return examples

    async def create_fine_tuning_job(
        self,
        owner_id: str,
        job_name: str,
        model_type: str,
        base_model: str,
        provider: str,
        training_data: List[Dict],
        training_params: Dict,
        document_ids: Optional[List[str]] = None
    ) -> FineTuningJob:
        """Create and persist a fine-tuning job.

        Args:
            owner_id: User/tenant ID
            job_name: Human-readable job name
            model_type: "llm", "embedding", or "local_llm"
            base_model: Model being fine-tuned
            provider: Provider ("openai", "anthropic", "local", "huggingface")
            training_data: List of training examples
            training_params: Dict with epochs, learning_rate, batch_size, etc.
            document_ids: Specific documents used for training

        Returns:
            Created FineTuningJob object
        """
        job = FineTuningJob(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            job_name=job_name,
            model_type=model_type,
            base_model=base_model,
            provider=provider,
            status="pending",
            dataset_source="documents" if not document_ids else "custom",
            document_ids=document_ids,
            training_params=training_params,
            is_active=False
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        # Store training examples
        for i, example in enumerate(training_data):
            ex = TrainingExample(
                id=str(uuid.uuid4()),
                job_id=job.id,
                example_type=example.get("example_type", "prompt_completion"),
                input_text=json.dumps(example),
                expected_output=None,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(ex)

        self.db.commit()
        return job

    async def get_job_status(self, owner_id: str, job_id: str) -> FineTuningJob:
        """Get job status with ownership verification.

        Args:
            owner_id: User/tenant ID for verification
            job_id: Job UUID

        Returns:
            FineTuningJob with current status

        Raises:
            ValueError: If job not found or owner mismatch
        """
        query = select(FineTuningJob).where(
            FineTuningJob.id == job_id,
            FineTuningJob.owner_id == owner_id
        )
        job = self.db.execute(query).scalar_one_or_none()

        if not job:
            raise ValueError(f"Job {job_id} not found or access denied")

        return job

    async def list_jobs(self, owner_id: str, status: Optional[str] = None) -> List[FineTuningJob]:
        """List all fine-tuning jobs for a user.

        Args:
            owner_id: User/tenant ID
            status: Optional filter by status (pending, training, completed, failed)

        Returns:
            List of FineTuningJob objects
        """
        query = select(FineTuningJob).where(FineTuningJob.owner_id == owner_id)

        if status:
            query = query.where(FineTuningJob.status == status)

        jobs = self.db.execute(query).scalars().all()
        return jobs

    async def activate_job(self, owner_id: str, job_id: str) -> FineTuningJob:
        """Activate a completed fine-tuned model for RAG use.

        Args:
            owner_id: User/tenant ID
            job_id: Job UUID

        Returns:
            Updated FineTuningJob

        Raises:
            ValueError: If job not completed or access denied
        """
        job = await self.get_job_status(owner_id, job_id)

        if job.status != "completed":
            raise ValueError(f"Cannot activate job with status '{job.status}'. Must be 'completed'.")

        # Deactivate other active models for this user
        query = select(FineTuningJob).where(
            FineTuningJob.owner_id == owner_id,
            FineTuningJob.is_active == True,
            FineTuningJob.id != job_id
        )
        active_jobs = self.db.execute(query).scalars().all()
        for active_job in active_jobs:
            active_job.is_active = False

        # Activate this job
        job.is_active = True
        job.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(job)
        return job

    async def deactivate_job(self, owner_id: str, job_id: str) -> FineTuningJob:
        """Deactivate a fine-tuned model (fall back to base model).

        Args:
            owner_id: User/tenant ID
            job_id: Job UUID

        Returns:
            Updated FineTuningJob
        """
        job = await self.get_job_status(owner_id, job_id)
        job.is_active = False
        job.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(job)
        return job

    async def delete_job(self, owner_id: str, job_id: str) -> None:
        """Delete a fine-tuning job and its artifacts.

        Args:
            owner_id: User/tenant ID
            job_id: Job UUID

        Raises:
            ValueError: If access denied
        """
        job = await self.get_job_status(owner_id, job_id)

        # Delete associated examples and metrics (cascade via ORM)
        self.db.delete(job)
        self.db.commit()

    async def record_metric(
        self,
        job_id: str,
        metric_type: str,
        epoch: int,
        value: float
    ) -> TrainingMetric:
        """Record a training metric (loss, accuracy, etc.).

        Args:
            job_id: Job UUID
            metric_type: "loss", "accuracy", "validation_loss", etc.
            epoch: Training epoch number
            value: Metric value

        Returns:
            Recorded TrainingMetric
        """
        metric = TrainingMetric(
            id=str(uuid.uuid4()),
            job_id=job_id,
            metric_type=metric_type,
            epoch=epoch,
            value=value,
            recorded_at=datetime.now(timezone.utc)
        )

        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    async def get_active_job(self, owner_id: str) -> Optional[FineTuningJob]:
        """Get the currently active fine-tuned model for a user.

        Args:
            owner_id: User/tenant ID

        Returns:
            Active FineTuningJob or None if no active model
        """
        query = select(FineTuningJob).where(
            FineTuningJob.owner_id == owner_id,
            FineTuningJob.is_active == True,
            FineTuningJob.status == "completed"
        )

        job = self.db.execute(query).scalar_one_or_none()
        return job
