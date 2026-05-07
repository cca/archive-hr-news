"""Tests for CLI commands."""

import csv
import json

import pytest
from click.testing import CliRunner

from entity_extractor.cli import cli


@pytest.fixture
def temp_entities_dir(tmp_path):
    """Create a temporary directory with test entity JSON files."""
    # Create test entity files
    entities1 = {
        "source_file": "test1.eml",
        "format": "eml",
        "subject": "Test 1",
        "entities": [
            {"text": "John Doe", "label": "PERSON"},
            {"text": "Acme Corp", "label": "ORG"},
            {
                "text": "San Francisco",
                "label": "GPE",
                "wikidata_id": "Q62",
                "wikidata_url": "http://www.wikidata.org/entity/Q62",
                "wikidata_description": "city in California",
            },
        ],
    }

    entities2 = {
        "source_file": "test2.eml",
        "format": "eml",
        "subject": "Test 2",
        "entities": [
            {"text": "Jane Smith", "label": "PERSON"},
            {"text": "Acme Corp", "label": "ORG"},  # Duplicate
            {"text": "New York", "label": "GPE"},
        ],
    }

    # Write files
    (tmp_path / "test1.entities.json").write_text(json.dumps(entities1))
    (tmp_path / "test2.entities.json").write_text(json.dumps(entities2))

    return tmp_path


def test_compile_creates_csv(temp_entities_dir):
    """Test that compile command creates a CSV file."""
    runner = CliRunner()
    output_csv = temp_entities_dir / "output.csv"

    result = runner.invoke(
        cli, ["compile", str(temp_entities_dir), "-o", str(output_csv)]
    )

    assert result.exit_code == 0
    assert output_csv.exists()


