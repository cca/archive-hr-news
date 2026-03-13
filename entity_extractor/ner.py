"""Named Entity Recognition using spaCy."""

from typing import List

import spacy
from spacy.language import Language

from .models import EmailEntities, Entity


class NERProcessor:
    """Handles NER processing using spaCy."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize the NER processor.

        Args:
            model_name: Name of the spaCy model to use
        """
        self.model_name = model_name
        self._nlp: Language | None = None

    @property
    def nlp(self) -> Language:
        """Lazy load the spaCy model."""
        if self._nlp is None:
            try:
                self._nlp = spacy.load(self.model_name)
            except OSError:
                raise RuntimeError(
                    f"spaCy model '{self.model_name}' not found. "
                    f"Please run: python -m spacy download {self.model_name}"
                )
        return self._nlp

    def extract_entities(
        self,
        text: str,
        source_file: str,
        file_format: str,
        # Default to person, organization, country, and location entities
        entity_types: List[str] = ["PERSON", "ORG", "GPE", "LOC"],
        subject: str | None = None,
    ) -> EmailEntities:
        """
        Extract named entities from text.

        Args:
            text: Text content to process
            source_file: Original file path
            file_format: Format of the file (eml, html, pdf)
            subject: Email subject line
            entity_types: List of entity types to extract (default: all)

        Returns:
            EmailEntities object containing extracted entities
        """
        doc = self.nlp(text)

        entities: set[Entity] = set()
        for ent in doc.ents:
            if ent.label_ in entity_types:
                entity = Entity(text=ent.text, label=ent.label_)
                entities.add(entity)

        return EmailEntities(
            source_file=source_file,
            format=file_format,
            subject=subject,
            entities=entities,
        )
