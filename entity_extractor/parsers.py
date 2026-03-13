"""Email parsers for different formats (EML, HTML, PDF)."""

import email
from email import policy
from pathlib import Path
from typing import Optional, Tuple

import pdfplumber
from bs4 import BeautifulSoup


def parse_eml(file_path: Path) -> Tuple[str, Optional[str]]:
    """
    Parse an EML file and extract text content and subject.

    Args:
        file_path: Path to the EML file

    Returns:
        Tuple of (text_content, subject)
    """
    with open(file_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    subject: str = msg.get("subject", "")

    # Extract body text
    text_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type: str = part.get_content_type()
            if content_type == "text/plain":
                try:
                    text_parts.append(part.get_content())
                except Exception:
                    continue
            elif content_type == "text/html":
                # Fallback to HTML if no plain text
                try:
                    html_content = part.get_content()
                    soup = BeautifulSoup(html_content, "html.parser")
                    text_parts.append(soup.get_text(separator=" ", strip=True))
                except Exception:
                    continue
    else:
        # Non-multipart message
        try:
            content = msg.get_content()
            if msg.get_content_type() == "text/html":
                soup = BeautifulSoup(content, "html.parser")
                text_parts.append(soup.get_text(separator=" ", strip=True))
            else:
                text_parts.append(content)
        except Exception:
            text_parts.append(str(msg))

    text = " ".join(text_parts)
    # Normalize whitespace, prevents newlines in the middle of names from creating dupes
    text = text.replace("\n", " ")
    return text, subject


def parse_html(file_path: Path) -> Tuple[str, Optional[str]]:
    """
    Parse an HTML file and extract text content and subject.

    Args:
        file_path: Path to the HTML file

    Returns:
        Tuple of (text_content, subject)
    """
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Try to extract subject from title or meta tags
    subject = None
    title = soup.find("title")
    if title:
        subject = title.get_text(strip=True)

    # Extract text content
    text = soup.get_text(separator=" ", strip=True)

    return text, subject


def parse_pdf(file_path: Path) -> Tuple[str, Optional[str]]:
    """
    Parse a PDF file and extract text content.

    Args:
        file_path: Path to the PDF file

    Returns:
        Tuple of (text_content, subject)

    Note: PDF subject extraction is limited, usually None
    """
    text_parts = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        # Drive PDFs will have title metadata
        subject: str | None = pdf.metadata.get("Title") if pdf.metadata else None

    text: str = "\n\n".join(text_parts)

    return text, subject


def parse_email_file(file_path: Path) -> Tuple[str, Optional[str], str]:
    """
    Parse an email file based on its extension.

    Args:
        file_path: Path to the email file

    Returns:
        Tuple of (text_content, subject, format)

    Raises:
        ValueError: If file format is not supported
    """
    suffix = file_path.suffix.lower()

    if suffix == ".eml":
        text, subject = parse_eml(file_path)
        return text, subject, "eml"
    elif suffix in [".html", ".htm"]:
        text, subject = parse_html(file_path)
        return text, subject, "html"
    elif suffix == ".pdf":
        text, subject = parse_pdf(file_path)
        return text, subject, "pdf"
    else:
        raise ValueError(f"Unsupported file format: {suffix}")