def test_compile_deduplicates_entities(temp_entities_dir):
    """Test that compile command deduplicates entities."""
    runner = CliRunner()
    output_csv = temp_entities_dir / "output.csv"

    result = runner.invoke(
        cli, ["compile", str(temp_entities_dir), "-o", str(output_csv)]
    )

    assert result.exit_code == 0

    # Read CSV and check for deduplication
    with open(output_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should have 5 unique entities (Acme Corp appears twice but should be deduplicated)
    # John Doe, Jane Smith, Acme Corp, San Francisco, New York
    assert len(rows) == 5

    # Check that Acme Corp appears only once
    acme_entries = [r for r in rows if r["text"] == "Acme Corp"]
    assert len(acme_entries) == 1


def test_compile_csv_structure(temp_entities_dir):
    """Test that CSV has correct columns and data."""
    runner = CliRunner()
    output_csv = temp_entities_dir / "output.csv"

    result = runner.invoke(
        cli, ["compile", str(temp_entities_dir), "-o", str(output_csv)]
    )

    assert result.exit_code == 0

    # Read CSV
    with open(output_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Check columns
    assert rows[0].keys() == {
        "text",
        "label",
        "wikidata_id",
        "wikidata_url",
        "wikidata_description",
        "source_emails",
    }

    # Check San Francisco has wikidata info
    sf_row = [r for r in rows if r["text"] == "San Francisco"][0]
    assert sf_row["wikidata_id"] == "Q62"
    assert "wikidata.org" in sf_row["wikidata_url"]

    # Check Acme Corp appears in both source files (without .eml extension)
    acme_row = [r for r in rows if r["text"] == "Acme Corp"][0]
    assert "test1" in acme_row["source_emails"]
    assert "test2" in acme_row["source_emails"]
    assert " | " in acme_row["source_emails"]
    assert ".eml" not in acme_row["source_emails"]


def test_compile_default_output_path(temp_entities_dir):
    """Test that compile uses default output path when not specified."""
    runner = CliRunner()

    result = runner.invoke(cli, ["compile", str(temp_entities_dir)])

    assert result.exit_code == 0
    assert (temp_entities_dir / "entities.csv").exists()


def test_compile_no_files(tmp_path):
    """Test compile with directory containing no entity files."""
    runner = CliRunner()

    result = runner.invoke(cli, ["compile", str(tmp_path)])

    assert result.exit_code == 0
    assert "No .entities.json files found" in result.output


def test_compile_multiple_files_with_duplicates(tmp_path):
    """Test collecting entities from multiple files and deduplicating."""
    # Create 3 files with overlapping entities
    entities1 = {
        "source_file": "email1.eml",
        "format": "eml",
        "entities": [
            {"text": "Alice Johnson", "label": "PERSON"},
            {"text": "Tech Corp", "label": "ORG"},
            {"text": "Boston", "label": "GPE"},
        ],
    }

    entities2 = {
        "source_file": "email2.eml",
        "format": "eml",
        "entities": [
            {"text": "Alice Johnson", "label": "PERSON"},  # Duplicate
            {"text": "Medical Inc", "label": "ORG"},
            {"text": "boston", "label": "GPE"},  # Case variation - should dedupe
        ],
    }

    entities3 = {
        "source_file": "email3.eml",
        "format": "eml",
        "entities": [
            {"text": "Bob Smith", "label": "PERSON"},
            {"text": "Tech Corp", "label": "ORG"},  # Duplicate
            {"text": "Seattle", "label": "GPE"},
        ],
    }

    (tmp_path / "email1.entities.json").write_text(json.dumps(entities1))
    (tmp_path / "email2.entities.json").write_text(json.dumps(entities2))
    (tmp_path / "email3.entities.json").write_text(json.dumps(entities3))

    runner = CliRunner()
    output_csv = tmp_path / "output.csv"

    result = runner.invoke(cli, ["compile", str(tmp_path), "-o", str(output_csv)])

    assert result.exit_code == 0
    assert "Compiled 6 unique entities" in result.output

    # Read and verify CSV
    with open(output_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should have 6 unique entities (case-insensitive deduplication)
    assert len(rows) == 6

    # Verify case-insensitive deduplication worked
    boston_entries = [r for r in rows if r["text"].lower() == "boston"]
    assert len(boston_entries) == 1

    alice_entries = [r for r in rows if r["text"] == "Alice Johnson"]
    assert len(alice_entries) == 1

    tech_entries = [r for r in rows if r["text"] == "Tech Corp"]
    assert len(tech_entries) == 1


def test_compile_with_and_without_wikidata(tmp_path):
    """Test entities with and without Wikidata information."""
    entities = {
        "source_file": "test.eml",
        "format": "eml",
        "entities": [
            {
                "text": "Paris",
                "label": "GPE",
                "wikidata_id": "Q90",
                "wikidata_url": "http://www.wikidata.org/entity/Q90",
                "wikidata_description": "capital of France",
            },
            {
                "text": "London",
                "label": "GPE",
                "wikidata_id": "Q84",
                "wikidata_url": "http://www.wikidata.org/entity/Q84",
                "wikidata_description": "capital of the United Kingdom",
            },
            {"text": "Unknown City", "label": "GPE"},  # No Wikidata
            {"text": "Random Org", "label": "ORG"},  # No Wikidata
        ],
    }

    (tmp_path / "test.entities.json").write_text(json.dumps(entities))

    runner = CliRunner()
    output_csv = tmp_path / "output.csv"

    result = runner.invoke(cli, ["compile", str(tmp_path), "-o", str(output_csv)])

    assert result.exit_code == 0

    # Read CSV
    with open(output_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 4

    # Check entities with Wikidata
    paris_row = [r for r in rows if r["text"] == "Paris"][0]
    assert paris_row["wikidata_id"] == "Q90"
    assert "Q90" in paris_row["wikidata_url"]
    assert "France" in paris_row["wikidata_description"]

    london_row = [r for r in rows if r["text"] == "London"][0]
    assert london_row["wikidata_id"] == "Q84"
    assert "Q84" in london_row["wikidata_url"]
    assert "United Kingdom" in london_row["wikidata_description"]

    # Check entities without Wikidata (should have empty strings)
    unknown_row = [r for r in rows if r["text"] == "Unknown City"][0]
    assert unknown_row["wikidata_id"] == ""
    assert unknown_row["wikidata_url"] == ""
    assert unknown_row["wikidata_description"] == ""

    random_row = [r for r in rows if r["text"] == "Random Org"][0]
    assert random_row["wikidata_id"] == ""
    assert random_row["wikidata_url"] == ""
    assert random_row["wikidata_description"] == ""


def test_compile_sorted_output(tmp_path):
    """Test that output is sorted by label then text."""
    entities = {
        "source_file": "test.eml",
        "format": "eml",
        "entities": [
            {"text": "Zebra Corp", "label": "ORG"},
            {"text": "Alice", "label": "PERSON"},
            {"text": "Boston", "label": "GPE"},
            {"text": "Bob", "label": "PERSON"},
            {"text": "Apple Inc", "label": "ORG"},
            {"text": "Atlanta", "label": "GPE"},
        ],
    }

    (tmp_path / "test.entities.json").write_text(json.dumps(entities))

    runner = CliRunner()
    output_csv = tmp_path / "output.csv"

    result = runner.invoke(cli, ["compile", str(tmp_path), "-o", str(output_csv)])

    assert result.exit_code == 0

    # Read CSV
    with open(output_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Check sorting: first by label (GPE, ORG, PERSON), then by text
    assert rows[0]["label"] == "GPE"
    assert rows[0]["text"] == "Atlanta"
    assert rows[1]["label"] == "GPE"
    assert rows[1]["text"] == "Boston"
    assert rows[2]["label"] == "ORG"
    assert rows[2]["text"] == "Apple Inc"
    assert rows[3]["label"] == "ORG"
    assert rows[3]["text"] == "Zebra Corp"
    assert rows[4]["label"] == "PERSON"
    assert rows[4]["text"] == "Alice"
    assert rows[5]["label"] == "PERSON"
    assert rows[5]["text"] == "Bob"


def test_compile_preserves_wikidata_on_duplicate(tmp_path):
    """Test that when deduplicating, Wikidata info is preserved."""
    # Two files with same entity, one has Wikidata info
    entities1 = {
        "source_file": "email1.eml",
        "format": "eml",
        "entities": [
            {
                "text": "Berlin",
                "label": "GPE",
                "wikidata_id": "Q64",
                "wikidata_url": "http://www.wikidata.org/entity/Q64",
                "wikidata_description": "capital of Germany",
            }
        ],
    }

    entities2 = {
        "source_file": "email2.eml",
        "format": "eml",
        "entities": [
            {"text": "Berlin", "label": "GPE"}  # Same entity, no Wikidata
        ],
    }

    (tmp_path / "email1.entities.json").write_text(json.dumps(entities1))
    (tmp_path / "email2.entities.json").write_text(json.dumps(entities2))

    runner = CliRunner()
    output_csv = tmp_path / "output.csv"

    result = runner.invoke(cli, ["compile", str(tmp_path), "-o", str(output_csv)])

    assert result.exit_code == 0

    # Read CSV
    with open(output_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should have only 1 Berlin entry
    assert len(rows) == 1

    # The Wikidata info should be preserved (from whichever was added first to the set)
    berlin_row = rows[0]
    assert berlin_row["text"] == "Berlin"
    # Entity with Wikidata was in entities1 - it should preserve that data
    assert berlin_row["wikidata_id"] == "Q64"


def test_compile_print_option(temp_entities_dir):
    """Test that --print option displays entities in console and does not save CSV."""
    runner = CliRunner()
    output_csv = temp_entities_dir / "output.csv"

    result = runner.invoke(
        cli, ["compile", str(temp_entities_dir), "-o", str(output_csv), "--print"]
    )

    assert result.exit_code == 0
    # Should include table output
    assert "Compiled Entities" in result.output
    assert "John Doe" in result.output
    assert "Acme Corp" in result.output
    # CSV should NOT be created when --print is used
    assert not output_csv.exists()


def test_compile_no_print_creates_csv(temp_entities_dir):
    """Test that CSV is created when --print is not specified."""
    runner = CliRunner()
    output_csv = temp_entities_dir / "output.csv"

    result = runner.invoke(
        cli, ["compile", str(temp_entities_dir), "-o", str(output_csv)]
    )

    assert result.exit_code == 0
    # Should NOT include table output
    assert "Compiled Entities" not in result.output
    # Should show save message
    assert "Entities saved to:" in result.output
    # CSV should be created
    assert output_csv.exists()


def test_compile_source_emails_tracking(tmp_path):
    """Test that source emails are tracked for each entity."""
    entities1 = {
        "source_file": "email1.eml",
        "format": "eml",
        "entities": [
            {"text": "Shared Entity", "label": "PERSON"},
            {"text": "Unique to Email 1", "label": "ORG"},
        ],
    }

    entities2 = {
        "source_file": "email2.eml",
        "format": "eml",
        "entities": [
            {"text": "Shared Entity", "label": "PERSON"},  # Duplicate
            {"text": "Unique to Email 2", "label": "ORG"},
        ],
    }

    entities3 = {
        "source_file": "email3.eml",
        "format": "eml",
        "entities": [
            {"text": "Shared Entity", "label": "PERSON"},  # Duplicate
        ],
    }

    (tmp_path / "email1.entities.json").write_text(json.dumps(entities1))
    (tmp_path / "email2.entities.json").write_text(json.dumps(entities2))
    (tmp_path / "email3.entities.json").write_text(json.dumps(entities3))

    runner = CliRunner()
    output_csv = tmp_path / "output.csv"

    result = runner.invoke(cli, ["compile", str(tmp_path), "-o", str(output_csv)])

    assert result.exit_code == 0

    with open(output_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Check shared entity has all three sources (without .eml extension)
    shared_row = [r for r in rows if r["text"] == "Shared Entity"][0]
    assert "email1" in shared_row["source_emails"]
    assert "email2" in shared_row["source_emails"]
    assert "email3" in shared_row["source_emails"]
    assert (
        shared_row["source_emails"].count(" | ") == 2
    )  # Two separators for three items
    assert ".eml" not in shared_row["source_emails"]

    # Check unique entities have single source
    unique1_row = [r for r in rows if r["text"] == "Unique to Email 1"][0]
    assert unique1_row["source_emails"] == "email1"
    assert " | " not in unique1_row["source_emails"]


def test_compile_single_file(tmp_path):
    """Test compile with a single entity JSON file."""
    entities = {
        "source_file": "single.eml",
        "format": "eml",
        "entities": [
            {"text": "Test Person", "label": "PERSON"},
            {"text": "Test Org", "label": "ORG"},
        ],
    }

    json_file = tmp_path / "single.entities.json"
    json_file.write_text(json.dumps(entities))

    runner = CliRunner()
    output_csv = tmp_path / "output.csv"

    # Pass the single file instead of directory
    result = runner.invoke(cli, ["compile", str(json_file), "-o", str(output_csv)])

    assert result.exit_code == 0
    assert output_csv.exists()

    with open(output_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2
