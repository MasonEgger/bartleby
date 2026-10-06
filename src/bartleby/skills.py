# ABOUTME: Deterministic agent-skill generation — bartleby-write/review/ops.
# Renders bundled skill templates filled with the site's actual shape (no NLP, no LLM, no network).

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bartleby.content_query import select_published
from bartleby.schema_introspection import (
    derive_authors_schema,
    derive_content_type_schema,
    derive_taxonomies_schema,
)

if TYPE_CHECKING:
    from bartleby.authors import Author
    from bartleby.config import AgentContext, BartlebyConfig
    from bartleby.content import Page


@dataclass(slots=True)
class GeneratedSkill:
    """One generated skill: its file stem and full markdown content."""

    name: str
    content: str

    @property
    def filename(self) -> str:
        """The skill's output filename (``<name>.md``)."""
        return f"{self.name}.md"


def generate_skills(
    pages: list[Page],
    config: BartlebyConfig,
    authors: dict[str, Author],
    *,
    shortcodes: list[str] | None = None,
    style_guide_text: str | None = None,
) -> list[GeneratedSkill]:
    """Generate the three agent skills from the site's shape, deterministically.

    The same config/schema inputs always produce byte-identical content: the
    skills are rendered from the derived schemas, sorted authors and taxonomy
    terms, and the explicit ``ai.agent_context`` (included verbatim when set).
    No content analysis is performed (deferred from v1).

    :param pages: Discovered content pages (drafts are filtered for term counts).
    :param config: The loaded site configuration.
    :param authors: The authors mapping.
    :param shortcodes: Available shortcode names to advertise (sorted on output).
    :param style_guide_text: Optional style-guide markdown, included verbatim.
    :returns: The write, review, and ops skills (in that order).
    """
    published = select_published(pages)
    shortcode_names = sorted(shortcodes or [])
    return [
        GeneratedSkill(
            name="bartleby-write",
            content=_write_skill(published, config, authors, shortcode_names, style_guide_text),
        ),
        GeneratedSkill(
            name="bartleby-review",
            content=_review_skill(published, config, style_guide_text),
        ),
        GeneratedSkill(name="bartleby-ops", content=_ops_skill(config)),
    ]


def _write_skill(
    pages: list[Page],
    config: BartlebyConfig,
    authors: dict[str, Author],
    shortcodes: list[str],
    style_guide_text: str | None,
) -> str:
    """Render the content-creation skill."""
    lines = [
        "---",
        "name: bartleby-write",
        f"description: Create content for {config.site.title}.",
        "---",
        "",
        f"# Writing for {config.site.title}",
        "",
        "## Content types",
        "",
    ]
    lines += _content_type_section(config)
    lines += ["", "## Authors", ""]
    lines += _authors_section(authors)
    lines += ["", "## Taxonomy terms in use", ""]
    lines += _taxonomy_section(pages, config)
    if shortcodes:
        lines += ["", "## Available shortcodes", ""]
        lines += [f"- `[% {name} %]`" for name in shortcodes]
    lines += _agent_context_section(config.ai.agent_context)
    lines += _style_guide_section(style_guide_text)
    lines += [
        "",
        "## Creating a post",
        "",
        "```bash",
        'bartleby new post "Title" --type <content-type> --output json',
        "```",
    ]
    return "\n".join(lines) + "\n"


def _review_skill(
    pages: list[Page],
    config: BartlebyConfig,
    style_guide_text: str | None,
) -> str:
    """Render the content-review skill."""
    lines = [
        "---",
        "name: bartleby-review",
        f"description: Review and improve content for {config.site.title}.",
        "---",
        "",
        f"# Reviewing content for {config.site.title}",
        "",
        "## Metadata schemas to check against",
        "",
    ]
    lines += _content_type_section(config)
    lines += ["", "## Existing taxonomy terms (prefer reusing these)", ""]
    lines += _taxonomy_section(pages, config)
    lines += _agent_context_section(config.ai.agent_context)
    lines += _style_guide_section(style_guide_text)
    lines += [
        "",
        "## Validating",
        "",
        "```bash",
        "bartleby validate --output json",
        "```",
    ]
    return "\n".join(lines) + "\n"


