# ABOUTME: Deterministic agent-skill generation: bartleby-write, bartleby-review, bartleby-ops.
# Renders skills filled with the site's actual shape (no NLP, no LLM, no network).

"""Agent-skill generation.

The determinism and fidelity contract:

* Determinism. The same site yields byte-identical skills.
  Every list is sorted (content types, authors by id, taxonomies and terms by name,
  shortcodes, feature names), except fields, which keep their order in ``bartleby.yml``.
  Nothing reads the clock, the environment, or the network, and nothing depends on the
  order pages or authors were discovered in.
  The only free text is what the site owner wrote: ``ai.agent_context`` and the style guide,
  both included verbatim.
* Fidelity. Every fact is read from the same derivations the build uses, never recomputed.
  Content types, fields, choices, authors, and taxonomy terms come from
  :mod:`bartleby.schema_introspection`, the source of ``schema.json``.
  The active theme and its feature lists come from
  :func:`bartleby.agent_surface.build_theme_block`, the ``theme`` object of ``schema.json``.
  Published pages only: drafts contribute no terms and no example paths.
* Commands are real. Each ``bartleby`` command in a skill parses against the CLI, with flags
  that exist today, and uses values from the site (a real content type, a real page path)
  instead of stand-ins.
* No placeholders. Output carries no TODO or sample text and no em or en dashes.
  A section with nothing to say says ``none``.
* No content analysis (deferred): the skills describe the site's shape, not its prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bartleby.agent_surface import build_theme_block
from bartleby.content import STANDARD_FRONT_MATTER_FIELDS
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
    from bartleby.theme_loader import ResolvedTheme


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
    theme: ResolvedTheme,
    *,
    shortcodes: list[str] | None = None,
    style_guide_text: str | None = None,
) -> list[GeneratedSkill]:
    """Generate the three agent skills from the site's shape, deterministically.

    See the module docstring for the determinism and fidelity contract.

    :param pages: Discovered content pages (drafts are filtered out).
    :param config: The loaded site configuration.
    :param authors: The authors mapping.
    :param theme: The resolved theme chain the build renders with.
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
        GeneratedSkill(name="bartleby-ops", content=_ops_skill(published, config, theme)),
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
        "Every page also accepts one key per taxonomy, plus these built-in front matter fields.",
        "",
        "Built-in front matter fields:",
    ]
    lines += [
        f"- `{name}`: {STANDARD_FRONT_MATTER_FIELDS[name]}"
        for name in sorted(STANDARD_FRONT_MATTER_FIELDS)
    ]
    lines.append("")
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
    lines += ["", "## Creating a post", "", "```bash"]
    lines += [
        f'bartleby new post "Title" --type {type_name} --output json'
        for type_name in sorted(config.content_types)
    ]
    lines += ["```"]
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
        "bartleby lint --output json",
        "```",
    ]
    return "\n".join(lines) + "\n"


def _ops_skill(pages: list[Page], config: BartlebyConfig, theme: ResolvedTheme) -> str:
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
        "bartleby build --strict --output json",
        "bartleby validate --output json",
        "bartleby serve",
        "```",
        "",
        "`--strict` fails the build on cross-reference and validation errors.",
        "`serve` runs until stopped, and `serve --events` prints one JSON event per line.",
        "`--quiet` and `--verbose` work on every command.",
        "",
        "## Discover existing content",
        "",
        "```bash",
        "bartleby content list --output json",
    ]
    if pages:
        first_path = min(page.source_path.as_posix() for page in pages)
        lines.append(f"bartleby content get {first_path} --output json")
    lines += ["```", "", "## Schema introspection", "", "```bash"]
    lines += [
        f"bartleby schema {type_name} --output json" for type_name in sorted(config.content_types)
    ]
    lines += [
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
    lines += _theme_section(build_theme_block(config, theme))
    lines += [
        "",
        "## Regenerating these skills",
        "",
        "```bash",
        "bartleby generate-skill",
        "```",
        "",
        "Set `ai.skills.regenerate_on_build: true` in `bartleby.yml` "
        "to rewrite them on every build.",
    ]
    return "\n".join(lines) + "\n"


def _theme_section(theme_block: dict[str, object]) -> list[str]:
    """Render the active theme, its feature split, and the theme commands."""
    name = str(theme_block["name"])
    chain = _strings(theme_block["chain"])
    features = theme_block["features"]
    assert isinstance(features, dict)
    enabled = _strings(features["enabled"])
    implemented = _strings(features["implemented"])
    return [
        "",
        "## Theme",
        "",
        f"Active theme: `{name}` (chain, leaf first: {', '.join(chain)}).",
        f"Active features: {_joined(_strings(features['active']))}.",
        "Enabled but not implemented by this theme: "
        f"{_joined(sorted(set(enabled) - set(implemented)))}.",
        f"Implemented but not enabled: {_joined(sorted(set(implemented) - set(enabled)))}.",
        "Features are listed under `theme.features` in `bartleby.yml`.",
        "",
        "- `bartleby theme inspect --output json` lists every theme file "
        "with the layer that provides it.",
        f"- `bartleby theme eject` copies the active theme, flattened, into `themes/{name}`; "
        "`--to DIR` picks another destination and `--force` overwrites existing files.",
        "- `bartleby theme compile` recompiles the theme CSS including project overrides; "
        "`--refresh` forces a fresh download of the Tailwind binary.",
    ]


def _strings(value: object) -> list[str]:
    """Narrow a JSON-shaped value to a list of strings."""
    assert isinstance(value, list)
    return [str(item) for item in value]


def _joined(names: list[str]) -> str:
    """Comma-join names, or ``none`` when there are none."""
    return ", ".join(names) if names else "none"


def _content_type_section(config: BartlebyConfig) -> list[str]:
    """Render each content type's required/optional fields, sorted by name."""
    lines: list[str] = []
    for type_name in sorted(config.content_types):
        schema = derive_content_type_schema(type_name, config)
        lines.append(f"### {type_name}")
        lines.append("")
        lines.append(f"Source directory: `content/{schema.path}/`")
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
    """Render a field list as markdown bullets, or a ``none`` line."""
    if not fields:
        return ["- none"]
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
        return ["- none"]
    ordered = sorted(entries, key=lambda entry: str(entry["id"]))
    return [f"- `{entry['id']}`: {entry['name']}" for entry in ordered]


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
        joined = ", ".join(names) if names else "none"
        lines.append(f"- **{taxonomy['name']}**: {joined}")
    return lines or ["- none"]


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
