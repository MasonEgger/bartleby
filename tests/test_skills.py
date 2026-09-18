# ABOUTME: Tests for deterministic skill generation (bartleby-write/review/ops).
# Covers the three skills, site shape, determinism, agent_context, and reserved analyze_content.

from __future__ import annotations

from pathlib import Path

import pytest

from bartleby.authors import Author
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
from bartleby.content import Page
from bartleby.skills import generate_skills


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
        theme=ThemeConfig(),
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
    skills = generate_skills(_pages(), _config(), _authors())
    by_name = {skill.name: skill for skill in skills}
    assert set(by_name) == {"bartleby-write", "bartleby-review", "bartleby-ops"}


def test_write_skill_includes_content_types_and_schema() -> None:
    """The write skill names the site's content types and their required fields."""
    skills = generate_skills(_pages(), _config(), _authors())
    write = next(skill for skill in skills if skill.name == "bartleby-write")
    assert "tutorials" in write.content
    assert "blog" in write.content
    # The required choice field and its valid choices appear verbatim.
    assert "difficulty" in write.content
    assert "beginner" in write.content
    assert "advanced" in write.content


def test_write_skill_includes_authors_and_taxonomy_terms() -> None:
    """The write skill lists authors and the in-use taxonomy terms."""
    skills = generate_skills(_pages(), _config(), _authors())
    write = next(skill for skill in skills if skill.name == "bartleby-write")
    assert "mason" in write.content
    assert "python" in write.content
    assert "web" in write.content


def test_write_skill_includes_shortcodes_when_present() -> None:
    """Available shortcodes are listed in the write skill."""
    skills = generate_skills(_pages(), _config(), _authors(), shortcodes=["note", "warning"])
    write = next(skill for skill in skills if skill.name == "bartleby-write")
    assert "note" in write.content
    assert "warning" in write.content


def test_ops_skill_includes_cli_invocations() -> None:
    """The ops skill carries build/validate/export CLI commands with --output json."""
    skills = generate_skills(_pages(), _config(), _authors())
    ops = next(skill for skill in skills if skill.name == "bartleby-ops")
    assert "bartleby build --output json" in ops.content
    assert "bartleby validate --output json" in ops.content
    assert "bartleby export" in ops.content


def test_skills_are_byte_identical_for_identical_inputs() -> None:
    """Determinism: same config/schema inputs produce byte-identical skill files."""
    first = generate_skills(_pages(), _config(), _authors())
    second = generate_skills(_pages(), _config(), _authors())
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
    skills = generate_skills(_pages(), _config(agent_context=context), _authors())
    write = next(skill for skill in skills if skill.name == "bartleby-write")
    assert "Technical but approachable. Second person." in write.content
    assert "Python developers with 2+ years experience" in write.content
    assert "All code examples must be runnable" in write.content
    assert "Never use 'simply'" in write.content


def test_no_agent_context_means_no_voice_section() -> None:
    """When agent_context is unset, the verbatim voice text is absent."""
    skills = generate_skills(_pages(), _config(), _authors())
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
