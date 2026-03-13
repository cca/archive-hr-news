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

    def __hash__(self):
        """Hash based on text and label for deduplication."""
        return hash((self.text.lower(), self.label))

    def __eq__(self, other):
        """Equality based on text and label (case-insensitive)."""
        if not isinstance(other, Entity):
            return False
        return self.text.lower() == other.text.lower() and self.label == other.label


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
