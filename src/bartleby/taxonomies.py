# ABOUTME: Taxonomy system — term collection, page mapping, and page generation.
# Produces site-wide and per-content-type taxonomy index and term listing pages.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bartleby.content import Page
from bartleby.urls import slugify

if TYPE_CHECKING:
    from bartleby.config import BartlebyConfig


@dataclass(slots=True)
class TaxonomyTerm:
    """One term within a taxonomy (e.g. ``"python"`` under ``"tags"``)."""

    name: str
    slug: str
    pages: list[Page] = field(default_factory=list)
    count: int = 0


@dataclass(slots=True)
class TaxonomyData:
    """A taxonomy's collected terms, optionally scoped to a content type."""

    name: str
    terms: dict[str, TaxonomyTerm] = field(default_factory=dict)
    content_type: str | None = None


@dataclass(slots=True)
class AllTaxonomies:
    """Site-wide and per-content-type taxonomy data, ready for page generation."""

    global_taxonomies: dict[str, TaxonomyData] = field(default_factory=dict)
    content_type_taxonomies: dict[str, dict[str, TaxonomyData]] = field(default_factory=dict)


def build_taxonomies(pages: list[Page], config: BartlebyConfig) -> AllTaxonomies:
    """Collect taxonomy terms across pages, honoring per-content-type opt-ins."""
    result = AllTaxonomies()
    opted_in_taxonomies: set[str] = set()
    for content_type in config.content_types.values():
        opted_in_taxonomies.update(content_type.taxonomies)

    for taxonomy_name in opted_in_taxonomies:
        if taxonomy_name not in config.taxonomies:
            continue
        result.global_taxonomies[taxonomy_name] = TaxonomyData(name=taxonomy_name)

    for page in pages:
        content_type_name = page.content_type_name
        if content_type_name is None:
            continue
        content_type_optional = config.content_types.get(content_type_name)
        if content_type_optional is None:
            continue
        content_type = content_type_optional
        for taxonomy_name in content_type.taxonomies:
            taxonomy_config = config.taxonomies.get(taxonomy_name)
            if taxonomy_config is None:
                continue
            values = page.taxonomy_values.get(taxonomy_name, [])
            for value in values:
                _add_term(result.global_taxonomies[taxonomy_name], value, page, taxonomy_config)
                ct_taxonomies = result.content_type_taxonomies.setdefault(content_type_name, {})
                taxonomy_data = ct_taxonomies.setdefault(
                    taxonomy_name, TaxonomyData(name=taxonomy_name, content_type=content_type_name)
                )
                _add_term(taxonomy_data, value, page, taxonomy_config)

    _sort_term_pages(result)
    return result


def generate_taxonomy_pages(taxonomy_data: AllTaxonomies, config: BartlebyConfig) -> list[Page]:
    """Produce virtual :class:`Page` objects for taxonomy index and term URLs."""
    del config  # currently unused — kept for parity with spec and future filtering
    pages: list[Page] = []

    for taxonomy_name, data in taxonomy_data.global_taxonomies.items():
        pages.append(_make_taxonomy_index_page(taxonomy_name, data, content_type=None))
        for term_name, term in data.terms.items():
            pages.append(
                _make_taxonomy_term_page(taxonomy_name, term_name, term, content_type=None)
            )

    for content_type_name, taxonomies in taxonomy_data.content_type_taxonomies.items():
        for taxonomy_name, data in taxonomies.items():
            pages.append(
                _make_taxonomy_index_page(taxonomy_name, data, content_type=content_type_name)
            )
            for term_name, term in data.terms.items():
                pages.append(
                    _make_taxonomy_term_page(
                        taxonomy_name, term_name, term, content_type=content_type_name
                    )
                )
    return pages


def _add_term(
    taxonomy_data: TaxonomyData,
    value: str,
    page: Page,
    taxonomy_config: object,
) -> None:
    """Add ``page`` to ``value`` under ``taxonomy_data``, computing the term slug once."""
    if value not in taxonomy_data.terms:
        slug_format = getattr(taxonomy_config, "slug_format", "{slug}")
        slug = slug_format.replace("{slug}", slugify(value))
        taxonomy_data.terms[value] = TaxonomyTerm(name=value, slug=slug)
    term = taxonomy_data.terms[value]
    if page not in term.pages:
        term.pages.append(page)
        term.count = len(term.pages)


def _sort_term_pages(result: AllTaxonomies) -> None:
    """Sort each term's pages newest-first by date (None dates sort last)."""

    def key(page: Page) -> tuple[int, str]:
        # Pages with dates come first (0 vs. 1), then by ISO date string descending.
        return (0 if page.date is not None else 1, page.date.isoformat() if page.date else "")

    for data in result.global_taxonomies.values():
        for term in data.terms.values():
            term.pages.sort(key=key, reverse=False)
            # `reverse=False` with the tuple keeps dateless pages last; we want
            # newest dates first, so reverse the dated-page block in place.
            dated = [page for page in term.pages if page.date is not None]
            dated.sort(key=lambda page: page.date, reverse=True)  # type: ignore[arg-type, return-value]
            undated = [page for page in term.pages if page.date is None]
            term.pages = dated + undated

    for ct_taxonomies in result.content_type_taxonomies.values():
        for data in ct_taxonomies.values():
            for term in data.terms.values():
                dated = [page for page in term.pages if page.date is not None]
                dated.sort(key=lambda page: page.date, reverse=True)  # type: ignore[arg-type, return-value]
                undated = [page for page in term.pages if page.date is None]
                term.pages = dated + undated


def _make_taxonomy_index_page(
    taxonomy_name: str, data: TaxonomyData, *, content_type: str | None
) -> Page:
    """Build a virtual page for the taxonomy's index URL (``/tags/`` etc.)."""
    url = f"/{content_type}/{taxonomy_name}/" if content_type is not None else f"/{taxonomy_name}/"
    page = Page(
        source_path=Path("__generated__")
        / "taxonomy"
        / (content_type or "_global")
        / taxonomy_name,
        abs_source_path=Path("/__generated__/taxonomy")
        / (content_type or "_global")
        / taxonomy_name,
        title=taxonomy_name.title(),
        content_type_name=content_type,
        custom_metadata={
            "taxonomy_name": taxonomy_name,
            "taxonomy_kind": "index",
        },
    )
    page.output_url = url
    return page


def _make_taxonomy_term_page(
    taxonomy_name: str,
    term_name: str,
    term: TaxonomyTerm,
    *,
    content_type: str | None,
) -> Page:
    """Build a virtual page for one taxonomy term (``/tags/python/`` etc.)."""
    url = (
        f"/{content_type}/{taxonomy_name}/{term.slug}/"
        if content_type is not None
        else f"/{taxonomy_name}/{term.slug}/"
    )
    page = Page(
        source_path=Path("__generated__")
        / "taxonomy"
        / (content_type or "_global")
        / taxonomy_name
        / term.slug,
        abs_source_path=Path("/__generated__/taxonomy")
        / (content_type or "_global")
        / taxonomy_name
        / term.slug,
        title=f"{taxonomy_name.title()}: {term_name}",
        content_type_name=content_type,
        custom_metadata={
            "taxonomy_name": taxonomy_name,
            "taxonomy_kind": "term",
            "taxonomy_term": term_name,
            "posts": term.pages,
        },
    )
    page.output_url = url
    return page
