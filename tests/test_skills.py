# ABOUTME: Tests for deterministic skill generation (bartleby-write/review/ops).
# Covers the three skills, site shape, determinism, agent_context, and reserved analyze_content.

from __future__ import annotations

import json
import re
import shlex
import shutil
from pathlib import Path

import pytest

from bartleby.authors import Author
from bartleby.build import BuildResult, build
from bartleby.cli import _build_parser
from bartleby.config import (
    AgentContext,
    AIConfig,
    BartlebyConfig,
    ConfigError,
    ContentTypeConfig,
    DevServerConfig,
    MetadataFieldSchema,
    PaginationConfig,
    SiteConfig,
    TaxonomyConfig,
    ThemeConfig,
    load_config,
)
from bartleby.content import STANDARD_FRONT_MATTER_FIELDS, Page, discover_content
from bartleby.skills import GeneratedSkill, generate_skills
from bartleby.theme_loader import ResolvedTheme, ThemeLayer, ThemeManifest


def _config(agent_context: AgentContext | None = None) -> BartlebyConfig:
    """A config with two content types, a required choice field, and one taxonomy."""
    tutorials = ContentTypeConfig(
        name="tutorials",
        path="tutorials/posts",
        url_base="tutorials",
        url_format="{slug}",
        pagination=PaginationConfig(enabled=False, per_page=10),
        taxonomies=["tags"],
        feeds=[],
        readtime=True,
        excerpt_separator=None,
        metadata={
            "difficulty": MetadataFieldSchema(
                field_type="string",
                required=True,
                choices=["beginner", "intermediate", "advanced"],
            ),
        },
    )
    blog = ContentTypeConfig(
        name="blog",
        path="blog/posts",
        url_base="blog",
        url_format="{date:%Y/%m/%d}/{slug}",
        pagination=PaginationConfig(enabled=True, per_page=10),
        taxonomies=["tags"],
        feeds=["rss"],
        readtime=True,
        excerpt_separator=None,
        metadata={},
    )
    ai = AIConfig()
    if agent_context is not None:
        ai.agent_context = agent_context
    return BartlebyConfig(
        site=SiteConfig(title="Test Site", url="https://example.com"),
        nav=None,
        theme=ThemeConfig(features=["search", "nav.tabs", "scroll-spy"]),
        authors_file=".authors.yml",
        content_types={"tutorials": tutorials, "blog": blog},
        taxonomies={"tags": TaxonomyConfig(name="tags", slug_format="{slug}")},
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=ai,
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp/site"),
    )


def _theme() -> ResolvedTheme:
    """A two-layer chain (stub over base); the config below enables one implemented feature."""
    leaf = ThemeManifest(name="stub", extends="base", features=["search"])
    base = ThemeManifest(name="base", features=["nav.tabs", "color-mode.toggle"])
    return ResolvedTheme(
        chain=[
            ThemeLayer(name="stub", root=Path("/themes/stub"), manifest=leaf),
            ThemeLayer(name="base", root=Path("/themes/base"), manifest=base),
        ]
    )


def _authors() -> dict[str, Author]:
    return {
        "mason": Author(key="mason", name="Mason Egger", description="DA", avatar=None, url=None),
    }


def _pages() -> list[Page]:
    return [
        Page(
            source_path=Path("tutorials/posts/intro.md"),
            abs_source_path=Path("/tmp/site/content/tutorials/posts/intro.md"),
            title="Intro Tutorial",
            content_type_name="tutorials",
            taxonomy_values={"tags": ["python", "web"]},
        ),
    ]


def test_generates_three_named_skills() -> None:
    """generate_skills produces exactly the write, review, and ops skills."""
    skills = generate_skills(_pages(), _config(), _authors(), _theme())
    by_name = {skill.name: skill for skill in skills}
    assert set(by_name) == {"bartleby-write", "bartleby-review", "bartleby-ops"}


def test_write_skill_includes_content_types_and_schema() -> None:
    """The write skill names the site's content types and their required fields."""
    skills = generate_skills(_pages(), _config(), _authors(), _theme())
    write = next(skill for skill in skills if skill.name == "bartleby-write")
    assert "tutorials" in write.content
    assert "blog" in write.content
    # The required choice field and its valid choices appear verbatim.
    assert "difficulty" in write.content
    assert "beginner" in write.content
    assert "advanced" in write.content


