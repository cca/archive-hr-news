"""Tests for Wikidata entity linking."""

from unittest.mock import patch

import pytest

from entity_extractor.models import Entity
from entity_extractor.wikidata import WikidataLinker


class TestWikidataLinker:
    """Test Wikidata entity linking."""

    class FakeResponse:
        def __init__(self, json_data, status_code=200):
            self._json_data = json_data
            self.status_code = status_code

        def json(self):
            return self._json_data

        def raise_for_status(self):
            if self.status_code != 200:
                raise Exception("HTTP error")

    def fake_get(self, url, params=None, timeout=None):
        # Simulate Wikidata API responses based on the search query
        query = params.get("search", "") if params else ""
        if query == "Albert Einstein":
            return self.FakeResponse(
                {
                    "search": [
                        {
                            "id": "Q937",
                            "concepturi": "https://www.wikidata.org/entity/Q937",
                            "description": "German-born theoretical physicist",
                        }
                    ]
                }
            )
        elif query == "NASA":
            return self.FakeResponse(
                {
                    "search": [
                        {
                            "id": "Q9279",
                            "concepturi": "https://www.wikidata.org/entity/Q9279",
                            "description": "United States government agency responsible for the civilian space program",
                        }
                    ]
                }
            )
        elif query == "Paris":
            return self.FakeResponse(
                {
                    "search": [
                        {
                            "id": "Q90",
                            "concepturi": "https://www.wikidata.org/entity/Q90",
                            "description": "capital and most populous city of France",
                        }
                    ]
                }
            )
        elif query == "Marie Curie":
            return self.FakeResponse(
                {
                    "search": [
                        {
                            "id": "Q7186",
                            "concepturi": "https://www.wikidata.org/entity/Q7186",
                            "description": "Polish-French physicist and chemist",
                        }
                    ]
                }
            )
        elif query == "United Nations":
            return self.FakeResponse(
                {
                    "search": [
                        {
                            "id": "Q1065",
                            "concepturi": "https://www.wikidata.org/entity/Q1065",
                            "description": "intergovernmental organization",
                        }
                    ]
                }
            )
        elif query == "Isaac Newton":
            return self.FakeResponse(
                {
                    "search": [
                        {
                            "id": "Q935",
                            "concepturi": "https://www.wikidata.org/entity/Q935",
                            "description": "English mathematician, physicist, astronomer, and author",
                        }
                    ]
                }
            )
        elif query == "XyZzY123NotARealEntity":
            return self.FakeResponse({"search": []})
        else:
            return self.FakeResponse({"search": []})

    @pytest.fixture
    def linker(self):
        """Create a Wikidata linker instance."""
        return WikidataLinker(delay=0)

    @pytest.fixture
    def people_only_linker(self):
        """Create a Wikidata linker instance that only links people."""
        return WikidataLinker(delay=0, entity_types=["PERSON"])

    @pytest.fixture(autouse=True)
    def patch_wikidata_get(self, request, linker, people_only_linker):
        # Patch the session.get method for both linkers
        patcher1 = patch.object(linker.session, "get", side_effect=self.fake_get)
        patcher2 = patch.object(
            people_only_linker.session, "get", side_effect=self.fake_get
        )
        patcher1.start()
        patcher2.start()

        def fin():
            patcher1.stop()
            patcher2.stop()

        request.addfinalizer(fin)

    def test_initialization(self, linker):
        """Test that the linker initializes correctly."""
        assert linker.delay == 0
        assert linker.session is not None
        assert "User-Agent" in linker.session.headers

    def test_search_well_known_person(self, linker):
        """Test searching for a well-known person - Albert Einstein."""
        result = linker.search_entity("Albert Einstein")

        assert result is not None
        assert "id" in result
        assert result["id"] == "Q937"  # Albert Einstein's Wikidata ID
        assert "url" in result
        assert "Q937" in result["url"]
        assert "description" in result
        assert "physicist" in result["description"].lower()

    def test_search_well_known_organization(self, linker):
        """Test searching for a well-known organization - NASA."""
        result = linker.search_entity("NASA")

        assert result is not None
        assert "id" in result
        # NASA can return different QIDs (agency vs other ID)
        # Just verify we got a valid Wikidata entity
        assert result["id"].startswith("Q")
        assert "url" in result
        assert "description" in result

    def test_search_place(self, linker):
        """Test searching for a well-known place - Paris."""
        result = linker.search_entity("Paris")

        assert result is not None
        assert "id" in result
        # Paris, France is Q90
        assert result["id"] == "Q90"
        assert "url" in result
        assert "description" in result

    def test_search_nonexistent_entity(self, linker):
        """Test searching for a non-existent or very obscure entity."""
        result = linker.search_entity("XyZzY123NotARealEntity")

        # Should return None for entities not found
        assert result is None

    def test_enrich_person_entity(self, linker):
        """Test enriching a person entity with Wikidata information."""
        entity = Entity(text="Marie Curie", label="PERSON")

        enriched = linker.enrich_entity(entity)

        assert enriched.text == "Marie Curie"
        assert enriched.label == "PERSON"
        # Should have Wikidata information
        assert enriched.wikidata_id is not None
        assert enriched.wikidata_id == "Q7186"  # Marie Curie's Wikidata ID
        assert enriched.wikidata_url is not None
        assert "Q7186" in enriched.wikidata_url
        assert enriched.wikidata_description is not None

    def test_enrich_organization_entity(self, linker):
        """Test enriching an organization entity."""
        entity = Entity(text="United Nations", label="ORG")

        enriched = linker.enrich_entity(entity)

        assert enriched.wikidata_id is not None
        assert enriched.wikidata_url is not None
        assert enriched.wikidata_description is not None

    def test_entity_type_filter(self, people_only_linker):
        """Test that non-PERSON/ORG entities are not enriched."""
        entity = Entity(text="California", label="GPE")

        enriched = people_only_linker.enrich_entity(entity)

        # Should return entity unchanged (won't look up non-person entity)
        assert enriched.wikidata_id is None
        assert enriched.wikidata_url is None
        assert enriched.wikidata_description is None

    def test_enrich_multiple_entities(self, linker):
        """Test enriching multiple entities at once."""
        entities = [
            Entity(text="Albert Einstein", label="PERSON"),
            Entity(text="NASA", label="ORG"),
        ]

        enriched: set[Entity] = linker.enrich_entities(entities)

        assert len(enriched) == 2
        # All should be enriched
        for entity in enriched:
            assert entity.wikidata_id is not None

    def test_entity_to_dict_with_wikidata(self, linker):
        """Test that enriched entity serializes correctly."""
        entity = Entity(text="Isaac Newton", label="PERSON")

        enriched = linker.enrich_entity(entity)
        entity_dict = enriched.to_dict()

        assert "text" in entity_dict
        assert "label" in entity_dict
        # Should include Wikidata fields if enrichment succeeded
        if enriched.wikidata_id:
            assert "wikidata_id" in entity_dict
            assert "wikidata_url" in entity_dict
            assert "wikidata_description" in entity_dict
