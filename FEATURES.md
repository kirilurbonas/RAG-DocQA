# RAG-DocQA Features Documentation

## v1.2.0 Features (NEW)

### 1. Document Search & Filtering

**Overview**: Search uploaded documents by filename without downloading or manually browsing.

**API**:
```bash
# Search for documents matching a filename pattern (case-insensitive)
GET /api/v1/documents?q=invoice

# Supports partial matching
GET /api/v1/documents?q=2024
```

**Response**:
```json
[
  {
    "id": "doc-uuid",
    "filename": "invoice_2024_01.pdf",
    "uploaded_at": "2026-10-08T10:30:00Z",
    "chunk_count": 42,
    "text_length": 15234,
    "version": 1,
    "is_latest": true
  }
]
```

**Features**:
- Case-insensitive partial matching on filename
- Sorted by upload date (newest first)
- Only returns latest version by default
- Filters by owner/tenant automatically
- Works with all file types

**Frontend Integration**:
```javascript
// In DocumentList component
const searchDocuments = async (query) => {
  const response = await api.get('/documents', { params: { q: query } });
  return response.data;
};
```

---

### 2. Document Versioning

**Overview**: Automatically track multiple versions of documents with same filename. Useful for:
- Tracking document updates over time
- Querying historical versions
- Comparing versions of same document

**How It Works**:
1. Upload `report.pdf` → creates version 1
2. Upload `report.pdf` again → creates version 2, marks v1 as not-latest
3. Both versions stay in vector store and are queryable
4. Search/list only shows latest by default

**API**:

```bash
# Upload document (auto-versioning)
POST /api/v1/documents/upload
Content-Type: multipart/form-data
file=report.pdf

# Response includes version info
{
  "id": "doc-uuid",
  "filename": "report.pdf",
  "version": 2,
  "is_latest": true,
  "uploaded_at": "2026-10-08T10:35:00Z"
}

# Get all versions of a document (including old ones)
GET /api/v1/documents?q=report.pdf&latest_only=false

# Get a specific version by ID
GET /api/v1/documents/{doc-id}
```

**Metadata**:
- `version`: Integer version number (auto-incremented per filename)
- `is_latest`: Boolean, true only for newest version
- All versions remain searchable in vector store
- Chunk IDs include document ID (not version), so chunks aren't duplicated

**Use Cases**:
- Contract updates: track version history
- Report iterations: compare versions
- Data corrections: keep audit trail
- Compliance: maintain version record

---

### 3. More File Type Support

**Supported Formats** (v1.2.0):
- PDF (.pdf) ← existing
- DOCX (.docx) ← existing
- Markdown (.md, .markdown) ← existing
- TXT (.txt) ← existing
- **NEW: Excel (.xlsx)** ← openpyxl
- **NEW: PowerPoint (.pptx)** ← python-pptx

**Excel (.xlsx) Support**:
```bash
POST /api/v1/documents/upload
Content-Type: multipart/form-data
file=data.xlsx

# Extracts:
# - All cells from all sheets
# - Sheet names as markers ("Sheet: Sheet1", "Sheet: Sheet2")
# - Cell values separated by " | "
# - Respects MAX_EXTRACTED_TEXT_CHARS limit
```

**Example Extraction**:
```
Sheet: Sales
Date | Product | Amount
2024-01-01 | Widget | 100
2024-01-02 | Gadget | 150
...
```

**PowerPoint (.pptx) Support**:
```bash
POST /api/v1/documents/upload
Content-Type: multipart/form-data
file=presentation.pptx

# Extracts:
# - Text from all shapes on all slides
# - Slide numbers as markers ("--- Slide 1 ---")
# - Preserves text order within slides
# - Respects MAX_EXTRACTED_TEXT_CHARS limit
```

**Example Extraction**:
```
--- Slide 1 ---
Welcome to My Presentation
Company Name

--- Slide 2 ---
Key Points
- Point 1
- Point 2
...
```

**Installation**:
```bash
# Install optional file type support
pip install openpyxl python-pptx
```

**Security**:
- Zip bomb protection: enforces MAX_EXTRACTED_TEXT_CHARS
- No external formula evaluation (data_only=True for Excel)
- Text extraction only (no macros, VBA, or code execution)
- Safe handling of corrupted files (returns error, not crash)

**Limitations**:
- Excel: Extracts cell values only (not formulas, charts, or pivot tables)
- PowerPoint: Extracts text only (not speaker notes or embedded media)
- Both: Formatted text converted to plain text

---

### 4. Conversation History Persistence

