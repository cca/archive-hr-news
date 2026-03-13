"""Wikidata entity linking for enriching extracted entities."""

import time
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from entity_extractor import __version__

from .models import Entity


class WikidataLinker:
    """Links named entities to Wikidata."""

    BASE_URL = "https://www.wikidata.org/w/api.php"
    ENTITY_URL = "https://www.wikidata.org/wiki/"

    def __init__(self, delay: float = 0.1, entity_types: Optional[list[str]] = None):
        """
        Initialize the Wikidata linker.

        Args:
            delay: Delay between API requests in seconds (be respectful)
            entity_types: Optional list of entity types to link (e.g., ["PERSON", "ORG"])
        """
        self.delay = delay
        self.entity_types: list[str] | None = entity_types
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": f"EntityExtractor/{__version__} (Educational; Python/requests)"
            }
        )

    def search_entity(
        self, query: str, entity_type: str | None = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search for an entity in Wikidata.

        Args:
            query: Entity name to search for
            entity_type: Type of entity (PERSON, ORG, etc.) - used for filtering

        Returns:
            Dictionary with entity info or None if not found
        """
        params: dict[str, Any] = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "search": quote(query),
            "limit": 1,
        }

        try:
            response: requests.Response = self.session.get(
                self.BASE_URL, params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get("search") and len(data["search"]) > 0:
                result = data["search"][0]
                return {
                    "id": result["id"],
                    "url": result.get("concepturi", f"{self.ENTITY_URL}{result['id']}"),
                    "description": result.get("description", ""),
                }

            time.sleep(self.delay)  # Rate limiting
            return None

        except Exception:
            # Silently fail for now - linking is optional
            return None

    def enrich_entity(self, entity: Entity) -> Entity:
        """
        Enrich an entity with Wikidata information.

        Args:
            entity: Entity to enrich

        Returns:
            Entity with Wikidata fields populated (if found)
        """
        # Only attempt linking for specified entity types
        if self.entity_types and entity.label not in self.entity_types:
            return entity

        enriched_entity: Optional[Entity] = None
        result: Dict[str, Any] | None = self.search_entity(entity.text, entity.label)

        if result:
            enriched_entity = Entity(
                text=entity.text,
                label=entity.label,
                wikidata_id=result["id"],
                wikidata_url=result["url"],
                wikidata_description=result["description"],
            )

        return enriched_entity if enriched_entity else entity

    def enrich_entities(self, entities: set[Entity]) -> set[Entity]:
        """
        Enrich multiple entities with Wikidata information.

        Args:
            entities: Set of entities to enrich

        Returns:
            Set of enriched entities
        """
        enriched: set[Entity] = set()
        for entity in entities:
            enriched_entity: Entity = self.enrich_entity(entity)
            enriched.add(enriched_entity)

        return enriched
