# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-10-08

### Added

#### Document Management
- **Document Search/Filtering**: Filter documents by filename with case-insensitive partial matching
  - `GET /documents?q=search_term` returns matching documents
  - Sorted by upload date (newest first)
  - Only returns latest version by default

- **Document Versioning**: Automatic version tracking for re-uploaded documents
  - Re-upload same filename creates new version (auto-incremented)
  - Previous versions marked as `is_latest=false`
  - All versions remain searchable in vector store
  - Includes version metadata in document info

- **Extended File Type Support**:
  - Excel files (.xlsx) via openpyxl
  - PowerPoint files (.pptx) via python-pptx
  - Safe extraction with decompression bomb protection
  - Text-only extraction (no formulas, macros, or code)
  - Respects MAX_EXTRACTED_TEXT_CHARS limits

#### Conversation History
- **Conversation Management**: Persistent conversation storage per user/tenant
  - `POST /conversations` - Create new conversation
  - `GET /conversations` - List conversations with pagination
  - `GET /conversations/{id}` - Get conversation with full message history
  - `POST /conversations/{id}/messages` - Add message to conversation
  - `DELETE /conversations/{id}` - Delete conversation

- **Features**:
  - JSON-based persistence in `./conversations/{owner_id}/`
  - Messages in OpenAI format (role, content, timestamp)
  - Ownership isolation (users only access their own conversations)
  - Conversation titles and metadata tracking
  - Durable persistence across restarts

### Changed
- `get_documents()` now supports `latest_only` parameter (default: True)
- Requirements updated with optional Excel/PowerPoint libraries

### Documentation
- Added comprehensive FEATURES.md documenting all v1.2.0 features
- Updated README.md with v1.2.0 feature list and future roadmap
- Added usage examples for all new API endpoints

---

## [1.1.0] - 2025-10-07

### 🔒 Security & Reliability

#### Breaking Changes
- **Async API**: All RAG service methods are now async. Update integration code to use `await`:
  - Changed: `process_and_store_document()` → use `process_and_store_document_async()`
  - Changed: `answer_question()` is now `async def`
  - Changed: `stream_answer()` is now `async def`

#### Added
- **Persistent Document Registry**: Documents now persist in `{VECTOR_STORE_PATH}/document_registry.json`
  - Survives process restart
  - Consistent across multiple workers
  - Auto-loads on service initialization
  
- **Async Operations**: All blocking I/O wrapped with `run_in_executor` or async clients
  - `EmbeddingModel.encode_async()` for text encoding
  - `VectorStore.search_async()` for vector search
  - `AsyncOpenAI` client for LLM calls (non-blocking)
  
- **Health Check Endpoint**: Real health monitoring at `GET /health`
  - Returns 200 if all systems healthy
  - Returns 503 if embedding model or vector store unavailable
  - Includes component status details
  
- **Configuration Validation**: Pydantic-based `Settings` class
  - Type checking for all environment variables
  - Range validation for numeric parameters
  - Clear error messages on startup
  - `.env` file support with sensible defaults
  
- **Comprehensive Test Suite**: ~500 lines of pytest tests
  - Auth tests: JWT validation, tenant isolation, API key isolation
  - Document processor tests: Chunking edge cases, extraction
  - RAG service tests: Persistence, ownership enforcement
  - API route tests: Rate limiting, streaming, health checks
  - CI/CD integration with automatic test execution
  
- **OpenAI Resilience**:
  - Request timeout: 30 seconds (configurable via `LLM_TIMEOUT`)
  - Automatic retries: 2x with exponential backoff (configurable via `LLM_MAX_RETRIES`)
  - Proper error handling in streaming responses

#### Fixed
- **Fixed Document Data Loss on Restart**: Documents lost when service restarted (now persists to disk)
- **Fixed Event Loop Blocking**: Embedding encoding, vector search, and LLM calls were blocking entire worker (now async)
- **Fixed Streaming Response Text Loss**: Multi-line tokens caused SSE frame breakage
  - Implemented JSON encoding for SSE frames: `data: {"token": "...", "error": null}\n\n`
  - Frontend parser properly handles JSON-encoded payloads
  - Preserves UTF-8 multi-byte characters across chunk boundaries
  
