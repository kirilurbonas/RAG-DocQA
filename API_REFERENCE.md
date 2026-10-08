# RAG-DocQA API Reference (v1)

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All endpoints require authentication via:
- **JWT Bearer Token**: `Authorization: Bearer <token>`
- **API Key**: `X-API-Key: <key>` header
- Set `AUTH_MODE=jwt_or_api_key` (default) to support both

## Pagination
List endpoints support pagination with:
- `limit`: Max items to return (default: 10)
- `offset`: Offset for pagination (default: 0)

---

## Documents

### Upload Document
```
POST /documents/upload
Content-Type: multipart/form-data

Parameters:
  file: File to upload (PDF, DOCX, XLSX, PPTX, MD, TXT)

Response (201):
{
  "id": "uuid",
  "filename": "report.pdf",
  "uploaded_at": "2026-10-08T10:30:00Z",
  "chunk_count": 42,
  "text_length": 15234,
  "version": 1,
  "is_latest": true
}

Errors:
  400: File too large or unsupported type
  413: Payload Too Large
```

### List Documents
```
GET /documents?q=search&latest_only=true&limit=10&offset=0

Query Parameters:
  q: Search filename (case-insensitive, optional)
  latest_only: Return only latest version (default: true)
  limit: Max results (default: 10)
  offset: Pagination offset (default: 0)

Response (200):
[
  {
    "id": "uuid",
    "filename": "report.pdf",
    "uploaded_at": "2026-10-08T10:30:00Z",
    "chunk_count": 42,
    "text_length": 15234,
    "version": 1,
    "is_latest": true
  }
]
```

### Get Document
```
GET /documents/{document_id}

Response (200):
{
  "id": "uuid",
  "filename": "report.pdf",
  "uploaded_at": "2026-10-08T10:30:00Z",
  "chunk_count": 42,
  "text_length": 15234,
  "version": 2,
  "is_latest": true
}

Errors:
  404: Document not found
```

### Delete Document
```
DELETE /documents/{document_id}

Response (200):
{
  "message": "Document deleted successfully"
}

Errors:
  404: Document not found
```

---

## Q&A

### Ask Question
```
POST /ask
Content-Type: application/json

{
  "question": "What was Q4 revenue?",
  "document_ids": ["uuid1", "uuid2"],  // optional, search all if omitted
  "top_k": 5  // number of chunks to retrieve (1-20, default: 5)
}

Response (200):
{
  "answer": "Q4 revenue was $2.5M, up 15% YoY...",
  "sources": [
    {
      "document_id": "uuid1",
      "filename": "report.pdf",
      "chunks": [
        {
          "chunk_id": "chunk-1",
          "text": "Q4 revenue reached $2.5M...",
          "distance": 0.12
        }
      ]
    }
  ],
  "metadata": {
    "chunks_retrieved": 3,
    "question": "What was Q4 revenue?"
  }
}

Errors:
  400: Invalid document_ids or question
  500: LLM error
```

### Stream Question
```
POST /ask/stream
Content-Type: application/json

Same request body as /ask

Response (200): text/event-stream
data: {"token": "Q4", "error": null}
data: {"token": " revenue", "error": null}
data: {"token": " was", "error": null}
...

Errors:
  400: Invalid input
  500: Streaming error (sent as final SSE message)
```

---

## Conversations

### Create Conversation
```
POST /conversations
Content-Type: application/json

{
  "title": "Q4 Analysis"  // optional
}

Response (200):
{
  "id": "conv-uuid",
  "title": "Q4 Analysis",
  "created_at": "2026-10-08T10:30:00Z",
  "message_count": 0
}
```

### List Conversations
```
GET /conversations?limit=10&offset=0

Query Parameters:
  limit: Max conversations (default: 10)
  offset: Pagination offset (default: 0)

Response (200):
[
  {
    "id": "conv-uuid",
    "title": "Q4 Analysis",
    "created_at": "2026-10-08T10:30:00Z",
    "updated_at": "2026-10-08T10:35:00Z",
    "message_count": 5
  }
]
```

### Get Conversation
```
GET /conversations/{conversation_id}

Response (200):
{
  "id": "conv-uuid",
  "title": "Q4 Analysis",
  "created_at": "2026-10-08T10:30:00Z",
  "updated_at": "2026-10-08T10:35:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What was Q4 revenue?",
      "timestamp": "2026-10-08T10:31:00Z"
    },
    {
      "role": "assistant",
      "content": "Q4 revenue was $2.5M...",
      "timestamp": "2026-10-08T10:31:05Z"
    }
  ]
}

Errors:
  404: Conversation not found
```

### Add Message to Conversation
```
POST /conversations/{conversation_id}/messages
Content-Type: application/json

{
  "role": "user",  // or "assistant"
  "content": "What was the growth rate?"
}

Response (200):
{
  "status": "added",
  "role": "user",
  "conversation_id": "conv-uuid"
}

Errors:
  400: Invalid role (must be 'user' or 'assistant')
  404: Conversation not found
```

