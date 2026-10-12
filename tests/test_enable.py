# ABOUTME: Tests for `bartleby enable`/`disable` and the build skipping disabled content types.
# Covers the blog shape block, idempotency, comment preservation, and the on/off build outputs.

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pytest
import yaml

from bartleby.build import build
from bartleby.cli import main
from bartleby.config import load_config

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE = """\
# The site block.
site:
  title: Sample  # inline note
  url: https://example.com

# Pages of the home site.
nav:
  - Home: index.md
"""

POST = """\
---
title: "{title}"
date: 2026-03-01
description: "A post."
---

Body text.
"""


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tmp_path project with a home page and the sample config; the cwd is moved into it."""
    (tmp_path / "bartleby.yml").write_text(SAMPLE, encoding="utf-8")
    content = tmp_path / "content"
    content.mkdir()
    (content / "index.md").write_text(POST.format(title="Home"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _config_file(project: Path) -> str:
    return (project / "bartleby.yml").read_text(encoding="utf-8")


def _tutorials_block(project: Path) -> dict[str, object]:
    parsed = yaml.safe_load(_config_file(project))
    block: dict[str, object] = parsed["content_types"]["tutorials"]
    return block


def _add_post(project: Path, relative: str, title: str) -> None:
    post = project / "content" / relative
    post.parent.mkdir(parents=True, exist_ok=True)
    post.write_text(POST.format(title=title), encoding="utf-8")


class TestEnable:
    def test_adds_a_blog_shaped_instance_with_feeds(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])

        block = _tutorials_block(project)
        assert block["path"] == "tutorials/posts"
        assert block["feeds"] == ["rss", "atom"]
        assert block["readtime"] is True
        assert block["taxonomies"] == ["tags"]
        assert block["excerpt_separator"] == "<!-- more -->"
        assert load_config(project / "bartleby.yml").content_types["tutorials"].enabled is True

    def test_adds_the_taxonomy_the_shape_references(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])

        parsed = yaml.safe_load(_config_file(project))
        assert parsed["taxonomies"]["tags"] == {"slug_format": "{slug}"}

    def test_keeps_a_taxonomy_the_site_already_declares(self, project: Path) -> None:
        main(["config", "set", "taxonomies.tags.slug_format", "tag-{slug}"])

        main(["enable", "blog", "tutorials"])

        parsed = yaml.safe_load(_config_file(project))
        assert parsed["taxonomies"]["tags"] == {"slug_format": "tag-{slug}"}

    def test_second_run_changes_nothing_and_says_so(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["enable", "blog", "tutorials"])
        first = _config_file(project)
        capsys.readouterr()

        main(["enable", "blog", "tutorials"])

        assert _config_file(project) == first
        assert "already" in capsys.readouterr().out

    def test_does_not_clobber_an_existing_instance(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])
        main(["config", "set", "content_types.tutorials.readtime", "false"])

        main(["enable", "blog", "tutorials"])

        assert _tutorials_block(project)["readtime"] is False

    def test_enables_the_same_shape_more_than_once(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])
        main(["enable", "blog", "speaking"])

        types = load_config(project / "bartleby.yml").content_types
        assert {"tutorials", "speaking"} <= set(types)
        assert types["speaking"].path == "speaking/posts"

    def test_preserves_existing_comments(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])

        text = _config_file(project)
        assert "# The site block." in text
        assert "# inline note" in text
        assert "# Pages of the home site." in text

    def test_keeps_the_comment_above_the_key_after_content_types(self, project: Path) -> None:
        (project / "bartleby.yml").write_text(
            SAMPLE
            + "\ncontent_types:\n  notes:\n    path: notes\n"
            + "\n# Tax comment.\ntaxonomies:\n  tags:\n    slug_format: '{slug}'\n",
            encoding="utf-8",
        )

        main(["enable", "blog", "tutorials"])

        lines = _config_file(project).splitlines()
        comment_index = lines.index("# Tax comment.")
        assert lines[comment_index + 1] == "taxonomies:"
        assert lines[comment_index - 1] == ""
        block = lines[lines.index("  tutorials:") : comment_index]
        assert not any(line.lstrip().startswith("#") for line in block)

    def test_json_output_reports_the_change(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["enable", "blog", "tutorials", "--output", "json"])

        payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert payload["status"] == "success"
        assert payload["name"] == "tutorials"
        assert payload["enabled"] is True
        assert payload["changed"] is True

    def test_unknown_shape_exits_non_zero_naming_the_known_shapes(self, project: Path) -> None:
        before = _config_file(project)

        with pytest.raises(SystemExit) as raised:
            main(["enable", "podcast", "shows"])

        assert raised.value.code != 0
        assert _config_file(project) == before

    def test_unknown_shape_message_names_the_known_shapes(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            main(["enable", "podcast", "shows"])

        error = capsys.readouterr().err
        assert "podcast" in error
        assert "blog" in error

    def test_rejects_an_instance_name_that_is_not_a_plain_name(self, project: Path) -> None:
        before = _config_file(project)

        with pytest.raises(SystemExit) as raised:
            main(["enable", "blog", "a.b"])

        assert raised.value.code != 0
        assert _config_file(project) == before


class TestDisable:
    def test_sets_enabled_false_and_keeps_the_block(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])

        main(["disable", "blog", "tutorials"])

        block = _tutorials_block(project)
        assert block["enabled"] is False
        assert block["path"] == "tutorials/posts"
        assert block["feeds"] == ["rss", "atom"]
        assert load_config(project / "bartleby.yml").content_types["tutorials"].enabled is False

    def test_enable_after_disable_flips_it_back_and_keeps_customizations(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["enable", "blog", "tutorials"])
        main(["config", "set", "content_types.tutorials.excerpt_separator", "<!-- cut -->"])
        main(["config", "set", "taxonomies.series.slug_format", "{slug}"])
        main(["config", "set", "content_types.tutorials.taxonomies", "[tags, series]"])
        main(["disable", "blog", "tutorials"])
        capsys.readouterr()

        main(["enable", "blog", "tutorials", "--output", "json"])

        payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert payload["enabled"] is True
        assert payload["changed"] is True
        block = _tutorials_block(project)
        assert block["enabled"] is True
        assert block["excerpt_separator"] == "<!-- cut -->"
        assert block["taxonomies"] == ["tags", "series"]
        assert block["path"] == "tutorials/posts"

    def test_enable_on_an_enabled_instance_after_a_flip_is_a_no_op(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])
        main(["disable", "blog", "tutorials"])
        main(["enable", "blog", "tutorials"])
        first = _config_file(project)

        main(["enable", "blog", "tutorials"])

        assert _config_file(project) == first

    def test_second_run_changes_nothing(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])
        main(["disable", "blog", "tutorials"])
        first = _config_file(project)

        main(["disable", "blog", "tutorials"])

        assert _config_file(project) == first

    def test_absent_instance_exits_non_zero_naming_it(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        before = _config_file(project)

        with pytest.raises(SystemExit) as raised:
            main(["disable", "blog", "tutorials"])

        assert raised.value.code != 0
        assert "tutorials" in capsys.readouterr().err
        assert _config_file(project) == before

    def test_unknown_shape_exits_non_zero(self, project: Path) -> None:
        with pytest.raises(SystemExit) as raised:
            main(["disable", "podcast", "shows"])

        assert raised.value.code != 0


class TestRejectedResultLeavesFileUntouched:
    def test_enable_into_an_invalid_config_does_not_write(self, project: Path) -> None:
        """A config that fails validation stops enable before any write."""
        (project / "bartleby.yml").write_text("site:\n  title: T\n", encoding="utf-8")
        before = _config_file(project)

        with pytest.raises(SystemExit):
            main(["enable", "blog", "tutorials"])

        assert _config_file(project) == before


class TestBuild:
    def test_enabled_type_builds_listing_pages_and_feeds(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])
        _add_post(project, "tutorials/posts/intro.md", "Intro Tutorial")

        build(project / "bartleby.yml")

        site = project / "site"
        assert (site / "tutorials" / "index.html").is_file()
        assert (site / "tutorials" / "feed.xml").is_file()
        assert (site / "tutorials" / "atom.xml").is_file()
        assert "Intro Tutorial" in (site / "tutorials" / "feed.xml").read_text(encoding="utf-8")
        assert "Intro Tutorial" in (site / "feed.xml").read_text(encoding="utf-8")
        assert "Intro Tutorial" in (site / "llms.txt").read_text(encoding="utf-8")

    def test_disabled_type_drops_listing_pages_and_feeds(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])
        _add_post(project, "tutorials/posts/intro.md", "Intro Tutorial")
        main(["disable", "blog", "tutorials"])

        build(project / "bartleby.yml")

        site = project / "site"
        assert not (site / "tutorials").exists()
        schema = json.loads((site / "schema.json").read_text(encoding="utf-8"))
        assert "tutorials" not in [entry["name"] for entry in schema["content_types"]]
        assert "Intro Tutorial" not in (site / "feed.xml").read_text(encoding="utf-8")
        assert "Intro Tutorial" not in (site / "llms.txt").read_text(encoding="utf-8")
        assert (site / "index.html").is_file()

    def test_enable_then_disable_then_rebuild_removes_the_outputs(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])
        _add_post(project, "tutorials/posts/intro.md", "Intro Tutorial")
        build(project / "bartleby.yml")
        assert (project / "site" / "tutorials" / "feed.xml").is_file()

        main(["disable", "blog", "tutorials"])
        build(project / "bartleby.yml")

        assert not (project / "site" / "tutorials").exists()

    def test_other_enabled_types_still_build(self, project: Path) -> None:
        main(["enable", "blog", "tutorials"])
        main(["enable", "blog", "speaking"])
        _add_post(project, "tutorials/posts/intro.md", "Intro Tutorial")
        _add_post(project, "speaking/posts/talk.md", "A Talk")
        main(["disable", "blog", "tutorials"])

        build(project / "bartleby.yml")

        site = project / "site"
        assert (site / "speaking" / "feed.xml").is_file()
        assert "A Talk" in (site / "feed.xml").read_text(encoding="utf-8")
        assert not (site / "tutorials").exists()

    def test_nav_entry_for_a_disabled_type_warns_and_builds(
        self, project: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        main(["enable", "blog", "tutorials"])
        main(["config", "set", "nav", "[{Home: index.md}, {Tutorials: tutorials/}]"])
        main(["disable", "blog", "tutorials"])

        with caplog.at_level(logging.WARNING, logger="bartleby"):
            build(project / "bartleby.yml")

        warnings = [record.getMessage() for record in caplog.records]
        assert any("tutorials" in message and "disabled" in message for message in warnings)

    def test_taxonomy_used_only_by_a_disabled_type_yields_no_page_or_sitemap_entry(
        self, project: Path
    ) -> None:
        main(["enable", "blog", "tutorials"])
        main(["config", "set", "taxonomies.series.slug_format", "{slug}"])
        main(["config", "set", "content_types.tutorials.taxonomies", "[series]"])
        main(["disable", "blog", "tutorials"])

        build(project / "bartleby.yml")

        site = project / "site"
        assert not (site / "series").exists()
        assert "/series/" not in (site / "sitemap.xml").read_text(encoding="utf-8")
