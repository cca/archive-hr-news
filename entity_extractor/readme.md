# Entity Extractor

Python CLI tool for extracting named entities (people, organizations, locations) from emails using spaCy NER. The entities are stored as JSON files with names that collocate them alongside their source email files. The tool can process EML, HTML, and PDF files and outputs structured JSON with entity information. Optional Wikidata linking is available.

## Installation

1. Install dependencies using uv: `uv sync`
2. Download the spaCy language model: `uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl`

## Usage

### Basic Commands

```bash
# Process all email files in a directory
extract-entities data/
# Process a single file:
extract-entities data/email.eml
# With Wikidata linking:
extract-entities data/ --wikidata
# Process a specific format:
extract-entities data/ --format html
```

### CLI Options

```bash
Options:
  -o, --output-dir PATH       Output directory for JSON files (default: same as input)
  -f, --format TEXT           File format to process (default: eml)
  --wikidata / --no-wikidata  Enable Wikidata entity linking (slower)
  -m, --model TEXT            spaCy model to use (default: en_core_web_sm)
  -e, --entity-types TEXT     Comma-separated entity types to extract (default: PERSON,ORG,GPE,LOC)
  --help                      Show this message and exit.
```

## Output Format

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
├── __init__.py       # Package initialization
├── cli.py            # Rich CLI interface
├── parsers.py        # Email parsing (EML, HTML, PDF)
├── ner.py            # spaCy NER processing
├── wikidata.py       # Wikidata entity linking
└── models.py         # Data models (Entity, EmailEntities)
```

### Parser Priority

1. **EML** (best): Native email format with structured headers and plain text body
2. **HTML**: Structured markup, easy to extract text
3. **PDF**: Last resort, text extraction can be unreliable

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black entity_extractor/ # format code
uv run ruff check entity_extractor/ # lint code
```

## Troubleshooting

### Version compatibility warning

The warning about spaCy version compatibility is expected and can be ignored unless you see actual errors.

## Future Enhancements

- Check extracted entities for CCA affiliations
- Batch processing with parallel workers
- Custom entity recognition rules
- Integration with other knowledge bases (VIAF, LCNAF)
- Export to different formats (CSV, TSV, SQLite)