def test_write_skill_includes_authors_and_taxonomy_terms() -> None:
    """The write skill lists authors and the in-use taxonomy terms."""
    skills = generate_skills(_pages(), _config(), _authors(), _theme())
    write = next(skill for skill in skills if skill.name == "bartleby-write")
    assert "mason" in write.content
    assert "python" in write.content
    assert "web" in write.content


def test_write_skill_includes_shortcodes_when_present() -> None:
    """Available shortcodes are listed in the write skill."""
    skills = generate_skills(
        _pages(), _config(), _authors(), _theme(), shortcodes=["note", "warning"]
    )
    write = next(skill for skill in skills if skill.name == "bartleby-write")
    assert "note" in write.content
    assert "warning" in write.content


def test_ops_skill_includes_cli_invocations() -> None:
    """The ops skill carries build/validate/export CLI commands with --output json."""
    skills = generate_skills(_pages(), _config(), _authors(), _theme())
    ops = next(skill for skill in skills if skill.name == "bartleby-ops")
    assert "bartleby build --output json" in ops.content
    assert "bartleby validate --output json" in ops.content
    assert "bartleby export" in ops.content


def test_skills_are_byte_identical_for_identical_inputs() -> None:
    """Determinism: same config/schema inputs produce byte-identical skill files."""
    first = generate_skills(_pages(), _config(), _authors(), _theme())
    second = generate_skills(_pages(), _config(), _authors(), _theme())
    first_map = {skill.name: skill.content for skill in first}
    second_map = {skill.name: skill.content for skill in second}
    assert first_map == second_map


def test_agent_context_included_verbatim_when_set() -> None:
    """ai.agent_context voice/audience/constraints appear verbatim in the skills."""
    context = AgentContext(
        voice="Technical but approachable. Second person.",
        audience="Python developers with 2+ years experience",
        constraints=["All code examples must be runnable", "Never use 'simply'"],
    )
    skills = generate_skills(_pages(), _config(agent_context=context), _authors(), _theme())
    write = next(skill for skill in skills if skill.name == "bartleby-write")
    assert "Technical but approachable. Second person." in write.content
    assert "Python developers with 2+ years experience" in write.content
    assert "All code examples must be runnable" in write.content
    assert "Never use 'simply'" in write.content


def test_no_agent_context_means_no_voice_section() -> None:
    """When agent_context is unset, the verbatim voice text is absent."""
    skills = generate_skills(_pages(), _config(), _authors(), _theme())
    write = next(skill for skill in skills if skill.name == "bartleby-write")
    assert "Technical but approachable" not in write.content


def test_analyze_content_is_a_not_yet_supported_config_error(tmp_path: Path) -> None:
    """Setting ai.skills.analyze_content is rejected by config validation."""
    config_text = (
        "site:\n"
        '  title: "T"\n'
        '  url: "https://example.com"\n'
        "ai:\n"
        "  skills:\n"
        "    analyze_content: true\n"
    )
    config_path = tmp_path / "bartleby.yml"
    config_path.write_text(config_text, encoding="utf-8")
    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)
    assert "not yet supported" in str(exc_info.value).lower()


def test_skills_config_output_dir_default() -> None:
    """ai.skills.output_dir defaults to .claude/skills."""
    config = _config()
    assert config.ai.skills.output_dir == ".claude/skills"


def _skill(skills: list[GeneratedSkill], name: str) -> str:
    return next(skill.content for skill in skills if skill.name == name)


def _commands(content: str) -> list[str]:
    """Every ``bartleby ...`` line inside a fenced bash block or an inline code span."""
    fenced = re.findall(r"^(bartleby .+)$", content, flags=re.MULTILINE)
    inline = re.findall(r"`(bartleby [^`]+)`", content)
    return fenced + inline


# --- fidelity: the skills state the real site shape --------------------------


def test_skills_are_byte_identical_whatever_the_input_order() -> None:
    """Determinism: reordering pages, authors, and content types changes nothing."""
    config = _config()
    reordered = _config()
    reordered.content_types = dict(reversed(list(config.content_types.items())))
    authors = _authors()
    authors["alan"] = Author(key="alan", name="Alan", description=None, avatar=None, url=None)
    reversed_authors = dict(reversed(list(authors.items())))
    pages = [*_pages(), _pages()[0]]
    pages[1].source_path = Path("tutorials/posts/zeta.md")
    pages[1].taxonomy_values = {"tags": ["zebra", "apple"]}
    first = generate_skills(pages, config, authors, _theme())
    second = generate_skills(list(reversed(pages)), reordered, reversed_authors, _theme())
    assert [(skill.name, skill.content) for skill in first] == [
        (skill.name, skill.content) for skill in second
    ]


