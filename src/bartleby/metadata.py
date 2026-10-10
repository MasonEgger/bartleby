# ABOUTME: Build-time metadata validation against content type schemas.
# Checks required fields, type constraints, choice lists, and author references.

"""Build-time metadata validation.

Error-message contract: a :class:`ValidationError` message names the schema entry that
the page broke, as ``content_types.<type>.metadata.<field>: <message> (fix: <hint>)``
(see :func:`bartleby.errors.format_error`). The page file travels separately in
``file_path``, so the build prints ``<file>: <message>``. An unknown author reference
lists the ids the authors file defines. Hints say what to write in the page's front
matter, or which schema line to relax.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bartleby.authors import unknown_author_hint
from bartleby.errors import format_error

if TYPE_CHECKING:
    from bartleby.authors import Author
    from bartleby.config import BartlebyConfig, ContentTypeConfig, MetadataFieldSchema
    from bartleby.content import Page


@dataclass(slots=True)
class ValidationError:
    """A single metadata validation problem found on a page.

    :ivar file_path: Path to the offending content file, relative to ``content/``.
    :ivar field: Name of the field that failed validation. Empty string for
        page-level errors not tied to a specific field.
    :ivar message: Human-readable description of the problem.
    """

    file_path: str
    field: str
    message: str


def validate_page_metadata(
    page: Page,
    content_type: ContentTypeConfig | None,
    authors: dict[str, Author],
) -> list[ValidationError]:
    """Validate a single page's metadata.

    :param page: The page to validate.
    :param content_type: The content type config governing this page, or
        ``None`` for static pages outside any content type.
    :param authors: Mapping of author keys loaded from ``.authors.yml``.
    :returns: List of :class:`ValidationError`; empty when the page is valid.
    """
    errors: list[ValidationError] = []
    file_path = str(page.source_path)

    if not page.title:
        errors.append(
            ValidationError(
                file_path=file_path,
                field="title",
                message="required field 'title' is missing",
            )
        )

    for key in page.author_keys:
        if key not in authors:
            errors.append(
                ValidationError(
                    file_path=file_path,
                    field="authors",
                    message=format_error(
                        f"unknown author key {key!r}",
                        key_path="authors",
                        hint=unknown_author_hint(authors),
                    ),
                )
            )

    if content_type is not None and page.content_type_name is not None:
        errors.extend(_validate_custom_metadata(page, content_type, file_path))

    return errors


def validate_all_metadata(
    pages: list[Page],
    config: BartlebyConfig,
    authors: dict[str, Author],
) -> list[ValidationError]:
    """Validate every page against its content type's schema.

    :param pages: All pages discovered by :func:`bartleby.content.discover_content`.
    :param config: The parsed Bartleby config.
    :param authors: Mapping of author keys loaded from ``.authors.yml``.
    :returns: Combined list of :class:`ValidationError` across all pages.
    """
    errors: list[ValidationError] = []
    for page in pages:
        content_type = (
            config.content_types.get(page.content_type_name) if page.content_type_name else None
        )
        errors.extend(validate_page_metadata(page, content_type, authors))
    return errors


def _validate_custom_metadata(
    page: Page,
    content_type: ContentTypeConfig,
    file_path: str,
) -> list[ValidationError]:
    """Apply the content type's metadata schema to ``page.custom_metadata``."""
    errors: list[ValidationError] = []
    for field_name, schema in content_type.metadata.items():
        schema_key = f"content_types.{content_type.name}.metadata.{field_name}"
        value = page.custom_metadata.get(field_name)
        if value is None:
            if schema.required:
                message = format_error(
                    f"required field {field_name!r} is missing",
                    key_path=schema_key,
                    hint=(
                        f"add `{field_name}:` to this file's front matter, "
                        "or set `required: false` in the schema"
                    ),
                )
                errors.append(ValidationError(file_path, field_name, message))
            continue
        type_error = _check_type(field_name, value, schema)
        if type_error is not None:
            message = format_error(
                type_error["message"],
                key_path=schema_key,
                hint=(
                    f"write a {schema.field_type} value in the front matter, "
                    "or change the field's `type:` in the schema"
                ),
            )
            errors.append(ValidationError(file_path, field_name, message))
            continue
        choice_error = _check_choices(field_name, value, schema)
        if choice_error is not None:
            message = format_error(
                choice_error["message"],
                key_path=schema_key,
                hint=f"set `{field_name}` to one of the listed choices",
            )
            errors.append(ValidationError(file_path, field_name, message))
    return errors


def _check_type(field_name: str, value: Any, schema: MetadataFieldSchema) -> dict[str, str] | None:
    """Return an error payload (field, message) when ``value`` violates ``schema.field_type``."""
    expected = schema.field_type
    if expected == "string":
        if isinstance(value, str):
            return None
        return {
            "field": field_name,
            "message": f"expected string for {field_name!r}, got {type(value).__name__}",
        }
    if expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return {
                "field": field_name,
                "message": f"expected integer for {field_name!r}, got {type(value).__name__}",
            }
        return None
    if expected == "boolean":
        if isinstance(value, bool):
            return None
        return {
            "field": field_name,
            "message": f"expected boolean for {field_name!r}, got {type(value).__name__}",
        }
    if expected == "date":
        if isinstance(value, datetime.date):
            return None
        if isinstance(value, str):
            try:
                datetime.date.fromisoformat(value)
            except ValueError:
                return {
                    "field": field_name,
                    "message": f"expected date for {field_name!r}, got unparseable string",
                }
            return None
        return {
            "field": field_name,
            "message": f"expected date for {field_name!r}, got {type(value).__name__}",
        }
    if expected == "list":
        if isinstance(value, list):
            return None
        return {
            "field": field_name,
            "message": f"expected list for {field_name!r}, got {type(value).__name__}",
        }
    return None


def _check_choices(
    field_name: str, value: Any, schema: MetadataFieldSchema
) -> dict[str, str] | None:
    """Return an error payload when ``value`` is outside ``schema.choices``."""
    if schema.choices is None:
        return None
    if value in schema.choices:
        return None
    options = ", ".join(repr(choice) for choice in schema.choices)
    return {
        "field": field_name,
        "message": f"{value!r} is not one of the allowed choices: {options}",
    }
