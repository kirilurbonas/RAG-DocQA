"""API routes for the document Q&A system."""

import json
import logging
import os
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.services.rag_service import RAGService
from app.services.conversation_service import ConversationService
from app.limiter import limiter
from app.security.auth import SecurityContext, get_security_context, require_stats_role
from app.security.audit import audit_event
from app.utils.safe_filename import sanitize_upload_filename

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))
AUDIT_ASK = os.getenv("AUDIT_LOG_ASK", "false").lower() == "true"
RATE_LIMIT_UPLOAD = os.getenv("RATE_LIMIT_UPLOAD", "20/hour")
RATE_LIMIT_ASK = os.getenv("RATE_LIMIT_ASK", "120/hour")
RATE_LIMIT_READ = os.getenv("RATE_LIMIT_READ", "600/hour")


# Initialize RAG service
rag_service = RAGService(
    embedding_model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
    vector_store_path=os.getenv("VECTOR_STORE_PATH", "./chroma_db"),
    llm_provider=os.getenv("LLM_PROVIDER", "openai"),
    llm_kwargs={
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    } if os.getenv("LLM_PROVIDER", "openai") == "openai" else {}
)

# Initialize conversation service
conversation_service = ConversationService(
    data_dir=os.getenv("CONVERSATIONS_DIR", "./conversations")
)

router = APIRouter()


# Request/Response models
class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: Optional[List[str]] = Field(default=None, max_length=100)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        for doc_id in value:
            try:
                UUID(doc_id)
            except ValueError as exc:
                raise ValueError(f"Invalid document_id: {doc_id}") from exc
        return value


class QuestionResponse(BaseModel):
    answer: str
    sources: List[dict]
    metadata: dict


class DocumentResponse(BaseModel):
    id: str
    filename: str
    uploaded_at: str
    chunk_count: int
    text_length: int


class StatsResponse(BaseModel):
    total_documents: int
    vector_store_documents: int
    embedding_model: str
    embedding_dimension: int


def _request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


