"""Pytest configuration and shared fixtures."""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ["OPENAI_API_KEY"] = "test-key-sk-proj-12345"
os.environ["AUTH_MODE"] = "jwt_or_api_key"
os.environ["JWT_SECRET"] = "test-secret-key"


@pytest.fixture
def temp_vector_store():
    """Create a temporary vector store directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_client(temp_vector_store):
    """Create a test client with temporary vector store."""
    with patch.dict(os.environ, {"VECTOR_STORE_PATH": temp_vector_store}):
        from app.main import app
        return TestClient(app)


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing."""
    with patch("app.services.llm_service.AsyncOpenAI") as mock:
        mock_instance = AsyncMock()
        mock.return_value = mock_instance
        mock_instance.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content="Test response"))]
            )
        )
        yield mock_instance


@pytest.fixture
def sample_pdf_bytes():
    """Create sample PDF bytes for testing."""
    # Minimal valid PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< >>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000232 00000 n
0000000337 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
429
%%EOF"""
    return pdf_content


@pytest.fixture
def sample_text_bytes():
    """Create sample text bytes for testing."""
    return b"This is a test document.\nIt contains some sample text for testing purposes."


@pytest.fixture
def sample_docx_bytes():
    """Create a minimal valid DOCX file."""
    # This is a very basic DOCX structure (ZIP file)
    import zipfile
    import io

    docx_buffer = io.BytesIO()
    with zipfile.ZipFile(docx_buffer, 'w') as docx:
        # Minimal _rels/.rels
        docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

        # Minimal word/document.xml
        docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:t>Test paragraph</w:t></w:r></w:p>
</w:body>
</w:document>''')

        # Minimal [Content_Types].xml
        docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

    return docx_buffer.getvalue()
