"""Data models for entity extraction."""

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Entity:
    """Represents a named entity extracted from text.

    Frozen dataclass to make it hashable for deduplication.
    """

    text: str
    label: str
    wikidata_id: Optional[str] = None
    wikidata_url: Optional[str] = None
    wikidata_description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert entity to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize entity text for deduplication.

        Removes common variations:
        - "the " prefix (case-insensitive)
        - "'s" possessive suffix
        """
        normalized = text.lower()
        # Remove "the " prefix
        if normalized.startswith("the "):
            normalized = normalized[4:]
        # Remove "'s" possessive suffix
        if normalized.endswith("'s"):
            normalized = normalized[:-2]
        return normalized

    def __hash__(self):
        """Hash based on normalized text and label for deduplication."""
        return hash((self._normalize_text(self.text), self.label))

    def __eq__(self, other):
        """Equality based on normalized text and label."""
        if not isinstance(other, Entity):
            return False
        return (
            self._normalize_text(self.text) == self._normalize_text(other.text)
            and self.label == other.label
        )


@dataclass
class EmailEntities:
    """Container for all entities extracted from an email."""

    source_file: str
    format: str  # 'eml', 'html', or 'pdf'
    subject: Optional[str] = None
    entities: set[Entity] = field(default_factory=set)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_file": self.source_file,
            "format": self.format,
            "subject": self.subject,
            "entities": [entity.to_dict() for entity in self.entities],
        }
