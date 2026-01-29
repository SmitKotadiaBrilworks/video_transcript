"""Generate PDF from transcript text."""

import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def transcript_to_pdf(
    text: str,
    output_path: str,
    title: str = "Transcript",
) -> str:
    """
    Create a PDF file from transcript text.

    Args:
        text: Full transcript text.
        output_path: Path for the output PDF file.
        title: Optional title for the document.

    Returns:
        Path to the created PDF.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    story: list = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))

    # Split into paragraphs (double newline) or long lines
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        # Escape XML special chars for ReportLab
        block = block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(block, styles["Normal"]))
        story.append(Spacer(1, 0.1 * inch))

    doc.build(story)
    return output_path


def get_transcript_pdf_path(
    base_name: str,
    output_dir: str = "output_transcripts",
) -> str:
    """Return output path for a transcript PDF given a base name."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return os.path.join(output_dir, f"{base_name}_transcript.pdf")
