"""Export conversations to various formats (Markdown, PDF)."""

from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConversationExporter:
    """Export conversation history to various formats."""

    @staticmethod
    def to_markdown(
        conversation: Dict,
        include_metadata: bool = True,
        include_timestamps: bool = True
    ) -> str:
        """
        Export conversation to Markdown format.

        Args:
            conversation: Conversation dict with id, title, created_at, messages
            include_metadata: Whether to include conversation metadata header
            include_timestamps: Whether to include message timestamps

        Returns:
            Markdown string
        """
        lines = []

        # Add header
        if include_metadata:
            title = conversation.get('title', 'Conversation')
            lines.append(f"# {title}")
            lines.append("")

            created_at = conversation.get('created_at')
            if created_at and include_timestamps:
                lines.append(f"**Started:** {created_at}")

            updated_at = conversation.get('updated_at')
            if updated_at and include_timestamps:
                lines.append(f"**Last Updated:** {updated_at}")

            conv_id = conversation.get('id')
            if conv_id:
                lines.append(f"**ID:** `{conv_id}`")

            lines.append("")
            lines.append("---")
            lines.append("")

        # Add messages
        messages = conversation.get('messages', [])

        if not messages:
            lines.append("*No messages in this conversation.*")
            return '\n'.join(lines)

        for i, msg in enumerate(messages, 1):
            role = msg.get('role', 'unknown').capitalize()
            content = msg.get('content', '')
            timestamp = msg.get('timestamp')

            # Format role as heading
            lines.append(f"## {role}")

            # Add timestamp if available
            if timestamp and include_timestamps:
                lines.append(f"*{timestamp}*")
                lines.append("")

            # Add content
            lines.append(content)
            lines.append("")

        return '\n'.join(lines)

    @staticmethod
    def to_pdf(
        conversation: Dict,
        include_metadata: bool = True,
        include_timestamps: bool = True
    ) -> bytes:
        """
        Export conversation to PDF format.

        Args:
            conversation: Conversation dict
            include_metadata: Whether to include metadata
            include_timestamps: Whether to include timestamps

        Returns:
            PDF bytes
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
            from io import BytesIO
        except ImportError:
            logger.error("reportlab not available for PDF export")
            raise ImportError(
                "reportlab is required for PDF export. "
                "Install with: pip install reportlab"
            )

        # Create PDF in memory
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#1f4788',
            spaceAfter=12
        )
        role_style = ParagraphStyle(
            'Role',
            parent=styles['Heading2'],
            fontSize=14,
            textColor='#2e5c8a',
            spaceAfter=6,
            spaceBefore=12
        )
        content_style = ParagraphStyle(
            'Content',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=14
        )
        meta_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=9,
            textColor='#666666',
            spaceAfter=2
        )

        # Build document elements
        elements = []

        # Add header
        if include_metadata:
            title = conversation.get('title', 'Conversation Export')
            elements.append(Paragraph(title, title_style))
            elements.append(Spacer(1, 0.2 * inch))

            # Add metadata
            if conversation.get('created_at'):
                elements.append(
                    Paragraph(
                        f"<b>Started:</b> {conversation.get('created_at')}",
                        meta_style
                    )
                )

            if conversation.get('updated_at'):
                elements.append(
                    Paragraph(
                        f"<b>Last Updated:</b> {conversation.get('updated_at')}",
                        meta_style
                    )
                )

            if conversation.get('id'):
                elements.append(
                    Paragraph(
                        f"<b>ID:</b> {conversation.get('id')}",
                        meta_style
                    )
                )

            elements.append(Spacer(1, 0.3 * inch))

        # Add messages
        messages = conversation.get('messages', [])

        if not messages:
            elements.append(Paragraph("No messages in this conversation.", content_style))
        else:
            for msg in messages:
                role = msg.get('role', 'unknown').capitalize()
                content = msg.get('content', '')
                timestamp = msg.get('timestamp')

                # Add role as heading
                elements.append(Paragraph(f"<b>{role}</b>", role_style))

                # Add timestamp if available
                if timestamp and include_timestamps:
                    elements.append(
                        Paragraph(f"<i>{timestamp}</i>", meta_style)
                    )

                # Add message content (escape special characters)
                safe_content = (
                    content
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                )
                elements.append(Paragraph(safe_content, content_style))
                elements.append(Spacer(1, 0.1 * inch))

        # Build PDF
        try:
            doc.build(elements)
            pdf_buffer.seek(0)
            return pdf_buffer.getvalue()
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise

    @staticmethod
    def to_json(conversation: Dict) -> str:
        """
        Export conversation to JSON format.

        Args:
            conversation: Conversation dict

        Returns:
            JSON string
        """
        import json
        return json.dumps(conversation, indent=2, ensure_ascii=False)

    @staticmethod
    def export(
        conversation: Dict,
        format: str = "markdown",
        **kwargs
    ) -> bytes:
        """
        Export conversation to specified format.

        Args:
            conversation: Conversation dict
            format: Export format ("markdown", "pdf", or "json")
            **kwargs: Additional format-specific options

        Returns:
            Exported content as bytes
        """
        format = format.lower()

        if format == "markdown":
            md = ConversationExporter.to_markdown(conversation, **kwargs)
            return md.encode('utf-8')
        elif format == "pdf":
            return ConversationExporter.to_pdf(conversation, **kwargs)
        elif format == "json":
            json_str = ConversationExporter.to_json(conversation)
            return json_str.encode('utf-8')
        else:
            raise ValueError(
                f"Unsupported export format: {format}. "
                "Supported: markdown, pdf, json"
            )

    @staticmethod
    def get_export_filename(conversation: Dict, format: str) -> str:
        """
        Generate appropriate filename for exported conversation.

        Args:
            conversation: Conversation dict
            format: Export format

        Returns:
            Filename string
        """
        title = conversation.get('title', 'conversation')
        # Sanitize title for filename
        safe_title = (
            title
            .lower()
            .replace(' ', '_')
            .replace('/', '_')
            .replace('\\', '_')
            .replace(':', '_')
            .replace('?', '')
            .replace('*', '')
            .replace('|', '')
            .replace('"', '')
            .replace('<', '')
            .replace('>', '')
        )

        # Limit length
        safe_title = safe_title[:50]

        extensions = {
            'markdown': 'md',
            'pdf': 'pdf',
            'json': 'json'
        }
        ext = extensions.get(format.lower(), 'txt')

        return f"{safe_title}.{ext}"