def test_write_skill_lists_fields_under_required_and_optional_with_choices() -> None:
    """The required choice field sits under Required, with every choice."""
    write = _skill(generate_skills(_pages(), _config(), _authors(), _theme()), "bartleby-write")
    tutorials = write.split("### tutorials")[1].split("### ")[0]
    required = tutorials.split("Required fields:")[1].split("Optional fields:")[0]
    assert "`difficulty` (string) (choices: beginner, intermediate, advanced)" in required
    blog = write.split("### blog")[1].split("## ")[0]
    assert blog.count("- none") == 2


def test_write_skill_names_the_built_in_front_matter_fields() -> None:
    """The write skill says which fields every page takes beyond the schema."""
    write = _skill(generate_skills(_pages(), _config(), _authors(), _theme()), "bartleby-write")
    section = write.split("Built-in front matter fields:")[1].split("## ")[0]
    listed = re.findall(r"^- `(\w+)`: ", section, flags=re.MULTILINE)
    assert listed == sorted(STANDARD_FRONT_MATTER_FIELDS)
    assert "`slug`" in section
    assert "`url_base`" in section
    for field, meaning in STANDARD_FRONT_MATTER_FIELDS.items():
        assert f"- `{field}`: {meaning}" in section


def test_front_matter_meanings_match_the_docs_reference() -> None:
    """The docs table and the code mapping list the same standard fields."""
    docs = Path(__file__).parent.parent / "docs/content/reference/pages/front-matter-fields.md"
    table = docs.read_text(encoding="utf-8").split("## Standard Fields")[1].split("## ")[0]
    documented = set(re.findall(r"^\| `(\w+)` \|", table, flags=re.MULTILINE))
    assert documented == set(STANDARD_FRONT_MATTER_FIELDS)


def test_write_skill_gives_a_new_post_command_per_real_content_type() -> None:
    """Each content type gets a concrete `new post` command, not a stand-in."""
    write = _skill(generate_skills(_pages(), _config(), _authors(), _theme()), "bartleby-write")
    assert 'bartleby new post "Title" --type blog --output json' in write
    assert 'bartleby new post "Title" --type tutorials --output json' in write
    assert "<content-type>" not in write


def test_review_skill_names_taxonomies_and_types() -> None:
    """The review skill carries the real types, fields, and taxonomy terms."""
    review = _skill(generate_skills(_pages(), _config(), _authors(), _theme()), "bartleby-review")
    assert "### tutorials" in review
    assert "beginner" in review
    assert "**tags**: python, web" in review


def test_ops_skill_states_the_active_theme_and_split_features() -> None:
    """Active features are the enabled-and-implemented ones; the rest are called out."""
    ops = _skill(generate_skills(_pages(), _config(), _authors(), _theme()), "bartleby-ops")
    assert "`stub`" in ops
    assert "stub, base" in ops
    assert "Active features: nav.tabs, search" in ops
    assert "Enabled but not implemented by this theme: scroll-spy" in ops
    assert "Implemented but not enabled: color-mode.toggle" in ops


def test_ops_skill_names_the_theme_commands_with_their_real_flags() -> None:
    """eject, inspect, and compile appear with the flags cli.py defines."""
    ops = _skill(generate_skills(_pages(), _config(), _authors(), _theme()), "bartleby-ops")
    for command in ("bartleby theme inspect", "bartleby theme eject", "bartleby theme compile"):
        assert command in ops
    for flag in ("--to", "--force", "--refresh"):
        assert flag in ops
    assert "themes/stub" in ops


def test_ops_skill_uses_a_real_page_path_and_content_type() -> None:
    """`content get` and `schema` use real values from the site."""
    ops = _skill(generate_skills(_pages(), _config(), _authors(), _theme()), "bartleby-ops")
    assert "bartleby content get tutorials/posts/intro.md --output json" in ops
    assert "bartleby schema blog --output json" in ops
    assert "<" not in ops


def test_every_command_in_every_skill_parses_against_the_real_cli() -> None:
    """A skill never teaches a subcommand or flag the CLI does not have."""
    parser = _build_parser()
    skills = generate_skills(_pages(), _config(), _authors(), _theme())
    seen = 0
    for skill in skills:
        for command in _commands(skill.content):
            parser.parse_args(shlex.split(command)[1:])
            seen += 1
    assert seen > 10


