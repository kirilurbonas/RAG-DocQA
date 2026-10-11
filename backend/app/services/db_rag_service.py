"""Database-backed RAG service for document management (Phase 2+)."""

import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.models import Document

logger = logging.getLogger(__name__)


class DbDocumentService:
    """Document management using SQLite database backend."""

    def __init__(self, db: Session):
        """
        Initialize database document service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_document(
        self,
        document_id: str,
        owner_id: str,
        filename: str,
        chunk_count: int,
        text_length: int,
        version: int = 1
    ) -> Dict:
        """
        Create document metadata record.

        Args:
            document_id: Document UUID
            owner_id: Owner/tenant ID
            filename: Original filename
            chunk_count: Number of chunks
            text_length: Total text length
            version: Version number

        Returns:
            Document dict
        """
        # Mark previous versions as not latest
        if version > 1:
            previous_docs = self.db.query(Document).filter(
                Document.owner_id == owner_id,
                Document.filename == filename,
                Document.is_latest == True
            ).all()
            for doc in previous_docs:
                doc.is_latest = False

        document = Document(
            id=document_id,
            owner_id=owner_id,
            filename=filename,
            version=version,
            is_latest=True,
            chunk_count=chunk_count,
            text_length=text_length
        )
        self.db.add(document)
        self.db.commit()

        logger.info(f"Created document {document_id} (v{version}) for owner {owner_id}")

        return self._to_dict(document)

    def list_documents(
        self,
        owner_id: str,
        search_query: Optional[str] = None,
        latest_only: bool = True
    ) -> List[Dict]:
        """
        List documents for owner with optional search and filtering.

        Args:
            owner_id: Owner/tenant ID
            search_query: Optional filename search (case-insensitive)
            latest_only: Only return latest versions

        Returns:
            List of document dicts
        """
        query = self.db.query(Document).filter(Document.owner_id == owner_id)

        if latest_only:
            query = query.filter(Document.is_latest == True)

        if search_query:
            search_lower = search_query.lower()
            query = query.filter(Document.filename.ilike(f"%{search_lower}%"))

        documents = query.order_by(Document.uploaded_at.desc()).all()

        return [self._to_dict(doc) for doc in documents]

    def get_document(self, document_id: str, owner_id: str) -> Optional[Dict]:
        """
        Get specific document by ID.

        Args:
            document_id: Document ID
            owner_id: Owner/tenant ID (for ownership check)

        Returns:
            Document dict or None if not found
        """
        document = self.db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == owner_id
        ).first()

        return self._to_dict(document) if document else None

    def delete_document(self, document_id: str, owner_id: str) -> bool:
        """
        Delete document and all its versions.

        Args:
            document_id: Document ID
            owner_id: Owner/tenant ID (for ownership check)

        Returns:
            True if deleted, False if not found
        """
        document = self.db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == owner_id
        ).first()

        if not document:
            return False

        self.db.delete(document)
        self.db.commit()

        return True

    def get_documents_by_filename(
        self,
        owner_id: str,
        filename: str
    ) -> List[Dict]:
        """
        Get all versions of a document by filename.

        Args:
            owner_id: Owner/tenant ID
            filename: Filename to search for

        Returns:
            List of document dicts (all versions)
        """
        documents = self.db.query(Document).filter(
            Document.owner_id == owner_id,
            Document.filename == filename
        ).order_by(Document.version.desc()).all()

        return [self._to_dict(doc) for doc in documents]

    @staticmethod
    def _to_dict(document: Document) -> Dict:
        """Convert document ORM object to dict."""
        if not document:
            return None

        return {
            "id": document.id,
            "filename": document.filename,
            "version": document.version,
            "is_latest": document.is_latest,
            "chunk_count": document.chunk_count,
            "text_length": document.text_length,
            "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
            "owner_id": document.owner_id
        }
