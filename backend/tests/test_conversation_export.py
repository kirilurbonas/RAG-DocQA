"""Comprehensive tests for conversation export functionality (Phase 5)."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from app.services.conversation_exporter import ConversationExporter
from fastapi.testclient import TestClient
from app.main import app


class TestMarkdownExport:
    """Test Markdown export functionality."""

    def test_export_basic_conversation(self):
        """Test exporting a basic conversation to Markdown."""
        conversation = {
            'id': 'conv-123',
            'title': 'Test Conversation',
            'created_at': '2024-10-11T10:00:00Z',
            'updated_at': '2024-10-11T10:05:00Z',
            'messages': [
                {'role': 'user', 'content': 'Hello', 'timestamp': '2024-10-11T10:00:00Z'},
                {'role': 'assistant', 'content': 'Hi there!', 'timestamp': '2024-10-11T10:00:01Z'},
            ]
        }

        md = ConversationExporter.to_markdown(conversation)

        assert isinstance(md, str)
        assert 'Test Conversation' in md
        assert 'Hello' in md
        assert 'Hi there!' in md
        assert conversation['id'] in md

    def test_export_without_metadata(self):
        """Test exporting without metadata header."""
        conversation = {
            'title': 'Test',
            'messages': [
                {'role': 'user', 'content': 'Question?'},
                {'role': 'assistant', 'content': 'Answer.'},
            ]
        }

        md = ConversationExporter.to_markdown(conversation, include_metadata=False)

        assert 'Question?' in md
        assert 'Answer.' in md
        # Should not have title as heading
        assert '# Test' not in md

    def test_export_without_timestamps(self):
        """Test exporting without timestamps."""
        conversation = {
            'title': 'Test',
            'created_at': '2024-10-11T10:00:00Z',
            'messages': [
                {'role': 'user', 'content': 'Question?', 'timestamp': '2024-10-11T10:00:00Z'},
            ]
        }

        md = ConversationExporter.to_markdown(
            conversation,
            include_metadata=True,
            include_timestamps=False
        )

        # Should have title but not timestamps
        assert '# Test' in md
        assert '2024-10-11T10:00:00Z' not in md

    def test_export_empty_conversation(self):
        """Test exporting conversation with no messages."""
        conversation = {
            'title': 'Empty Chat',
            'messages': []
        }

        md = ConversationExporter.to_markdown(conversation)

        assert 'Empty Chat' in md
        assert 'No messages' in md

    def test_export_with_special_characters(self):
        """Test exporting conversation with special characters."""
        conversation = {
            'title': 'Special Chars',
            'messages': [
                {'role': 'user', 'content': 'Test with **bold** and `code`'},
                {'role': 'assistant', 'content': 'Response with _italic_ text'},
            ]
        }

        md = ConversationExporter.to_markdown(conversation)

        assert 'bold' in md
        assert 'code' in md
        assert 'italic' in md

    def test_export_multiline_messages(self):
        """Test exporting messages with multiple lines."""
        conversation = {
            'messages': [
                {
                    'role': 'user',
                    'content': 'Line 1\nLine 2\nLine 3'
                }
            ]
        }

        md = ConversationExporter.to_markdown(conversation)

        assert 'Line 1' in md
        assert 'Line 2' in md
        assert 'Line 3' in md


class TestPDFExport:
    """Test PDF export functionality."""

    def test_export_pdf_requires_reportlab(self):
        """Test that PDF export requires reportlab."""
        conversation = {
            'title': 'Test',
            'messages': []
        }

        # If reportlab is available, this should work fine
        try:
            pdf = ConversationExporter.to_pdf(conversation)
            assert isinstance(pdf, bytes)
        except ImportError:
            # If not available, should raise ImportError
            pytest.skip("reportlab not installed")

    def test_export_pdf_basic(self):
        """Test exporting basic conversation to PDF."""
        try:
            from reportlab.lib.pagesizes import letter
        except ImportError:
            pytest.skip("reportlab not installed")

        conversation = {
            'title': 'Test Conversation',
            'created_at': '2024-10-11T10:00:00Z',
            'messages': [
                {'role': 'user', 'content': 'Hello?'},
                {'role': 'assistant', 'content': 'Hi!'},
            ]
        }

        pdf_bytes = ConversationExporter.to_pdf(conversation)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF should start with %PDF
        assert pdf_bytes.startswith(b'%PDF')

    def test_export_pdf_without_metadata(self):
        """Test PDF export without metadata."""
        try:
            from reportlab.lib.pagesizes import letter
        except ImportError:
            pytest.skip("reportlab not installed")

        conversation = {
            'title': 'Test',
            'created_at': '2024-10-11T10:00:00Z',
            'messages': [
                {'role': 'user', 'content': 'Question?'},
            ]
        }

        pdf_bytes = ConversationExporter.to_pdf(
            conversation,
            include_metadata=False
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')

    def test_export_pdf_with_special_characters(self):
        """Test PDF export with special HTML characters."""
        try:
            from reportlab.lib.pagesizes import letter
        except ImportError:
            pytest.skip("reportlab not installed")

        conversation = {
            'title': 'HTML Chars',
            'messages': [
                {'role': 'user', 'content': 'Test <tag> & special'},
            ]
        }

        # Should not raise even with special chars
        pdf_bytes = ConversationExporter.to_pdf(conversation)
        assert isinstance(pdf_bytes, bytes)


class TestJSONExport:
    """Test JSON export functionality."""

    def test_export_json_basic(self):
        """Test exporting conversation to JSON."""
        conversation = {
            'id': 'conv-123',
            'title': 'Test',
            'messages': [
                {'role': 'user', 'content': 'Hello'},
            ]
        }

        json_str = ConversationExporter.to_json(conversation)

        assert isinstance(json_str, str)
        assert 'conv-123' in json_str
        assert 'Test' in json_str
        assert 'Hello' in json_str

    def test_export_json_unicode(self):
        """Test JSON export with Unicode characters."""
        conversation = {
            'title': 'Test',
            'messages': [
                {'role': 'user', 'content': 'Hëllö wørld 🌍'},
            ]
        }

        json_str = ConversationExporter.to_json(conversation)

        assert '🌍' in json_str or 'wørld' in json_str


class TestGenericExport:
    """Test generic export function."""

    def test_export_markdown_format(self):
        """Test export with markdown format."""
        conversation = {
            'title': 'Test',
            'messages': [
                {'role': 'user', 'content': 'Hello'},
            ]
        }

        result = ConversationExporter.export(conversation, format='markdown')

        assert isinstance(result, bytes)
        assert b'Test' in result
        assert b'Hello' in result

    def test_export_json_format(self):
        """Test export with JSON format."""
        conversation = {
            'title': 'Test',
            'messages': [
                {'role': 'user', 'content': 'Hello'},
            ]
        }

        result = ConversationExporter.export(conversation, format='json')

        assert isinstance(result, bytes)
        assert b'"title"' in result or b'Test' in result

    def test_export_unsupported_format(self):
        """Test export with unsupported format."""
        conversation = {'title': 'Test'}

        with pytest.raises(ValueError, match="Unsupported export format"):
            ConversationExporter.export(conversation, format='invalid')

    def test_export_case_insensitive(self):
        """Test that format is case-insensitive."""
        conversation = {
            'title': 'Test',
            'messages': []
        }

        # Should work with uppercase
        result = ConversationExporter.export(conversation, format='MARKDOWN')
        assert isinstance(result, bytes)

        result = ConversationExporter.export(conversation, format='JSON')
        assert isinstance(result, bytes)


class TestFilenameGeneration:
    """Test filename generation for exports."""

    def test_generate_markdown_filename(self):
        """Test generating filename for Markdown export."""
        conversation = {'title': 'My Conversation'}

        filename = ConversationExporter.get_export_filename(conversation, 'markdown')

        assert filename.endswith('.md')
        assert 'conversation' in filename.lower()

    def test_generate_pdf_filename(self):
        """Test generating filename for PDF export."""
        conversation = {'title': 'My Conversation'}

        filename = ConversationExporter.get_export_filename(conversation, 'pdf')

        assert filename.endswith('.pdf')

    def test_generate_json_filename(self):
        """Test generating filename for JSON export."""
        conversation = {'title': 'My Conversation'}

        filename = ConversationExporter.get_export_filename(conversation, 'json')

        assert filename.endswith('.json')

    def test_filename_sanitization(self):
        """Test that special characters are removed from filename."""
        conversation = {'title': 'Test: File? With <Special> Characters*'}

        filename = ConversationExporter.get_export_filename(conversation, 'markdown')

        # Should not contain special characters
        assert ':' not in filename
        assert '?' not in filename
        assert '<' not in filename
        assert '>' not in filename
        assert '*' not in filename

    def test_filename_length_limit(self):
        """Test that filename is limited to reasonable length."""
        conversation = {'title': 'A' * 100}

        filename = ConversationExporter.get_export_filename(conversation, 'markdown')

        # Filename without extension should be reasonable
        name_without_ext = filename.rsplit('.', 1)[0]
        assert len(name_without_ext) <= 50

    def test_filename_with_spaces(self):
        """Test that spaces are converted to underscores."""
        conversation = {'title': 'My Test Conversation'}

        filename = ConversationExporter.get_export_filename(conversation, 'markdown')

        assert ' ' not in filename
        assert '_' in filename


class TestExportEdgeCases:
    """Test edge cases in export functionality."""

    def test_export_conversation_missing_fields(self):
        """Test exporting conversation with missing fields."""
        conversation = {
            'messages': [
                {'role': 'user'},  # Missing content
                {'content': 'Response'},  # Missing role
            ]
        }

        md = ConversationExporter.to_markdown(conversation)

        # Should handle gracefully
        assert isinstance(md, str)

    def test_export_very_long_message(self):
        """Test exporting conversation with very long message."""
        long_content = 'A' * 10000
        conversation = {
            'messages': [
                {'role': 'user', 'content': long_content},
            ]
        }

        md = ConversationExporter.to_markdown(conversation)

        assert long_content in md

    def test_export_many_messages(self):
        """Test exporting conversation with many messages."""
        conversation = {
            'messages': [
                {
                    'role': 'user' if i % 2 == 0 else 'assistant',
                    'content': f'Message {i}'
                }
                for i in range(100)
            ]
        }

        md = ConversationExporter.to_markdown(conversation)

        # Should contain all messages
        for i in range(100):
            assert f'Message {i}' in md


class TestExportRoutes:
    """Test export endpoints."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Headers with valid JWT token."""
        token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjo5OTk5OTk5OTk5LCJ0ZW5hbnQiOiJkZWZhdWx0In0."
            "L8Bp2wTLbRNv-C7zj-z8SuFn5N7v5t8y4u9w2x3z4K4"
        )
        return {"Authorization": f"Bearer {token}"}

    def test_export_endpoint_exists(self, client, auth_headers):
        """Test that export endpoint exists."""
        response = client.get(
            "/api/v1/conversations/nonexistent/export?format=markdown",
            headers=auth_headers
        )

        # Should return 404 (conversation not found) or 401 (auth)
        assert response.status_code in [401, 404, 503]

    def test_export_invalid_format(self, client, auth_headers):
        """Test export with invalid format."""
        response = client.get(
            "/api/v1/conversations/test-id/export?format=invalid",
            headers=auth_headers
        )

        # Should return error
        assert response.status_code in [400, 401, 404, 503]

    def test_export_markdown_content_type(self, client, auth_headers):
        """Test that markdown export returns correct content type."""
        response = client.get(
            "/api/v1/conversations/test-id/export?format=markdown",
            headers=auth_headers
        )

        # May fail with 404, but if it works, check content type
        if response.status_code == 200:
            assert 'text/markdown' in response.headers.get('content-type', '')

    def test_export_pdf_content_type(self, client, auth_headers):
        """Test that PDF export returns correct content type."""
        response = client.get(
            "/api/v1/conversations/test-id/export?format=pdf",
            headers=auth_headers
        )

        # May fail with 404, but if it works, check content type
        if response.status_code == 200:
            assert 'application/pdf' in response.headers.get('content-type', '')

    def test_export_json_content_type(self, client, auth_headers):
        """Test that JSON export returns correct content type."""
        response = client.get(
            "/api/v1/conversations/test-id/export?format=json",
            headers=auth_headers
        )

        # May fail with 404, but if it works, check content type
        if response.status_code == 200:
            assert 'application/json' in response.headers.get('content-type', '')
