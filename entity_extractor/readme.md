# Entity Extractor

Python CLI tool for extracting named entities (people, organizations, locations) from emails using spaCy NER. The entities are stored as JSON files with names that collocate them alongside their source email files. The tool can process EML (default), HTML, and PDF files and outputs structured JSON with entity information. Optional Wikidata linking is available.

## Installation

1. Install dependencies using uv: `uv sync`
2. Download the spaCy language model: `uv run spacy download en_core_web_sm`

## Usage

The CLI has two main subcommands: `extract` for processing emails and `compile` for aggregating entities.

### Extract Subcommand

Extract named entities from email files:

```bash
# Process all email files in a directory
uv run extract-entities extract data/
# Process a single file
uv run extract-entities extract data/email.eml
# With Wikidata linking
uv run extract-entities extract data/ --wikidata
# Process a specific format
uv run extract-entities extract data/ --format html
```

**Options:**

- `-o, --output-dir PATH` - Output directory for JSON files (default: same as input)
- `-f, --format [eml|html|pdf]` - File format to process (default: eml)
- `--wikidata / --no-wikidata` - Enable Wikidata entity linking (slower)
- `-m, --model TEXT` - spaCy model to use (default: en_core_web_sm)
- `-e, --entity-types TEXT` - Comma-separated entity types to extract (default: PERSON,ORG,GPE,LOC)

### Compile Subcommand

Compile a deduplicated list of all entities from existing entity JSON files:

```bash
# Compile all entities from a directory to CSV
uv run extract-entities compile data/
# Specify output location
uv run extract-entities compile data/ -o entities.csv
# Print to console instead of saving CSV
uv run extract-entities compile data/ --print
# Process a single entity file
uv run extract-entities compile data/email.entities.json
```

**Options:**

- `-o, --output PATH` - Output CSV file path (default: entities.csv in input directory)
- `--print / --no-print` - Print entities to console instead of saving to CSV

## Output Formats

### Extract Output

For each processed email, a JSON file is created with the `.entities.json` extension:

```json
{
  "source_file": "email.eml",
  "format": "eml",
  "subject": "Important Message",
  "entities": [
    {
      "text": "Stephen Beal",
      "label": "PERSON",
      "wikidata_id": "Q7608685",
      "wikidata_url": "https://www.wikidata.org/wiki/Q7608685",
      "wikidata_description": "American artist"
    }
  ]
}
```

### Compile Output

Outputs a CSV of deduplicated entities (case-insensitive) with pipe-separated source email filenames for each entity.

### Entity Types

Default entity types extracted:

- **PERSON** - People, including fictional characters
- **ORG** - Organizations, companies, agencies, institutions
- **GPE** - Geopolitical entities (countries, cities, states)
- **LOC** - Non-GPE locations (mountain ranges, bodies of water)

See [spaCy's documentation](https://spacy.io/models/en#en_core_web_sm-labels) for all available entity types.

## Programmatic Usage

```python
from pathlib import Path
from entity_extractor.parsers import parse_email_file
from entity_extractor.ner import NERProcessor

# Initialize NER processor
ner = NERProcessor()

# Parse email
text, subject, fmt = parse_email_file(Path("email.eml"))

# Extract entities
result = ner.extract_entities(
    text=text,
    source_file="email.eml",
    file_format=fmt,
    subject=subject
)

# Access entities
for entity in result.entities:
    print(f"{entity.text} ({entity.label})")
```

## Architecture

```bash
entity_extractor/
├── tests/            # Unit tests
├── __init__.py       # Package initialization
├── cli.py            # Rich CLI interface
├── parsers.py        # Email parsing (EML, HTML, PDF)
├── ner.py            # spaCy NER processing
├── wikidata.py       # Wikidata entity linking
└── models.py         # Data models (Entity, EmailEntities)
```

## Development

```bash
uv run pytest # tests
uv run ruff check entity_extractor # lint code
uv run ruff format --check entity_extractor # format code
```

## Troubleshooting

### Version compatibility warning

The warning about spaCy version compatibility is expected and can be ignored unless you see actual errors.
