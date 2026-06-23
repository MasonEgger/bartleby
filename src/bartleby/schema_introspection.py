# ABOUTME: Schema introspection — derive content-type, author, and taxonomy schemas.
# Backs `bartleby schema` and the static schema.json the agent surface reuses.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bartleby.taxonomies import build_taxonomies

if TYPE_CHECKING:
    from bartleby.authors import Author
    from bartleby.config import BartlebyConfig
    from bartleby.content import Page


class SchemaError(Exception):
    """Raised when a schema is requested for something that is not defined."""


@dataclass(slots=True)
class ContentTypeSchema:
    """Introspected schema for one content type (the ``bartleby schema <type>`` shape).

    The ``to_dict`` form is the stable contract that ``schema.json`` reuses in the
    static agent surface, so its key names match the documented manifest shape.
    """

    content_type: str
    path: str
    url_base: str | None
    url_format: str | None
    required_fields: list[dict[str, object]]
    optional_fields: list[dict[str, object]]
    features: dict[str, object]

    @property
    def exit_code(self) -> int:
        return 0

    def to_dict(self) -> dict[str, object]:
        return {
            "content_type": self.content_type,
            "path": self.path,
            "url_base": self.url_base,
            "url_format": self.url_format,
            "required_fields": self.required_fields,
            "optional_fields": self.optional_fields,
            "features": self.features,
        }

    def to_text(self) -> str:
        lines = [f"content type: {self.content_type} ({self.path})"]
        lines.append("required:")
        lines += [_field_line(field) for field in self.required_fields] or ["  (none)"]
        lines.append("optional:")
        lines += [_field_line(field) for field in self.optional_fields] or ["  (none)"]
        return "\n".join(lines)


@dataclass(slots=True)
class AuthorsSchema:
    """Introspected public author list (the ``bartleby schema authors`` shape)."""

    authors: list[dict[str, object]]

    @property
    def exit_code(self) -> int:
        return 0

    def to_dict(self) -> dict[str, object]:
        return {"authors": self.authors}

    def to_text(self) -> str:
        if not self.authors:
            return "no authors defined"
        return "\n".join(f"{entry['id']}: {entry['name']}" for entry in self.authors)


@dataclass(slots=True)
class TaxonomiesSchema:
    """Introspected taxonomies with in-use terms (the ``bartleby schema taxonomies`` shape)."""

    taxonomies: list[dict[str, object]]

    @property
    def exit_code(self) -> int:
        return 0

    def to_dict(self) -> dict[str, object]:
        return {"taxonomies": self.taxonomies}

    def to_text(self) -> str:
        if not self.taxonomies:
            return "no taxonomies defined"
        lines: list[str] = []
        for taxonomy in self.taxonomies:
            terms = taxonomy["terms"]
            assert isinstance(terms, list)
            joined = ", ".join(f"{term['term']} ({term['count']})" for term in terms) or "(none)"
            lines.append(f"{taxonomy['name']}: {joined}")
        return "\n".join(lines)


def derive_content_type_schema(type_name: str, config: BartlebyConfig) -> ContentTypeSchema:
    """Derive the field schema for one content type from config.

    :param type_name: The content type name (e.g. ``"blog"``).
    :param config: The loaded site configuration.
    :returns: A :class:`ContentTypeSchema` describing required/optional fields and features.
    :raises SchemaError: If ``type_name`` is not a defined content type.
    """
    content_type = config.content_types.get(type_name)
    if content_type is None:
        raise SchemaError(f"unknown content type {type_name!r}")

    required_fields: list[dict[str, object]] = []
    optional_fields: list[dict[str, object]] = []
    for field_name, field_schema in content_type.metadata.items():
        descriptor: dict[str, object] = {"name": field_name, "type": field_schema.field_type}
        if field_schema.choices is not None:
            descriptor["choices"] = field_schema.choices
        if field_schema.required:
            required_fields.append(descriptor)
        else:
            optional_fields.append(descriptor)

    features: dict[str, object] = {
        "pagination": content_type.pagination.enabled,
        "per_page": content_type.pagination.per_page,
        "feeds": list(content_type.feeds),
        "readtime": content_type.readtime,
    }
    if content_type.excerpt_separator is not None:
        features["excerpt_separator"] = content_type.excerpt_separator

    return ContentTypeSchema(
        content_type=type_name,
        path=content_type.path,
        url_base=content_type.url_base,
        url_format=content_type.url_format,
        required_fields=required_fields,
        optional_fields=optional_fields,
        features=features,
    )


def derive_authors_schema(authors: dict[str, Author]) -> AuthorsSchema:
    """Derive the public author list, omitting any non-public fields.

    :param authors: The authors mapping from :func:`bartleby.authors.load_authors`.
    :returns: An :class:`AuthorsSchema` carrying public author data only.
    """
    listed: list[dict[str, object]] = []
    for author in authors.values():
        entry: dict[str, object] = {"id": author.key, "name": author.name}
        if author.url is not None:
            entry["url"] = author.url
        if author.avatar is not None:
            entry["image"] = author.avatar
        if author.description is not None:
            entry["bio"] = author.description
        listed.append(entry)
    return AuthorsSchema(authors=listed)


def derive_taxonomies_schema(pages: list[Page], config: BartlebyConfig) -> TaxonomiesSchema:
    """Derive each taxonomy's in-use terms with counts from the discovered pages.

    Term collection reuses :func:`bartleby.taxonomies.build_taxonomies` so the
    schema's notion of an in-use term matches what the build itself indexes.

    :param pages: Discovered content pages.
    :param config: The loaded site configuration.
    :returns: A :class:`TaxonomiesSchema` listing taxonomies and their terms.
    """
    collected = build_taxonomies(pages, config)
    taxonomies: list[dict[str, object]] = []
    for taxonomy_name, taxonomy_config in config.taxonomies.items():
        data = collected.global_taxonomies.get(taxonomy_name)
        terms: list[dict[str, object]] = []
        if data is not None:
            for term in data.terms.values():
                terms.append({"term": term.name, "count": term.count})
        taxonomies.append(
            {
                "name": taxonomy_name,
                "slug_format": taxonomy_config.slug_format,
                "terms": terms,
            }
        )
    return TaxonomiesSchema(taxonomies=taxonomies)


def _field_line(field: dict[str, object]) -> str:
    """Render one field descriptor as an indented human-readable line."""
    suffix = f" choices={field['choices']}" if "choices" in field else ""
    return f"  {field['name']}: {field['type']}{suffix}"
