from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.colors import HexColor
from io import BytesIO
import markdown2
from datetime import datetime
from typing import Dict
import json

class ExportService:
    """Export research results to various formats"""
    
    def to_pdf(self, result: Dict) -> bytes:
        """Convert research result to PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Create styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Build PDF content
        story = []
        
        # Title
        story.append(Paragraph("Research Report", title_style))
        story.append(Spacer(1, 20))
        
        # Metadata
        story.append(Paragraph(f"<b>Query:</b> {result['query']}", styles['Normal']))
        story.append(Paragraph(f"<b>Date:</b> {result['completed_at']}", styles['Normal']))
        story.append(Paragraph(f"<b>Sources Analyzed:</b> {result['extracted_count']}", styles['Normal']))
        story.append(Paragraph(f"<b>Search Engines:</b> {', '.join(result.get('search_engines_used', ['Unknown']))}", styles['Normal']))
        
        if result['summary'].get('provider'):
            story.append(Paragraph(f"<b>AI Model:</b> {result['summary']['provider']}", styles['Normal']))
        
        story.append(Spacer(1, 30))
        
        # Summary sections
        summary = result['summary']
        for section_name, section_content in summary.get('sections', {}).items():
            story.append(Paragraph(section_name, heading_style))
            
            # Clean and format content
            content = section_content.replace('[Source', '(Source').replace(']', ')')
            paragraphs = content.split('\n\n')
            
            for para in paragraphs:
                if para.strip():
                    # Handle bullet points
                    if para.strip().startswith('- '):
                        para = '• ' + para.strip()[2:]
                    
                    story.append(Paragraph(para, styles['Normal']))
                    story.append(Spacer(1, 6))
            
            story.append(Spacer(1, 12))
        
        # Sources page
        story.append(PageBreak())
        story.append(Paragraph("Sources", title_style))
        story.append(Spacer(1, 20))
        
        # List cited sources
        for source in summary.get('sources', []):
            if source.get('cited'):
                source_text = f"<b>Source {source['id']}:</b> {source['title']}<br/>"
                source_text += f"URL: <link href='{source['url']}'>{source['url']}</link><br/>"
                source_text += f"Search Engine: {source.get('source_engine', 'unknown')}"
                
                story.append(Paragraph(source_text, styles['Normal']))
                story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    
    def to_markdown(self, result: Dict) -> str:
        """Convert research result to Markdown"""
        lines = []
        
        # Header
        lines.append("# Research Report\n")
        lines.append(f"**Query:** {result['query']}  ")
        lines.append(f"**Date:** {result['completed_at']}  ")
        lines.append(f"**Sources Analyzed:** {result['extracted_count']}  ")
        lines.append(f"**Search Engines:** {', '.join(result.get('search_engines_used', ['Unknown']))}  ")
        
        if result['summary'].get('provider'):
            lines.append(f"**AI Model:** {result['summary']['provider']}  ")
        
        lines.append("\n---\n")
        
        # Summary sections
        summary = result['summary']
        for section_name, section_content in summary.get('sections', {}).items():
            lines.append(f"\n## {section_name}\n")
            lines.append(section_content)
        
        # Sources
        lines.append("\n---\n")
        lines.append("\n## Sources\n")
        
        for source in summary.get('sources', []):
            if source.get('cited'):
                lines.append(f"\n### Source {source['id']}: {source['title']}")
                lines.append(f"- **URL:** [{source['domain']}]({source['url']})")
                lines.append(f"- **Search Engine:** {source.get('source_engine', 'unknown')}")
        
        return '\n'.join(lines)
    
    def to_json(self, result: Dict) -> str:
        """Convert research result to formatted JSON"""
        return json.dumps(result, indent=2, ensure_ascii=False)