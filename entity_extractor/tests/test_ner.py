"""Tests for NER entity extraction."""

import pytest

from entity_extractor.models import EmailEntities
from entity_extractor.ner import NERProcessor


class TestNERProcessor:
    """Test the NER processor."""

    @pytest.fixture
    def ner_processor(self):
        """Create a NER processor instance."""
        return NERProcessor(model_name="en_core_web_sm")

    def test_initialization(self, ner_processor):
        """Test that the NER processor initializes correctly."""
        assert ner_processor.model_name == "en_core_web_sm"
        assert ner_processor._nlp is None  # Lazy loading

    def test_lazy_loading(self, ner_processor):
        """Test that the spaCy model loads lazily."""
        # Model should load on first access
        nlp = ner_processor.nlp
        assert nlp is not None
        assert ner_processor._nlp is not None

    def test_extract_person_entities(self, ner_processor):
        """Test extraction of person names."""
        text = "Barack Obama was the 44th President of the United States."

        result = ner_processor.extract_entities(
            text=text,
            source_file="test.txt",
            file_format="text",
            entity_types=["PERSON"],
        )

        assert isinstance(result, EmailEntities)
        assert result.source_file == "test.txt"
        assert result.format == "text"
        assert len(result.entities) > 0

        # Check for Barack Obama
        person_entities = [e for e in result.entities if e.label == "PERSON"]
        assert len(person_entities) > 0
        assert any("Obama" in e.text for e in person_entities)

    def test_extract_organization_entities(self, ner_processor):
        """Test extraction of organization names."""
        text = "Apple Inc. and Microsoft Corporation are technology companies."

        result = ner_processor.extract_entities(
            text=text, source_file="test.txt", file_format="text", entity_types=["ORG"]
        )

        org_entities = [e for e in result.entities if e.label == "ORG"]
        assert len(org_entities) >= 2

        # Check for Apple and Microsoft
        org_texts = [e.text for e in org_entities]
        assert any("Apple" in text for text in org_texts)
        assert any("Microsoft" in text for text in org_texts)

    def test_extract_location_entities(self, ner_processor):
        """Test extraction of location entities."""
        text = "San Francisco is a city in California, United States."

        result = ner_processor.extract_entities(
            text=text,
            source_file="test.txt",
            file_format="text",
            entity_types=["GPE", "LOC"],
        )

        location_entities = [e for e in result.entities if e.label in ["GPE", "LOC"]]
        assert len(location_entities) >= 2

        # Check for San Francisco and California
        location_texts = [e.text for e in location_entities]
        assert any(
            "Francisco" in text or "San Francisco" in text for text in location_texts
        )
        assert any("California" in text for text in location_texts)

    def test_entity_positions(self, ner_processor):
        """Test that entity positions are correct."""
        text = "Albert Einstein was born in Germany."

        result = ner_processor.extract_entities(
            text=text,
            source_file="test.txt",
            file_format="text",
            entity_types=["PERSON", "GPE"],
        )

        # Check that positions are valid
        for entity in result.entities:
            assert entity.start >= 0
            assert entity.end > entity.start
            assert entity.end <= len(text)
            # Verify the position matches the text
            assert text[entity.start : entity.end] == entity.text

    def test_multiple_entity_types(self, ner_processor):
        """Test extraction of multiple entity types."""
        text = "Marie Curie worked at the University of Paris in France."

        result = ner_processor.extract_entities(
            text=text,
            source_file="test.txt",
            file_format="text",
            entity_types=["PERSON", "ORG", "GPE"],
        )

        # Should extract person, organization, and location
        labels = set(e.label for e in result.entities)
        assert "PERSON" in labels or "ORG" in labels or "GPE" in labels
        assert len(result.entities) >= 2

    def test_empty_text(self, ner_processor):
        """Test handling of empty text."""
        result = ner_processor.extract_entities(
            text="", source_file="empty.txt", file_format="text"
        )

        assert isinstance(result, EmailEntities)
        assert len(result.entities) == 0

    def test_subject_field(self, ner_processor):
        """Test that subject field is preserved."""
        text = "Test content"
        subject = "Test Subject"

        result = ner_processor.extract_entities(
            text=text, source_file="test.txt", file_format="text", subject=subject
        )

        assert result.subject == subject

    def test_well_known_entities(self, ner_processor):
        """Test extraction of well-known entities that should be recognized."""
        # Test with multiple well-known people and organizations
        text = """
        Albert Einstein developed the theory of relativity.
        The United Nations was founded in 1945.
        William Shakespeare wrote many famous plays.
        NASA sent astronauts to the Moon.
        Marie Curie won two Nobel Prizes.
        """

        result = ner_processor.extract_entities(
            text=text,
            source_file="famous.txt",
            file_format="text",
            entity_types=["PERSON", "ORG"],
        )

        # Extract texts for easier checking
        entity_texts = [e.text.lower() for e in result.entities]
        combined_text = " ".join(entity_texts)

        # Should recognize at least some famous names
        # (spaCy may not catch all, but should get most)
        recognized_count = 0
        if "einstein" in combined_text:
            recognized_count += 1
        if "shakespeare" in combined_text:
            recognized_count += 1
        if "curie" in combined_text:
            recognized_count += 1
        if "nasa" in combined_text or "united nations" in combined_text:
            recognized_count += 1

        # Should recognize at least 2 out of these famous entities
        assert recognized_count >= 2, (
            f"Only recognized {recognized_count} entities: {entity_texts}"
        )
