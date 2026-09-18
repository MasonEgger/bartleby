# ABOUTME: Content export — serialise published pages as JSONL, JSON, or CSV.
# Reuses the published-content selection so export and build agree on what ships.

from __future__ import annotations

import csv
import io
import json
from typing import TYPE_CHECKING

from bartleby.content_query import select_published
from bartleby.urls import generate_url

if TYPE_CHECKING:
    from bartleby.config import BartlebyConfig
    from bartleby.content import Page

# Export formats understood by ``bartleby export`` (spec.md ``bartleby export``).
FORMAT_JSONL = "jsonl"
FORMAT_JSON = "json"
FORMAT_CSV = "csv"

# Field order used for the CSV header so columns are stable across runs.
_CSV_COLUMNS = ("path", "url", "type", "title", "date", "authors", "tags", "word_count")


def export_content(
    pages: list[Page],
    config: BartlebyConfig,
    *,
    fmt: str = FORMAT_JSONL,
    content_type: str | None = None,
    include_content: bool = False,
    include_html: bool = False,
) -> str:
    """Serialise published content in a structured export format.

    :param pages: Discovered content pages (drafts are filtered here).
    :param config: The loaded site configuration (for URL generation).
    :param fmt: ``jsonl`` (default), ``json``, or ``csv``.
    :param content_type: When set, restrict the export to this content type.
    :param include_content: When ``True``, embed each page's raw markdown body.
    :param include_html: When ``True``, embed each page's rendered HTML.
    :returns: The serialised export as a single string.
    :raises ValueError: When ``fmt`` is not a recognised export format.
    """
    selected = select_published(pages)
    if content_type is not None:
        selected = [page for page in selected if page.content_type_name == content_type]
    records = [
        _record(page, config, include_content=include_content, include_html=include_html)
        for page in selected
    ]

    if fmt == FORMAT_JSONL:
        return "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    if fmt == FORMAT_JSON:
        return json.dumps(records, ensure_ascii=False)
    if fmt == FORMAT_CSV:
        return _to_csv(records)
    raise ValueError(f"unknown export format {fmt!r}")


def _record(
    page: Page,
    config: BartlebyConfig,
    *,
    include_content: bool,
    include_html: bool,
) -> dict[str, object]:
    """Build one curated export record for a page."""
    record: dict[str, object] = {
        "path": page.source_path.as_posix(),
        "url": _url_for(page, config),
        "type": page.content_type_name,
        "title": page.title,
        "date": page.date.isoformat() if page.date is not None else None,
        "word_count": len(page.raw_content.split()),
    }
    if page.description is not None:
        record["description"] = page.description
    if page.author_keys:
        record["authors"] = list(page.author_keys)
    for taxonomy_name, terms in page.taxonomy_values.items():
        record[taxonomy_name] = list(terms)
    if include_content:
        record["content"] = page.raw_content
    if include_html:
        record["html"] = page.rendered_content
    return record


def _to_csv(records: list[dict[str, object]]) -> str:
    """Render records to CSV, joining list-valued fields with commas."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(_CSV_COLUMNS), extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow({column: _csv_value(record.get(column)) for column in _CSV_COLUMNS})
    return buffer.getvalue()


def _csv_value(value: object) -> str:
    """Coerce a record value into a CSV cell string."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def _url_for(page: Page, config: BartlebyConfig) -> str:
    """Compute a page's output URL without mutating the page."""
    content_type = (
        config.content_types.get(page.content_type_name) if page.content_type_name else None
    )
    return generate_url(page, content_type)