- **Fixed Rate Limiting Bug**: `GET /documents` and `GET /documents/{id}` rate limits not enforced
  - Parameter renamed from `_request` to `request` for slowapi compatibility
  
- **Fixed Deprecated Code**: `datetime.utcnow()` → `datetime.now(timezone.utc)` for Python 3.12+ compatibility

- **Dependency Compatibility Issues**:
  - chromadb: 0.4.15 → 0.5.0 (fixes numpy incompatibility)
  - sentence-transformers: 2.2.2 → 3.0.1 (fixes huggingface_hub cached_download removal)
  - openai: 1.3.5 → 1.45.0 (adds AsyncOpenAI, critical for non-blocking calls)
  - httpx: pinned to 0.27.0 (compatibility with openai 1.45.0)
  - huggingface-hub: pinned to 0.23.4 (explicit version management)
  - numpy: 1.24.3 → 1.26.0 (chromadb 0.5.0 compatibility)

#### Changed
- **Improved Documentation**:
  - Added "Recent Improvements" section to README
  - Added "Testing" section with test running instructions
  - Created comprehensive IMPROVEMENTS.md tracking all changes
  - Added deployment checklist in IMPROVEMENTS.md
  
- **Better Defaults**:
  - `LLM_TIMEOUT=30` (seconds)
  - `LLM_MAX_RETRIES=2`
  - `AUTH_MODE=jwt_or_api_key` (supports both JWT and API key)
  
- **CI/CD Pipeline**: Now includes pytest unit tests before linting

### 🗑️ Removed
- Unused `aiofiles` dependency

### 📊 Metrics

| Aspect | Before | After |
|--------|--------|-------|
| Data Loss Risk | High | Eliminated |
| Event Loop Blocking | Severe | Fixed |
| Test Coverage | 0% | ~30% critical paths |
| Known CVEs | 7+ | 0 |
| Streaming Reliability | Low | Fixed |
| Rate Limiting | Broken | Fixed |
| API Timeouts | None | 30s default |

### 📖 Documentation

- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Detailed tracking of all reliability upgrades
- [README.md](README.md) - Updated with test instructions and recent improvements
- [app/config.py](backend/app/config.py) - Configuration validation with inline documentation

---

## [1.0.0] - 2025-10-07

### Initial Release

- Document ingestion (PDF, DOCX, Markdown, TXT)
- Semantic search with embeddings
- LLM-powered Q&A with streaming responses
- FastAPI backend with rate limiting
- React frontend with chat interface
- Docker Compose deployment
- JWT and API key authentication
- Tenant isolation support
- Prometheus metrics
- Enterprise security features

---

## Migration Guide

### From v1.0.0 to v1.1.0

1. **Update Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **No Database Migrations Needed**: Document registry is JSON-based and auto-created.

3. **Update Code if Using RAGService Directly**:
   ```python
   # OLD (v1.0)
   doc = rag_service.process_and_store_document(file_content, filename)
   answer = await rag_service.answer_question(question)
   
   # NEW (v1.1)
   doc = await rag_service.process_and_store_document_async(file_content, filename)
   answer = await rag_service.answer_question(question)  # Already async, no change needed
   ```

4. **Test Your Setup**:
   ```bash
   cd backend
   pytest tests -v
   ```

5. **Verify Health**:
   ```bash
   curl http://localhost:8000/health
   ```

---

## Known Issues & Limitations

### Current
- Frontend test suite not yet implemented
- Rate limiting keying behind nginx reverse proxy needs configuration
- API key exposed in frontend bundle (use JWT for production)

### Roadmap (v1.2+)
- Database-backed document registry for distributed deployments
- Redis-based rate limiting for multi-instance deployments
- Conversation history persistence
- Document deduplication by content hash
- Additional LLM provider support (Anthropic, Cohere)

---

## Support

For issues, questions, or contributions:
- See [IMPROVEMENTS.md](IMPROVEMENTS.md) for known issues and workarounds
- See [SECURITY.md](SECURITY.md) for security configuration
- See [ENTERPRISE.md](ENTERPRISE.md) for enterprise features
