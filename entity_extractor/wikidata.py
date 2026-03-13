"""Wikidata entity linking for enriching extracted entities."""

import time
from typing import Any, Dict, Optional

import requests

from entity_extractor import __version__

from .models import Entity

# CCA and certain figures will come up often
# This way we know we get them right and save requests
cca_entity: Entity = Entity(
    text="CCA",
    label="ORG",
    wikidata_id="Q1026804",
    wikidata_url="http://www.wikidata.org/entity/Q1026804",
    wikidata_description='"private art and design school in California, United States (founded 1907, opened new additional permanent campus in San Francisco in 1996)"',
)
howse_entity: Entity = Entity(
    text="David C. Howse",
    label="PERSON",
    wikidata_id="Q131593045",
    wikidata_url="http://www.wikidata.org/entity/Q131593045",
    wikidata_description="10th president of the California College of the Arts",
)
entity_cache: dict[str, Entity] = {
    "CCA": cca_entity,
    "CCAC": cca_entity,
    "California College of the Arts": cca_entity,
    "California College of Art and Craft": cca_entity,
    "David C. Howse": howse_entity,
    "David Howse": howse_entity,
    "Stephen Beal": Entity(
        text="Stephen Beal",
        label="PERSON",
        wikidata_id="Q7608685",
        wikidata_url="http://www.wikidata.org/entity/Q7608685",
        wikidata_description="American artist",
    ),
}


class WikidataLinker:
    """Links named entities to Wikidata."""

    # https://www.wikidata.org/w/api.php?action=help&modules=wbsearchentities
    BASE_URL = "https://www.wikidata.org/w/api.php"
    ENTITY_URL = "https://www.wikidata.org/wiki/"
    # See Wikimedia User-Agent policy
    # https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
    USER_AGENT = f"EntityExtractor/{__version__} (https://libraries.cca.edu; ephetteplace@cca.edu) (Python/requests)"

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
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    def search_entity(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for an entity in Wikidata.

        Args:
            query: Entity name to search for

        Returns:
            Dictionary with entity info or None if not found
        """
        params: dict[str, Any] = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            # TODO could try to look through multiple results for best match
            "limit": 1,
            "search": query,
            # https://www.wikidata.org/wiki/Help:Data_type
            # this way we don't get properties in search results
            "type": "item",
        }

        try:
            # Example request URL:
            # https://www.wikidata.org/w/api.php?action=wbsearchentities&search=CCAC&language=en&format=json&limit=1&type=item
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
        if entity.text in entity_cache:
            enriched_entity = entity_cache[entity.text]
        else:
            result: Dict[str, Any] | None = self.search_entity(entity.text)
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