### Delete Conversation
```
DELETE /conversations/{conversation_id}

Response (200):
{
  "status": "deleted",
  "conversation_id": "conv-uuid"
}

Errors:
  404: Conversation not found
```

---

## Statistics

### Get Stats
```
GET /stats

Response (200):
{
  "total_documents": 42,
  "vector_store_documents": 42,
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_dimension": 384
}

Note: May require specific role if STATS_ALLOWED_ROLES is configured
```

---

## Health Check

### Health Check
```
GET /health

Response (200):
{
  "status": "healthy",
  "service": "rag-docqa",
  "timestamp": "2026-10-08T10:30:00Z",
  "checks": {
    "embedding_model": "ok",
    "vector_store": "ok"
  }
}

Response (503 - Service Unavailable):
{
  "status": "degraded",
  "service": "rag-docqa",
  "timestamp": "2026-10-08T10:30:00Z",
  "checks": {
    "embedding_model": "ok",
    "vector_store": "error: Connection failed"
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

Common HTTP Status Codes:
- **200**: Success
- **400**: Bad request (invalid parameters)
- **401**: Unauthorized (missing/invalid auth)
- **403**: Forbidden (insufficient permissions)
- **404**: Not found
- **413**: Payload too large
- **429**: Rate limited
- **500**: Internal server error
- **503**: Service unavailable

---

## Rate Limiting

Default limits (configurable via environment):
- **Upload**: 20 requests/hour per user
- **Ask/Stream**: 120 requests/hour per user
- **Read** (Documents, Conversations, Stats): 600 requests/hour per user

Response header includes rate limit info:
```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 599
X-RateLimit-Reset: 1728414600
```

---

## File Format Support

### Supported Upload Formats
- **PDF** (.pdf) - Text extraction via PyPDF2
- **Word** (.docx) - Text extraction via python-docx
- **Excel** (.xlsx) - Cell extraction via openpyxl
- **PowerPoint** (.pptx) - Text extraction via python-pptx
- **Markdown** (.md, .markdown) - HTML to text conversion
- **Plain Text** (.txt) - Direct UTF-8 decoding

### Size Limits
- Max file size: 10 MB (configurable: MAX_UPLOAD_BYTES)
- Max extracted text: 5 MB (configurable: MAX_EXTRACTED_TEXT_CHARS)
- Max PDF pages: 500 (configurable: MAX_PDF_PAGES)

---

## Searching

### Document Search
Documents support partial filename search with case-insensitive matching:

```bash
GET /documents?q=invoice  # returns invoice_2024.pdf, old_invoices.xlsx, etc.
GET /documents?q=2024     # returns all documents with 2024 in filename
```

### Vector Search (in Q&A)
Vector similarity search is performed automatically when asking questions:
- Retrieves top-k most relevant chunks
- Configurable via `top_k` parameter (1-20)
- Uses cosine similarity on embeddings

---

## Versioning

Documents support versioning automatically:
- Same filename re-upload creates new version
- Versions auto-incremented (1, 2, 3, ...)
- All versions remain searchable
- `is_latest` field indicates current version

Example:
```
Upload report.pdf (v1)
Upload report.pdf (v2) - marks v1 as is_latest=false
Upload report.pdf (v3) - marks v1, v2 as is_latest=false

GET /documents?q=report.pdf         # Returns v3 (latest_only=true by default)
GET /documents?q=report.pdf&latest_only=false  # Returns v1, v2, v3
```

---

## Webhooks & Events

Currently not implemented. Future enhancement for:
- Document upload notifications
- Conversation updates
- Async processing status

---

## SDKs & Clients

### Python
```python
import requests

client = requests.Session()
client.headers.update({
    'Authorization': f'Bearer {token}',  # or 'X-API-Key': api_key
})

# Upload document
with open('report.pdf', 'rb') as f:
    response = client.post(
        'http://localhost:8000/api/v1/documents/upload',
        files={'file': f}
    )
    doc = response.json()

# Ask question
response = client.post(
    'http://localhost:8000/api/v1/ask',
    json={'question': 'What was Q4 revenue?'}
)
answer = response.json()
```

### JavaScript
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Authorization': `Bearer ${token}`,  // or 'X-API-Key': apiKey
  }
});

// Upload document
const formData = new FormData();
formData.append('file', file);
const doc = await api.post('/documents/upload', formData);

// Ask question
const answer = await api.post('/ask', {
  question: 'What was Q4 revenue?'
});
```

---

## OpenAPI/Swagger

Swagger UI available at: `http://localhost:8000/docs`
ReDoc available at: `http://localhost:8000/redoc`

---

## Changes by Version

- **v1.2.0**: Added document search, versioning, new file types, conversation management
- **v1.1.0**: Persistent document registry, async operations, streaming fix, health checks
- **v1.0.0**: Initial release with document upload, Q&A, multi-user support