**Overview**: Store and manage Q&A conversation history per user/tenant. Useful for:
- Building context from previous questions
- Reviewing past conversations
- Sharing conversation history
- Analytics on user queries

**Key Endpoints**:

#### Create Conversation
```bash
POST /api/v1/conversations
Content-Type: application/json
{
  "title": "Q4 Revenue Analysis"  # optional
}

# Response:
{
  "id": "conv-uuid",
  "title": "Q4 Revenue Analysis",
  "created_at": "2026-10-08T10:30:00Z",
  "message_count": 0
}
```

#### List Conversations
```bash
GET /api/v1/conversations?limit=10&offset=0

# Response:
[
  {
    "id": "conv-uuid",
    "title": "Q4 Revenue Analysis",
    "created_at": "2026-10-08T10:30:00Z",
    "updated_at": "2026-10-08T10:35:00Z",
    "message_count": 5
  }
]
```

#### Get Conversation (with Full History)
```bash
GET /api/v1/conversations/{conversation-id}

# Response:
{
  "id": "conv-uuid",
  "title": "Q4 Revenue Analysis",
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
```

#### Add Message to Conversation
```bash
POST /api/v1/conversations/{conversation-id}/messages
Content-Type: application/json
{
  "role": "user",  # or "assistant"
  "content": "What was the growth rate?"
}

# Response:
{
  "status": "added",
  "role": "user",
  "conversation_id": "conv-uuid"
}
```

#### Delete Conversation
```bash
DELETE /api/v1/conversations/{conversation-id}

# Response:
{
  "status": "deleted",
  "conversation_id": "conv-uuid"
}
```

**Data Format**:
- Messages stored in OpenAI format (role: "user" | "assistant", content: string)
- Timestamps included for all messages
- Supports pagination for large conversations (limit/offset)
- Thread-safe JSON storage per owner

**Usage Example (Frontend)**:
```javascript
// Create new conversation
const conv = await api.post('/conversations', { title: 'Analysis' });

// Add user message
await api.post(`/conversations/${conv.id}/messages`, {
  role: 'user',
  content: 'Analyze this data'
});

// Ask question (with optional conversation context)
const answer = await api.post('/ask/stream', {
  question: 'What patterns do you see?',
  conversation_id: conv.id  // future enhancement
});

// Add assistant response
await api.post(`/conversations/${conv.id}/messages`, {
  role: 'assistant',
  content: answer
});

// List past conversations
const conversations = await api.get('/conversations');
```

**Storage**:
- JSON files stored in `./conversations/{owner_id}/`
- One file per conversation: `{conversation-id}.json`
- Automatic directory creation per owner
- Durable persistence across restarts
- No database required

**Security**:
- Ownership isolation: users only access their own conversations
- All queries filtered by owner_id
- No cross-tenant data leakage

**Future Enhancements** (planned for v1.3):
- Integrate history into LLM context (feed previous messages into prompt)
- Export conversation to PDF/Markdown
- Conversation sharing (per-message access control)
- Search within conversation history
- Conversation tags/labels

---

## v1.1.0 Features (Reliability)

See [CHANGELOG.md](CHANGELOG.md#v110---2025-10-07) for v1.1.0 reliability improvements:
- Persistent document registry
- Non-blocking async operations  
- Fixed streaming protocol
- OpenAI timeouts and retries
- Real health checks

---

## v1.0.0 Features (Foundation)

Core RAG-DocQA features:
- Document upload and processing
- Vector embedding and semantic search
- LLM-powered Q&A with streaming
- Source citations
- Multi-user/tenant isolation via JWT or API key
- Rate limiting
- Enterprise auth options
- Audit logging
- Docker deployment

---

## Configuration

### New Environment Variables (v1.2.0)

```bash
# Conversations directory
CONVERSATIONS_DIR=./conversations

# File type support (no explicit config needed; libs optional)
# Install openpyxl and python-pptx to enable Excel/PowerPoint support
```

### File Size Limits
```bash
# Already configured (unchanged from v1.1.0)
MAX_UPLOAD_BYTES=10485760  # 10 MB
MAX_EXTRACTED_TEXT_CHARS=5000000  # 5 MB text after extraction
MAX_PDF_PAGES=500
```

---

## API Versioning

- Current API: `/api/v1`
- All features available under `/api/v1/`
- Backward compatible with v1.0.0 and v1.1.0

---

## Testing

Feature testing added in unit tests:
- Document search functionality
- Version tracking on re-upload
- Conversation CRUD operations
- File type extraction (when libraries available)
- Ownership isolation for all features

Run tests:
```bash
cd backend
pytest tests -v -k "search or conversation or versioning or xlsx or pptx"
```
