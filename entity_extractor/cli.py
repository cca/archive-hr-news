"""Command-line interface for email entity extraction."""

import json
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from .models import EmailEntities
from .ner import NERProcessor
from .parsers import parse_email_file
from .wikidata import WikidataLinker

console = Console()


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for JSON files (default: same as input)",
)
@click.option(
    "--format",
    "-f",
    default="eml",
    type=click.Choice(["eml", "html", "pdf"], case_sensitive=False),
    help="File format to process (default: eml)",
)
@click.option(
    "--wikidata/--no-wikidata",
    default=False,
    help="Enable Wikidata entity linking (slower)",
)
@click.option(
    "--model",
    "-m",
    default="en_core_web_sm",
    help="spaCy model to use (default: en_core_web_sm)",
)
@click.option(
    "--entity-types",
    "-e",
    default="PERSON,ORG,GPE,LOC",
    help="Comma-separated entity types to extract (default: PERSON,ORG,GPE,LOC)",
)
def main(
    input_path: Path,
    output_dir: Optional[Path],
    format: str,
    wikidata: bool,
    model: str,
    entity_types: str,
):
    """
    Extract named entities from email files.

    INPUT_PATH can be a single file or a directory of email files.
    Only one format is processed at a time to avoid overwriting output files.
    """
    console.print(
        Panel.fit(
            "[bold cyan]Email Entity Extractor[/bold cyan]\n"
            "Extracting named entities using spaCy NER",
            border_style="cyan",
        )
    )

    # Parse options
    file_extension = f".{format.lower()}"
    entity_type_list = [et.strip() for et in entity_types.split(",")]

    # Collect files to process
    files = collect_files(input_path, file_extension)

    if not files:
        console.print("[yellow]No matching files found.[/yellow]")
        return

    console.print(f"\n[green]Found {len(files)} file(s) to process[/green]")

    # Initialize processors
    try:
        ner_processor = NERProcessor(model_name=model)
        # Test loading the model
        _ = ner_processor.nlp
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    wikidata_linker = WikidataLinker() if wikidata else None

    if wikidata:
        console.print("[yellow]Wikidata linking enabled (this will be slower)[/yellow]")

    # Process files with progress bar
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Processing emails...", total=len(files))

        for file_path in files:
            progress.update(task, description=f"[cyan]Processing {file_path.name}...")

            try:
                result = process_file(
                    file_path,
                    output_dir or file_path.parent,
                    ner_processor,
                    wikidata_linker,
                    entity_type_list,
                )
                results.append(result)
            except Exception as e:
                console.print(f"[red]Error processing {file_path.name}: {e}[/red]")

            progress.advance(task)

    # Display summary
    display_summary(results)


def collect_files(input_path: Path, file_extension: str) -> List[Path]:
    """Collect all email files to process for the specified format."""
    if input_path.is_file():
        if input_path.suffix.lower() == file_extension:
            return [input_path]
        else:
            # If a specific file is given but doesn't match the format, still process it
            return [input_path]

    # Directory - collect all files with the specified extension
    files = list(input_path.glob(f"*{file_extension}"))

    return sorted(files)


def process_file(
    file_path: Path,
    output_dir: Path,
    ner_processor: NERProcessor,
    wikidata_linker: Optional[WikidataLinker],
    entity_types: List[str],
) -> EmailEntities:
    """Process a single email file."""
    # Parse the email
    text, subject, file_format = parse_email_file(file_path)

    # Extract entities
    email_entities = ner_processor.extract_entities(
        text=text,
        source_file=str(file_path.name),
        file_format=file_format,
        subject=subject,
        entity_types=entity_types,
    )

    # Optionally enrich with Wikidata
    if wikidata_linker and email_entities.entities:
        email_entities.entities = wikidata_linker.enrich_entities(
            email_entities.entities
        )

    # Save to JSON
    output_file = output_dir / f"{file_path.stem}.entities.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(email_entities.to_dict(), f, indent=2, ensure_ascii=False)

    return email_entities


def display_summary(results: List[EmailEntities]):
    """Display a summary of processed files."""
    console.print("\n")

    table = Table(
        title="Extraction Summary", show_header=True, header_style="bold magenta"
    )
    table.add_column("File", style="cyan")
    table.add_column("Format", style="blue")
    table.add_column("Entities", justify="right", style="green")
    table.add_column("People", justify="right", style="yellow")
    table.add_column("Organizations", justify="right", style="yellow")

    total_entities = 0
    total_people = 0
    total_orgs = 0

    for result in results:
        entity_count = len(result.entities)
        people_count = sum(1 for e in result.entities if e.label == "PERSON")
        org_count = sum(1 for e in result.entities if e.label == "ORG")

        total_entities += entity_count
        total_people += people_count
        total_orgs += org_count

        table.add_row(
            result.source_file,
            result.format,
            str(entity_count),
            str(people_count),
            str(org_count),
        )

    console.print(table)

    console.print(f"\n[bold green]Total:[/bold green] {len(results)} files processed")
    console.print(
        f"[bold green]Extracted:[/bold green] {total_entities} entities "
        f"({total_people} people, {total_orgs} organizations)"
    )

    if results:
        console.print("\n[dim]Output files saved with .entities.json extension[/dim]")


if __name__ == "__main__":
    main()