def test_skills_have_no_placeholders_or_dashes() -> None:
    """No stand-in text and no em or en dashes in generated output."""
    skills = generate_skills(_pages(), _config(), _authors(), _theme(), shortcodes=["note"])
    for skill in skills:
        lowered = skill.content.lower()
        for stand_in in ("todo", "lorem", "example.com", "your-", "<content-type>", "<path>"):
            assert stand_in not in lowered, f"{skill.name} contains {stand_in!r}"
        assert "\u2014" not in skill.content
        assert "\u2013" not in skill.content


def test_skills_never_mention_removed_cli_and_config_surface() -> None:
    """Removed flags and keys (Step 20) must not reappear in generated text."""
    skills = generate_skills(_pages(), _config(), _authors(), _theme())
    for skill in skills:
        for removed in ("--dirty", "include_examples", "color_mode", "analyze_content"):
            assert removed not in skill.content


def test_ops_skill_names_how_to_regenerate() -> None:
    """The ops skill says how the skills themselves are regenerated."""
    ops = _skill(generate_skills(_pages(), _config(), _authors(), _theme()), "bartleby-ops")
    assert "bartleby generate-skill" in ops
    assert "ai.skills.regenerate_on_build" in ops


# --- integration: the docs site ----------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def docs_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a copy of the repo's docs site; its schema.json is the fidelity reference."""
    project = tmp_path_factory.mktemp("docs_skills") / "docs"
    shutil.copytree(_REPO_ROOT / "docs", project, ignore=shutil.ignore_patterns("site"))
    assert isinstance(build(project / "bartleby.yml"), BuildResult)
    return project


def _docs_skills(project: Path) -> list[GeneratedSkill]:
    from bartleby.authors import load_authors
    from bartleby.theme_loader import select_theme
    from bartleby.urls import generate_all_urls

    config = load_config(project / "bartleby.yml")
    pages, _assets = discover_content(config, project / "content")
    generate_all_urls(pages, config)
    return generate_skills(
        pages,
        config,
        load_authors(project / config.authors_file),
        select_theme(config.theme, project),
    )


def test_docs_skills_match_the_built_schema_json(docs_site: Path) -> None:
    """Content types, fields, choices, taxonomies, authors, and theme agree with schema.json."""
    schema = json.loads((docs_site / "site" / "schema.json").read_text(encoding="utf-8"))
    skills = _docs_skills(docs_site)
    write = _skill(skills, "bartleby-write")
    ops = _skill(skills, "bartleby-ops")
    for entry in schema["content_types"]:
        block = write.split(f"### {entry['content_type']}\n")[1].split("\n### ")[0]
        block = block.split("\n## ")[0]
        required = block.split("Required fields:")[1].split("Optional fields:")[0]
        optional = block.split("Optional fields:")[1]
        for group, text in (
            (entry["required_fields"], required),
            (entry["optional_fields"], optional),
        ):
            for field in group:
                assert f"`{field['name']}` ({field['type']})" in text
                for choice in field.get("choices", []):
                    assert choice in text
            assert text.count("\n- ") == max(len(group), 1)
    for taxonomy in schema["taxonomies"]:
        for term in taxonomy["terms"]:
            assert term["term"] in write
    for author in schema["authors"]:
        assert f"`{author['id']}`" in write
    assert f"`{schema['theme']['name']}`" in ops
    for feature in schema["theme"]["features"]["active"]:
        assert feature in ops


def test_docs_skills_have_no_placeholders(docs_site: Path) -> None:
    """The docs site's generated skills carry no stand-in text."""
    for skill in _docs_skills(docs_site):
        lowered = skill.content.lower()
        for stand_in in ("todo", "lorem", "example.com", "your-", "<content-type>", "<path>"):
            assert stand_in not in lowered, f"{skill.name} contains {stand_in!r}"
        assert "\u2014" not in skill.content
        assert "\u2013" not in skill.content


def test_docs_skills_commands_parse_and_are_identical_across_runs(docs_site: Path) -> None:
    """Every command parses against the real CLI, and a second run is byte-identical."""
    parser = _build_parser()
    first = _docs_skills(docs_site)
    for skill in first:
        for command in _commands(skill.content):
            parser.parse_args(shlex.split(command)[1:])
    second = _docs_skills(docs_site)
    assert [skill.content for skill in first] == [skill.content for skill in second]