def _ops_skill(config: BartlebyConfig) -> str:
    """Render the site-operations skill."""
    lines = [
        "---",
        "name: bartleby-ops",
        f"description: Operate the {config.site.title} site.",
        "---",
        "",
        f"# Operating {config.site.title}",
        "",
        "## Build, validate, serve",
        "",
        "```bash",
        "bartleby build --output json",
        "bartleby validate --output json",
        "bartleby serve",
        "```",
        "",
        "## Discover existing content",
        "",
        "```bash",
        "bartleby content list --output json",
        "bartleby content get <path> --output json",
        "```",
        "",
        "## Schema introspection",
        "",
        "```bash",
        "bartleby schema <content-type> --output json",
        "bartleby schema taxonomies --output json",
        "bartleby schema authors --output json",
        "```",
        "",
        "## Export content",
        "",
        "```bash",
        "bartleby export --format jsonl --include-content",
        "```",
    ]
    return "\n".join(lines) + "\n"


def _content_type_section(config: BartlebyConfig) -> list[str]:
    """Render each content type's required/optional fields, sorted by name."""
    lines: list[str] = []
    for type_name in sorted(config.content_types):
        schema = derive_content_type_schema(type_name, config)
        lines.append(f"### {type_name}")
        lines.append("")
        lines.append("Required fields:")
        lines += _field_lines(schema.required_fields)
        lines.append("")
        lines.append("Optional fields:")
        lines += _field_lines(schema.optional_fields)
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _field_lines(fields: list[dict[str, object]]) -> list[str]:
    """Render a field list as markdown bullets, or a ``(none)`` placeholder."""
    if not fields:
        return ["- (none)"]
    rendered: list[str] = []
    for field_schema in fields:
        choices = field_schema.get("choices")
        suffix = ""
        if isinstance(choices, list):
            suffix = f" (choices: {', '.join(str(choice) for choice in choices)})"
        rendered.append(f"- `{field_schema['name']}` ({field_schema['type']}){suffix}")
    return rendered


def _authors_section(authors: dict[str, Author]) -> list[str]:
    """Render the author list, sorted by id, public fields only."""
    schema = derive_authors_schema(authors)
    entries = schema.to_dict()["authors"]
    assert isinstance(entries, list)
    if not entries:
        return ["- (none)"]
    ordered = sorted(entries, key=lambda entry: str(entry["id"]))
    return [f"- `{entry['id']}` — {entry['name']}" for entry in ordered]


def _taxonomy_section(pages: list[Page], config: BartlebyConfig) -> list[str]:
    """Render taxonomy terms in use, sorted for deterministic output."""
    schema = derive_taxonomies_schema(pages, config)
    taxonomies = schema.to_dict()["taxonomies"]
    assert isinstance(taxonomies, list)
    lines: list[str] = []
    for taxonomy in sorted(taxonomies, key=lambda tax: str(tax["name"])):
        terms = taxonomy["terms"]
        assert isinstance(terms, list)
        names = sorted(str(term["term"]) for term in terms)
        joined = ", ".join(names) if names else "(none)"
        lines.append(f"- **{taxonomy['name']}**: {joined}")
    return lines or ["- (none)"]


def _agent_context_section(context: AgentContext) -> list[str]:
    """Render the explicit agent context verbatim when any field is set."""
    if context.voice is None and context.audience is None and not context.constraints:
        return []
    lines = ["", "## Voice and constraints", ""]
    if context.voice is not None:
        lines.append(f"Voice: {context.voice}")
    if context.audience is not None:
        lines.append(f"Audience: {context.audience}")
    if context.constraints:
        lines.append("")
        lines.append("Constraints:")
        lines += [f"- {constraint}" for constraint in context.constraints]
    return lines


def _style_guide_section(style_guide_text: str | None) -> list[str]:
    """Include the style-guide markdown verbatim when provided."""
    if not style_guide_text:
        return []
    return ["", "## Style guide", "", style_guide_text.rstrip()]
