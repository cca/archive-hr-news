# Archive HR Newsletters

Several tools for email archiving at CCA.

## Apps Script

Google Apps Script to search a Gmail inbox for particular emails and save them to a Drive folder. See [apps_script/readme.md](apps_script/readme.md) for details.

## Entity Extractor

Python CLI tool for extracting named entities (people, organizations, locations) from emails using spaCy NER. Download the emails stored in Drive from the apps script locally to work on them. Processes EML (preferred), HTML, and PDF files and outputs structured JSON with entity information. Optional Wikidata linking for entity enrichment. See [entity_extractor/readme.md](entity_extractor/readme.md) for details.

### Setup

```bash
# Install dependencies & spaCy model
uv sync
uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
# Extract entities from emails
extract-entities data/
```

## License

[ECL-2.0](https://opensource.org/license/ecl-2-0)
