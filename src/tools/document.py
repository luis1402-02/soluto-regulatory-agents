"""Document generation tool for agents."""

import asyncio
import io
import time
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import jinja2
import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..utils import get_logger
from .base import BaseTool, ToolResult

logger = get_logger(__name__)


class DocumentGeneratorTool(BaseTool):
    """Tool for generating documents in various formats."""

    name = "document_generator"
    description = "Generate documents in PDF, HTML, or TXT format"

    def __init__(self):
        """Initialize document generator."""
        self.template_loader = jinja2.FileSystemLoader("templates")
        self.template_env = jinja2.Environment(loader=self.template_loader)

    async def execute(
        self,
        content: str,
        format: Literal["pdf", "html", "txt"] = "pdf",
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        template: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> ToolResult:
        """Generate a document in the specified format."""
        start_time = time.time()

        try:
            if format == "pdf":
                result = await self._generate_pdf(content, title, metadata, output_path)
            elif format == "html":
                result = await self._generate_html(content, title, metadata, template, output_path)
            elif format == "txt":
                result = await self._generate_txt(content, title, metadata, output_path)
            else:
                raise ValueError(f"Unsupported format: {format}")

            execution_time = time.time() - start_time

            logger.info(
                "document_generated",
                format=format,
                title=title,
                execution_time=execution_time,
            )

            return ToolResult(
                success=True,
                output=result,
                execution_time=execution_time,
                metadata={"format": format, "title": title},
            )

        except Exception as e:
            logger.error("document_generation_failed", error=str(e), exc_info=e)
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _generate_pdf(
        self,
        content: str,
        title: Optional[str],
        metadata: Optional[Dict[str, Any]],
        output_path: Optional[str],
    ) -> Dict[str, Any]:
        """Generate a PDF document."""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._create_pdf,
            content,
            title,
            metadata,
            output_path,
        )

    def _create_pdf(
        self,
        content: str,
        title: Optional[str],
        metadata: Optional[Dict[str, Any]],
        output_path: Optional[str],
    ) -> Dict[str, Any]:
        """Create PDF document (sync)."""
        # Create output buffer or file
        if output_path:
            output = output_path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            output = io.BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            output,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        # Container for flowables
        story = []

        # Add title if provided
        if title:
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=30,
            )
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 0.2 * inch))

        # Add metadata table if provided
        if metadata:
            meta_data = [[k, str(v)] for k, v in metadata.items()]
            meta_table = Table(meta_data, colWidths=[2 * inch, 4 * inch])
            meta_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.beige),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ])
            )
            story.append(meta_table)
            story.append(Spacer(1, 0.3 * inch))

        # Convert markdown content to PDF elements
        styles = getSampleStyleSheet()
        
        # Parse content as markdown
        html_content = markdown.markdown(content, extensions=["extra", "codehilite"])
        
        # Convert to paragraphs (simplified)
        lines = content.split("\n")
        for line in lines:
            if line.strip():
                if line.startswith("#"):
                    # Header
                    level = len(line) - len(line.lstrip("#"))
                    text = line.lstrip("#").strip()
                    style = styles[f"Heading{min(level, 6)}"]
                    story.append(Paragraph(text, style))
                else:
                    # Regular paragraph
                    story.append(Paragraph(line, styles["Normal"]))
                story.append(Spacer(1, 0.1 * inch))

        # Build PDF
        doc.build(story)

        # Return result
        if output_path:
            return {
                "path": output_path,
                "size": Path(output_path).stat().st_size,
            }
        else:
            output.seek(0)
            return {
                "content": output.getvalue(),
                "size": len(output.getvalue()),
            }

    async def _generate_html(
        self,
        content: str,
        title: Optional[str],
        metadata: Optional[Dict[str, Any]],
        template: Optional[str],
        output_path: Optional[str],
    ) -> Dict[str, Any]:
        """Generate an HTML document."""
        # Convert markdown to HTML
        html_content = markdown.markdown(
            content,
            extensions=["extra", "codehilite", "toc", "tables"],
        )

        # Use template if provided
        if template:
            try:
                tmpl = self.template_env.get_template(template)
                html = tmpl.render(
                    title=title or "Document",
                    content=html_content,
                    metadata=metadata or {},
                )
            except jinja2.TemplateNotFound:
                # Fallback to default template
                html = self._create_default_html(title, html_content, metadata)
        else:
            html = self._create_default_html(title, html_content, metadata)

        # Save or return
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(html, encoding="utf-8")
            return {
                "path": output_path,
                "size": len(html),
            }
        else:
            return {
                "content": html,
                "size": len(html),
            }

    def _create_default_html(
        self,
        title: Optional[str],
        content: str,
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        """Create default HTML template."""
        meta_html = ""
        if metadata:
            meta_items = "".join([
                f"<li><strong>{k}:</strong> {v}</li>"
                for k, v in metadata.items()
            ])
            meta_html = f"""
            <div class="metadata">
                <h2>Metadata</h2>
                <ul>{meta_items}</ul>
            </div>
            """

        return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title or 'Document'}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #1a1a1a;
            margin-top: 24px;
            margin-bottom: 16px;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
        }}
        pre {{
            background: #f4f4f4;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
        }}
        .metadata {{
            background: #f9f9f9;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 24px;
        }}
        .metadata ul {{
            list-style: none;
            padding: 0;
        }}
        .metadata li {{
            padding: 4px 0;
        }}
    </style>
</head>
<body>
    <h1>{title or 'Document'}</h1>
    {meta_html}
    <div class="content">
        {content}
    </div>
</body>
</html>
        """

    async def _generate_txt(
        self,
        content: str,
        title: Optional[str],
        metadata: Optional[Dict[str, Any]],
        output_path: Optional[str],
    ) -> Dict[str, Any]:
        """Generate a plain text document."""
        # Build text content
        lines = []
        
        if title:
            lines.append(title)
            lines.append("=" * len(title))
            lines.append("")

        if metadata:
            lines.append("METADATA:")
            for key, value in metadata.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        lines.append(content)
        
        text = "\n".join(lines)

        # Save or return
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(text, encoding="utf-8")
            return {
                "path": output_path,
                "size": len(text),
            }
        else:
            return {
                "content": text,
                "size": len(text),
            }

    def get_schema(self) -> Dict[str, Any]:
        """Get tool parameter schema."""
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Document content (supports Markdown)",
                },
                "format": {
                    "type": "string",
                    "enum": ["pdf", "html", "txt"],
                    "description": "Output format",
                    "default": "pdf",
                },
                "title": {
                    "type": "string",
                    "description": "Document title",
                },
                "metadata": {
                    "type": "object",
                    "description": "Document metadata",
                },
                "template": {
                    "type": "string",
                    "description": "Template name for HTML generation",
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path",
                },
            },
            "required": ["content"],
        }