def _public_error_message(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    return "An internal server error occurred."


@router.post("/documents/upload", response_model=DocumentResponse)
@limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    ctx: SecurityContext = Depends(get_security_context),
):
    """
    Upload and process a document.

    Supported formats: PDF, DOCX, Markdown, TXT (see backend supported extensions).
    """
    owner_id = ctx.owner_id
    try:
        content_length_header = request.headers.get("content-length")
        if content_length_header:
            try:
                cl = int(content_length_header)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid Content-Length") from None
            if cl > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="File too large")

        file_content = await file.read()
        if len(file_content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large")

        safe_name = sanitize_upload_filename(file.filename)
        document_info = await rag_service.process_and_store_document_async(
            file_content=file_content,
            filename=safe_name,
            owner_id=owner_id,
        )
        audit_event(
            "document.upload",
            subject=ctx.subject,
            tenant_id=ctx.tenant_id,
            auth_method=ctx.auth_method,
            resource_type="document",
            resource_id=document_info.get("id"),
            request_id=_request_id(request),
            extra={"filename": safe_name, "chunk_count": document_info.get("chunk_count")},
        )
        return DocumentResponse(**document_info)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to process uploaded document")
        audit_event(
            "document.upload",
            subject=ctx.subject,
            tenant_id=ctx.tenant_id,
            auth_method=ctx.auth_method,
            resource_type="document",
            outcome="failure",
            request_id=_request_id(request),
            extra={"error": type(exc).__name__},
        )
        status_code = 400 if isinstance(exc, ValueError) else 500
        raise HTTPException(status_code=status_code, detail=_public_error_message(exc))


@router.get("/documents", response_model=List[DocumentResponse])
@limiter.limit(RATE_LIMIT_READ)
async def list_documents(
    request: Request,
    q: Optional[str] = None,  # Search query (filename/text)
    ctx: SecurityContext = Depends(get_security_context),
):
    """
    Get list of all uploaded documents for this tenant/user.

    Query parameters:
    - q: Search query to filter documents by filename (partial match, case-insensitive)
    """
    documents = rag_service.get_documents(owner_id=ctx.owner_id, search_query=q)
    return [DocumentResponse(**doc) for doc in documents]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
@limiter.limit(RATE_LIMIT_READ)
async def get_document(
    request: Request,
    document_id: str,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Get a specific document by ID."""
    document = rag_service.get_document(document_id, owner_id=ctx.owner_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**document)


@router.delete("/documents/{document_id}")
@limiter.limit(RATE_LIMIT_READ)
async def delete_document(
    request: Request,
    document_id: str,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Delete a document and all its chunks."""
    success = rag_service.delete_document(document_id, owner_id=ctx.owner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    audit_event(
        "document.delete",
        subject=ctx.subject,
        tenant_id=ctx.tenant_id,
        auth_method=ctx.auth_method,
        resource_type="document",
        resource_id=document_id,
        request_id=_request_id(request),
    )
    return {"message": "Document deleted successfully"}


@router.post("/ask", response_model=QuestionResponse)
@limiter.limit(RATE_LIMIT_ASK)
async def ask_question(
    request: Request,
    body: QuestionRequest,
    ctx: SecurityContext = Depends(get_security_context),
):
    """
    Ask a question about the uploaded documents.

    The system will search for relevant information and generate an answer.
    """
    try:
        if AUDIT_ASK:
            audit_event(
                "qa.ask",
                subject=ctx.subject,
                tenant_id=ctx.tenant_id,
                auth_method=ctx.auth_method,
                request_id=_request_id(request),
                extra={"top_k": body.top_k, "scoped_docs": bool(body.document_ids)},
            )
        result = await rag_service.answer_question(
            question=body.question,
            document_ids=body.document_ids,
            top_k=body.top_k,
            owner_id=ctx.owner_id,
        )
        return QuestionResponse(**result)
    except Exception as exc:
        logger.exception("Failed to generate answer")
        raise HTTPException(status_code=500, detail=_public_error_message(exc))


@router.post("/ask/stream")
@limiter.limit(RATE_LIMIT_ASK)
async def ask_question_stream(
    request: Request,
    body: QuestionRequest,
    ctx: SecurityContext = Depends(get_security_context),
):
    """
    Ask a question and stream the response.

    Returns a streaming response with answer tokens.
    """
    if AUDIT_ASK:
        audit_event(
            "qa.ask_stream",
            subject=ctx.subject,
            tenant_id=ctx.tenant_id,
            auth_method=ctx.auth_method,
            request_id=_request_id(request),
            extra={"top_k": body.top_k, "scoped_docs": bool(body.document_ids)},
        )

    async def generate():
        try:
            async for token in rag_service.stream_answer(
                question=body.question,
                document_ids=body.document_ids,
                top_k=body.top_k,
                owner_id=ctx.owner_id,
            ):
                # JSON-encode token to preserve newlines and special characters
                payload = json.dumps({"token": token, "error": None})
                yield f"data: {payload}\n\n"
        except Exception as exc:
            logger.exception("Failed to stream answer")
            # Send error as structured JSON
            error_payload = json.dumps({"token": None, "error": str(exc)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/stats", response_model=StatsResponse)
@limiter.limit(RATE_LIMIT_READ)
async def get_stats(
    request: Request,
    ctx: SecurityContext = Depends(require_stats_role),
):
    """Get service statistics (may require elevated roles in enterprise configs)."""
    stats = rag_service.get_stats(owner_id=ctx.owner_id)
    audit_event(
        "stats.read",
        subject=ctx.subject,
        tenant_id=ctx.tenant_id,
        auth_method=ctx.auth_method,
        request_id=_request_id(request),
    )
    return StatsResponse(**stats)


# Conversation History Endpoints

@router.post("/conversations", response_model=dict)
@limiter.limit(RATE_LIMIT_READ)
async def create_conversation(
    request: Request,
    title: Optional[str] = None,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Create a new conversation for storing Q&A history."""
    conv_id = conversation_service.create_conversation(owner_id=ctx.owner_id, title=title)
    return {
        "id": conv_id,
        "title": title or f"Conversation {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message_count": 0
    }


@router.get("/conversations", response_model=List[dict])
@limiter.limit(RATE_LIMIT_READ)
async def list_conversations(
    request: Request,
    limit: int = 10,
    offset: int = 0,
    ctx: SecurityContext = Depends(get_security_context),
):
    """List conversations for the current user."""
    conversations = conversation_service.list_conversations(
        owner_id=ctx.owner_id, limit=limit, offset=offset
    )
    return conversations


@router.get("/conversations/{conversation_id}", response_model=dict)
@limiter.limit(RATE_LIMIT_READ)
async def get_conversation(
    request: Request,
    conversation_id: str,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Get conversation details including message history."""
    conversation = conversation_service.get_conversation(
        owner_id=ctx.owner_id, conversation_id=conversation_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/conversations/{conversation_id}/messages", response_model=dict)
@limiter.limit(RATE_LIMIT_ASK)
async def add_message_to_conversation(
    request: Request,
    conversation_id: str,
    role: str,
    content: str,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Add a message to conversation history."""
    if role not in ["user", "assistant"]:
        raise HTTPException(status_code=400, detail="role must be 'user' or 'assistant'")

    success = conversation_service.add_message(
        owner_id=ctx.owner_id,
        conversation_id=conversation_id,
        role=role,
        content=content
    )

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "added", "role": role, "conversation_id": conversation_id}


@router.delete("/conversations/{conversation_id}", response_model=dict)
@limiter.limit(RATE_LIMIT_READ)
async def delete_conversation(
    request: Request,
    conversation_id: str,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Delete a conversation and its history."""
    success = conversation_service.delete_conversation(
        owner_id=ctx.owner_id, conversation_id=conversation_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "conversation_id": conversation_id}


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns 200 if all systems are ready, 503 if any system is unavailable.
    """
    health_status = {
        "status": "healthy",
        "service": "rag-docqa",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    try:
        # Check embedding model
        await rag_service.embedding_model.encode_async("health")
        health_status["checks"]["embedding_model"] = "ok"
    except Exception as e:
        health_status["checks"]["embedding_model"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        logger.warning(f"Embedding model health check failed: {e}")

    try:
        # Check vector store (Chroma)
        count = rag_service.vector_store.get_collection_stats()
        health_status["checks"]["vector_store"] = "ok"
    except Exception as e:
        health_status["checks"]["vector_store"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        logger.warning(f"Vector store health check failed: {e}")

    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503

    from fastapi import Response
    return Response(
        content=json.dumps(health_status),
        status_code=status_code,
        media_type="application/json"
    )
