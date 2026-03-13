"""Tests for email parsers."""

from pathlib import Path

import pytest

from entity_extractor.parsers import parse_email_file, parse_eml, parse_html

# Get the fixtures directory path
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestEmailParsers:
    """Test email parsing functions."""

    def test_parse_eml_file(self):
        """Test parsing an EML file."""
        test_file = FIXTURES_DIR / "test_email.eml"
        assert test_file.exists(), f"Fixture not found: {test_file}"

        text, subject = parse_eml(test_file)

        assert text is not None
        assert len(text) > 0
        assert subject is not None
        assert "Test Faculty Announcement" in subject
        # Check that content was extracted
        assert "Yee Jan Bao" in text
        assert "CCA Community" in text
        assert "Steve Beal" in text

    def test_parse_multipart_eml(self):
        """Test parsing a multipart EML file with plain text and HTML."""
        test_file = FIXTURES_DIR / "multipart_email.eml"
        assert test_file.exists(), f"Fixture not found: {test_file}"

        text, subject = parse_eml(test_file)

        assert text is not None
        assert len(text) > 0
        assert subject is not None
        assert "Simple Test Email" in subject
        # Should extract text content
        assert "Albert Einstein" in text
        assert "Marie Curie" in text
        assert "United Nations" in text

    def test_parse_html_file(self):
        """Test parsing an HTML file."""
        test_file = FIXTURES_DIR / "test_email.html"
        assert test_file.exists(), f"Fixture not found: {test_file}"

        text, subject = parse_html(test_file)

        assert text is not None
        assert len(text) > 0
        assert subject is not None
        # HTML should have the subject in the title
        assert "Test Faculty Announcement" in subject
        # Check content extraction
        assert "Yee Jan Bao" in text
        assert "CCA Community" in text

    def test_parse_simple_html_file(self):
        """Test parsing a simple HTML file."""
        test_file = FIXTURES_DIR / "simple_email.html"
        assert test_file.exists(), f"Fixture not found: {test_file}"

        text, subject = parse_html(test_file)

        assert text is not None
        assert len(text) > 0
        # Check entities are in the text
        assert "William Shakespeare" in text
        assert "NASA" in text
        assert "Paris" in text or "France" in text

    def test_parse_email_file_auto_detect_eml(self):
        """Test auto-detection of EML format."""
        test_file = FIXTURES_DIR / "test_email.eml"
        assert test_file.exists(), f"Fixture not found: {test_file}"

        text, subject, fmt = parse_email_file(test_file)

        assert fmt == "eml"
        assert text is not None
        assert len(text) > 0
        assert subject
        assert "Test Faculty Announcement" in subject

    def test_parse_email_file_auto_detect_html(self):
        """Test auto-detection of HTML format."""
        test_file = FIXTURES_DIR / "test_email.html"
        assert test_file.exists(), f"Fixture not found: {test_file}"

        text, subject, fmt = parse_email_file(test_file)

        assert fmt == "html"
        assert text is not None
        assert len(text) > 0

    def test_parse_email_file_unsupported_format(self):
        """Test that unsupported formats raise an error."""
        # Create a temporary file with unsupported extension
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                parse_email_file(tmp_path)
        finally:
            tmp_path.unlink()  # Clean up

    def test_eml_subject_extraction(self):
        """Test that EML parser correctly extracts subject."""
        test_file = FIXTURES_DIR / "test_email.eml"
        assert test_file.exists(), f"Fixture not found: {test_file}"

        text, subject = parse_eml(test_file)

        # Subject should be populated
        assert subject is not None
        assert len(subject) > 0
        assert "Test Faculty Announcement" in subject

    def test_html_title_extraction(self):
        """Test that HTML parser extracts title as subject."""
        test_file = FIXTURES_DIR / "simple_email.html"
        assert test_file.exists(), f"Fixture not found: {test_file}"

        text, subject = parse_html(test_file)

        # Should extract title as subject
        assert subject is not None
        assert "Simple HTML Email" in subject
