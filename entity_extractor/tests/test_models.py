"""Tests for data models."""

from entity_extractor.models import Entity


class TestEntityNormalization:
    """Test entity text normalization for deduplication."""

    def test_the_prefix_normalization(self):
        """Test that 'the' prefix is normalized."""
        entity1 = Entity(text="the Board", label="ORG")
        entity2 = Entity(text="Board", label="ORG")
        assert entity1 == entity2
        assert hash(entity1) == hash(entity2)

    def test_the_prefix_case_insensitive(self):
        """Test that 'The' prefix is normalized (case-insensitive)."""
        entity1 = Entity(text="The Board", label="ORG")
        entity2 = Entity(text="Board", label="ORG")
        entity3 = Entity(text="THE BOARD", label="ORG")
        assert entity1 == entity2
        assert entity1 == entity3
        assert hash(entity1) == hash(entity2)
        assert hash(entity1) == hash(entity3)

    def test_possessive_suffix_normalization(self):
        """Test that possessive 's suffix is normalized."""
        entity1 = Entity(text="San Diego's", label="GPE")
        entity2 = Entity(text="San Diego", label="GPE")
        assert entity1 == entity2
        assert hash(entity1) == hash(entity2)

    def test_both_the_and_possessive(self):
        """Test normalization of both 'the' prefix and 's suffix."""
        entity1 = Entity(text="the Board's", label="ORG")
        entity2 = Entity(text="Board", label="ORG")
        entity3 = Entity(text="the Board", label="ORG")
        entity4 = Entity(text="Board's", label="ORG")
        assert entity1 == entity2
        assert entity1 == entity3
        assert entity1 == entity4
        assert hash(entity1) == hash(entity2)
        assert hash(entity1) == hash(entity3)
        assert hash(entity1) == hash(entity4)

    def test_different_labels_not_equal(self):
        """Test that entities with same text but different labels are not equal."""
        entity1 = Entity(text="Washington", label="PERSON")
        entity2 = Entity(text="Washington", label="GPE")
        assert entity1 != entity2
        assert hash(entity1) != hash(entity2)

    def test_the_prefix_with_different_labels(self):
        """Test normalization respects label differences."""
        entity1 = Entity(text="the Washington", label="ORG")
        entity2 = Entity(text="Washington", label="GPE")
        assert entity1 != entity2

    def test_real_world_examples(self):
        """Test real-world entity variations."""
        # National Labor Relations Board variations
        nlrb1 = Entity(text="National Labor Relations Board", label="ORG")
        nlrb2 = Entity(text="the National Labor Relations Board", label="ORG")
        nlrb3 = Entity(text="The National Labor Relations Board", label="ORG")
        assert nlrb1 == nlrb2
        assert nlrb1 == nlrb3

        # San Diego variations
        sd1 = Entity(text="San Diego", label="GPE")
        sd2 = Entity(text="San Diego's", label="GPE")
        assert sd1 == sd2

    def test_set_deduplication(self):
        """Test that entities are properly deduplicated in a set."""
        entities = {
            Entity(text="the Board", label="ORG"),
            Entity(text="Board", label="ORG"),
            Entity(text="Board's", label="ORG"),
            Entity(text="THE BOARD", label="ORG"),
            Entity(text="the Board's", label="ORG"),
        }
        # All should collapse to one entity
        assert len(entities) == 1

    def test_set_deduplication_preserves_first(self):
        """Test that the first entity text is preserved when adding to set."""
        entities = set()
        entities.add(Entity(text="Board", label="ORG"))
        entities.add(Entity(text="the Board", label="ORG"))
        entities.add(Entity(text="Board's", label="ORG"))

        assert len(entities) == 1
        # The first added text should be preserved
        entity = list(entities)[0]
        assert entity.text == "Board"

    def test_set_deduplication_mixed_labels(self):
        """Test deduplication with mixed entity types."""
        entities = {
            Entity(text="Washington", label="PERSON"),
            Entity(text="the Washington", label="PERSON"),
            Entity(text="Washington", label="GPE"),
            Entity(text="Washington's", label="GPE"),
        }
        # Should have 2 entities (one PERSON, one GPE)
        assert len(entities) == 2

    def test_wikidata_preservation(self):
        """Test that wikidata info is preserved during deduplication."""
        entity1 = Entity(
            text="San Francisco",
            label="GPE",
            wikidata_id="Q62",
            wikidata_url="http://www.wikidata.org/entity/Q62",
            wikidata_description="city in California",
        )
        entity2 = Entity(text="the San Francisco", label="GPE")

        # They should be equal for deduplication
        assert entity1 == entity2

        # When added to a set, first one wins
        entities = {entity1, entity2}
        assert len(entities) == 1
        entity = list(entities)[0]
        assert entity.wikidata_id == "Q62"

    def test_edge_cases(self):
        """Test edge cases in normalization."""
        # "the" in the middle should not be removed
        entity1 = Entity(text="In the Beginning", label="ORG")
        entity2 = Entity(text="In Beginning", label="ORG")
        assert entity1 != entity2

        # "the" without space should not be removed
        entity3 = Entity(text="theater", label="ORG")
        entity4 = Entity(text="ater", label="ORG")
        assert entity3 != entity4

        # "'s" in middle should not be removed
        entity5 = Entity(text="It's Complicated", label="ORG")
        entity6 = Entity(text="It Complicated", label="ORG")
        assert entity5 != entity6

    def test_empty_and_short_strings(self):
        """Test normalization with edge case strings."""
        # Single word shouldn't crash
        entity1 = Entity(text="the", label="ORG")
        entity2 = Entity(text="", label="ORG")
        assert entity1 != entity2

        # Just "'s"
        entity3 = Entity(text="'s", label="ORG")
        entity4 = Entity(text="", label="ORG")
        assert entity3 == entity4  # Both normalize to empty string

    def test_compile_scenario(self):
        """Test a realistic compilation scenario with multiple variations."""
        # Simulating entities from multiple emails
        all_entities = {
            Entity(text="Stephen Beal", label="PERSON"),
            Entity(text="Steve Beal", label="PERSON"),  # Different enough, not dedupe
            Entity(text="CCA", label="ORG"),
            Entity(text="the CCA", label="ORG"),  # Should dedupe with CCA
            Entity(text="San Francisco", label="GPE"),
            Entity(
                text="San Francisco's", label="GPE"
            ),  # Should dedupe with San Francisco
            Entity(text="the Bay Area", label="LOC"),
            Entity(text="Bay Area", label="LOC"),  # Should dedupe with the Bay Area
        }

        # Should have 5 unique entities:
        # 1. Stephen Beal (PERSON)
        # 2. Steve Beal (PERSON) - different text
        # 3. CCA (ORG) - dedupe with "the CCA"
        # 4. San Francisco (GPE) - dedupe with "San Francisco's"
        # 5. Bay Area (LOC) - dedupe with "the Bay Area"
        assert len(all_entities) == 5

        # Verify specific deduplication
        cca_entities = {e for e in all_entities if e.label == "ORG"}
        assert len(cca_entities) == 1

        sf_entities = {e for e in all_entities if e.label == "GPE"}
        assert len(sf_entities) == 1

        ba_entities = {e for e in all_entities if e.label == "LOC"}
        assert len(ba_entities) == 1
