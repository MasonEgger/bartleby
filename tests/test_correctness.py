# ABOUTME: Correctness sweep for first-run claims: highlighted code is styled, docs feeds have
# entries, and bad config values or a read-only output dir fail with labeled errors.

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

from bartleby.build import BuildError, build
from bartleby.cli import main
from bartleby.config import OVERRIDE_SOURCE, ConfigError, load_config
from bartleby.config_schema import CONFIG_SCHEMA, ConfigField
from tests.feed_helpers import atom_entries, rss_entries
from tests.theme_helpers import bundled_theme

if TYPE_CHECKING:
    from collections.abc import Iterator

BASE_CONFIG = """\
site:
  title: Sweep
  url: https://example.com
taxonomies:
  tags: {}
content_types:
  blog:
    path: blog
    taxonomies: [tags]
    feeds: [rss]
    metadata:
      rating:
        type: string
"""

# (dotted path, value text) pairs that must be rejected, grouped by the guard they exercise.
BAD_INTEGERS = [
    ("site.feed.limit", "oops"),
    ("site.feed.limit", "[1]"),
    ("site.feed.limit", "true"),
    ("content_types.blog.pagination.per_page", "abc"),
    ("content_types.blog.pagination.per_page", "true"),
    ("dev_server.port", "abc"),
    ("dev_server.port", "true"),
]
BAD_BOOLEANS = [
    ("site.feed.enabled", "maybe"),
    ("content_types.blog.enabled", "maybe"),
    ("content_types.blog.readtime", "maybe"),
    ("content_types.blog.pagination.enabled", "maybe"),
    ("content_types.blog.metadata.rating.required", "maybe"),
    ("theme.icon_packs.lucide", "maybe"),
    ("ai.llms_txt", "maybe"),
    ("ai.llms_full_txt", "maybe"),
    ("ai.markdown_variants", "maybe"),
    ("ai.agent_surface", "maybe"),
    ("ai.skills.regenerate_on_build", "maybe"),
]
BAD_LISTS = [
    ("theme.features", "bogus"),
    ("theme.features", "3"),
    ("exclude_patterns", "abc"),
    ("plugins", "abc"),
    ("extra_css", "abc"),
    ("extra_js", "abc"),
    ("markdown_extensions", "abc"),
    ("nav", "abc"),
    ("content_types.blog.taxonomies", "tags"),
    ("content_types.blog.feeds", "rss"),
    ("content_types.blog.metadata.rating.choices", "easy"),
    ("site.feed.formats", "rss"),
    ("site.feed.include", "blog"),
    ("ai.robots.disallow", "GPTBot"),
    ("ai.agent_context.constraints", "abc"),
]
BAD_MAPPINGS = [("theme.icon_packs", "x")]
REJECTED = [*BAD_INTEGERS, *BAD_BOOLEANS, *BAD_LISTS, *BAD_MAPPINGS]
# (dotted path, value text) pairs a string key stores as typed, YAML syntax and all.
VERBATIM_STRINGS = [
    ("taxonomies.tags.slug_format", "{slug}"),
    ("taxonomies.tags.slug_format", "[a, b]"),
    ("site.title", "Yes"),
    ("site.description", "Hello: World"),
]


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project holding BASE_CONFIG as ``bartleby.yml``; the cwd is moved into it."""
    (tmp_path / "bartleby.yml").write_text(BASE_CONFIG, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _concrete(schema_path: str) -> str:
    """Fill a schema path's ``<name>`` and ``<field>`` segments with the BASE_CONFIG names."""
    return schema_path.replace("<name>", "blog").replace("<field>", "rating")


class TestSetOverrides:
    @pytest.mark.parametrize(("path", "text"), REJECTED)
    def test_bad_value_is_a_labeled_error_naming_the_key(
        self, project: Path, path: str, text: str
    ) -> None:
        with pytest.raises(ConfigError) as exc_info:
            load_config(project / "bartleby.yml", [f"{path}={text}"])

        error = exc_info.value
        assert error.source == OVERRIDE_SOURCE
        assert error.key_path == path
        assert error.hint
        assert str(error).startswith(f"--set: {path}: ")

    @pytest.mark.parametrize(("path", "text"), REJECTED)
    def test_config_set_rejects_without_writing(
        self, project: Path, capsys: pytest.CaptureFixture[str], path: str, text: str
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["config", "set", path, text])

        assert exc.value.code == 1
        stderr = capsys.readouterr().err
        assert path in stderr
        assert "(fix: " in stderr
        assert "Traceback" not in stderr
        assert (project / "bartleby.yml").read_text(encoding="utf-8") == BASE_CONFIG

    @pytest.mark.parametrize(("path", "text"), BAD_LISTS)
    def test_a_scalar_for_a_list_field_says_a_list_is_expected(
        self, project: Path, path: str, text: str
    ) -> None:
        with pytest.raises(ConfigError) as exc_info:
            load_config(project / "bartleby.yml", [f"{path}={text}"])

        assert exc_info.value.message == "must be a list"


class TestIntegerCoercion:
    @pytest.mark.parametrize(
        ("path", "attribute"),
        [
            ("site.feed.limit", "site.feed.limit"),
            ("content_types.blog.pagination.per_page", "content_types.blog.pagination.per_page"),
            ("dev_server.port", "dev_server.port"),
        ],
    )
    def test_numeric_string_still_coerces(self, project: Path, path: str, attribute: str) -> None:
        loaded = load_config(project / "bartleby.yml", [f'{path}="25"'])

        value: object = loaded
        for segment in attribute.split("."):
            value = (
                value.get(segment) if isinstance(value, dict) else getattr(value, segment, None)
            )
        assert value == 25


class TestSlugFormatIsAString:
    def test_a_pattern_set_from_the_shell_loads_as_a_string(self, project: Path) -> None:
        """A string key takes the text as typed, so the braces need only shell quoting."""
        main(["config", "set", "taxonomies.tags.slug_format", "tag-{slug}"])

        loaded = load_config(project / "bartleby.yml")
        assert loaded.taxonomies["tags"].slug_format == "tag-{slug}"
        assert yaml.safe_load((project / "bartleby.yml").read_text())["taxonomies"]["tags"] == {
            "slug_format": "tag-{slug}"
        }

    @pytest.mark.parametrize(("path", "text"), VERBATIM_STRINGS)
    def test_a_string_override_is_the_text_as_typed(
        self, project: Path, path: str, text: str
    ) -> None:
        loaded = load_config(project / "bartleby.yml", [f"{path}={text}"])

        node: object = loaded
        for segment in path.split("."):
            node = node[segment] if isinstance(node, dict) else getattr(node, segment)
        assert node == text

    def test_the_hint_for_an_unquoted_file_value_shows_both_forms(self, project: Path) -> None:
        """A bare ``{slug}`` in the file is a mapping; the fix shows the file and shell forms."""
        config_path = project / "bartleby.yml"
        config_path.write_text(
            BASE_CONFIG.replace("tags: {}", "tags:\n    slug_format: {slug}"), encoding="utf-8"
        )

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_path)

        hint = exc_info.value.hint or ""
        assert "quote" in hint
        assert 'slug_format: "{slug}"' in hint
        assert "config set taxonomies.<name>.slug_format '{slug}'" in hint


class TestChoices:
    CHOICE_FIELDS = [entry for entry in CONFIG_SCHEMA if entry.choices is not None]

    @pytest.mark.parametrize("entry", CHOICE_FIELDS, ids=[entry.path for entry in CHOICE_FIELDS])
    def test_value_outside_the_schema_choices_is_rejected(
        self, project: Path, entry: ConfigField
    ) -> None:
        path = _concrete(entry.path)
        outside = "not-a-choice"
        assert entry.choices is not None
        assert outside not in entry.choices
        text = f"[{outside}]" if entry.type_name == "list" else outside

        with pytest.raises(ConfigError) as exc_info:
            load_config(project / "bartleby.yml", [f"{path}={text}"])

        assert exc_info.value.key_path == path
        assert exc_info.value.source == OVERRIDE_SOURCE
        assert exc_info.value.hint

    @pytest.mark.parametrize("entry", CHOICE_FIELDS, ids=[entry.path for entry in CHOICE_FIELDS])
    def test_every_schema_choice_is_accepted(self, project: Path, entry: ConfigField) -> None:
        assert entry.choices is not None
        path = _concrete(entry.path)
        for choice in entry.choices:
            text = f"[{choice}]" if entry.type_name == "list" else choice
            load_config(project / "bartleby.yml", [f"{path}={text}"])


class TestReadOnlyOutput:
    @pytest.fixture
    def site(self, tmp_path: Path) -> Iterator[Path]:
        """A copy of the sample site, already built once; permissions are restored at teardown."""
        project = tmp_path / "project"
        shutil.copytree(Path(__file__).parent / "fixtures" / "site", project)
        build(project / "bartleby.yml")
        yield project
        project.chmod(0o755)
        (project / "site").chmod(0o755)

    def test_unwritable_output_dir_is_a_labeled_build_error(self, site: Path) -> None:
        (site / "site").chmod(0o555)

        with pytest.raises(BuildError) as exc_info:
            build(site / "bartleby.yml")

        message = exc_info.value.errors[0].message
        assert exc_info.value.errors[0].file_path == str(site / "site")
        assert "cannot replace" in message
        assert "(fix: " in message
        assert "output_dir" in message

    def test_unwritable_project_dir_is_a_labeled_build_error(self, site: Path) -> None:
        site.chmod(0o555)

        with pytest.raises(BuildError) as exc_info:
            build(site / "bartleby.yml")

        message = exc_info.value.errors[0].message
        assert exc_info.value.errors[0].file_path == str(site)
        assert f"(fix: make {site} writable (chmod u+w)" in message
        assert "output_dir" not in message

    def test_output_dir_on_another_filesystem_is_moved_into_place(
        self, site: Path, tmp_path: Path
    ) -> None:
        shm = Path("/dev/shm")
        if not shm.is_dir() or shm.stat().st_dev == tmp_path.stat().st_dev:
            pytest.skip("no second filesystem: /dev/shm is missing or shares tmp_path's device")
        target = Path(tempfile.mkdtemp(prefix="bartleby-xdev-", dir=shm)) / "site"
        config = site / "bartleby.yml"
        try:
            for _ in range(2):  # the second build replaces the first one's output
                build(config, overrides=[f"output_dir={target}"])
                assert (target / "index.html").is_file()
        finally:
            shutil.rmtree(target.parent, ignore_errors=True)

    def test_cli_reports_it_without_a_traceback(
        self, site: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (site / "site").chmod(0o555)

        with pytest.raises(SystemExit) as exc:
            main(["build", "--config", str(site / "bartleby.yml")])

        assert exc.value.code == 1
        stderr = capsys.readouterr().err
        assert "Traceback" not in stderr
        assert "(fix: " in stderr


THEMES = ("scrivener", "material")

# Token classes the highlight CSS must style: keywords, strings, comments, names, functions,
# builtins, numbers, operators, punctuation, and the namespace, escape, and decorator shapes.
TOKEN_SELECTORS = ("k", "kn", "s", "s1", "s2", "c", "c1", "n", "nf", "nb", "mi", "o", "p", "nd")

PYTHON_BLOCK = """\
---
title: Home
---

```python
import os  # a comment
@decorator
def greet(name: str = "world") -> int:
    return len(f"hi {name}\\n") + 42 if name else None
```
"""


def _compiled_css(theme_name: str) -> str:
    """The theme's compiled main.css exactly as the package ships it."""
    css_path = (
        Path(__file__).parent.parent
        / "src"
        / "bartleby"
        / "themes"
        / theme_name
        / "static"
        / "css"
        / "main.css"
    )
    return css_path.read_text(encoding="utf-8")


def _has_token_rule(css: str, token: str) -> bool:
    """Whether the CSS has a rule whose selector is ``.highlight .<token>``."""
    return re.search(rf"\.highlight \.{token}[,{{]", css) is not None


def _token_classes(html: str) -> set[str]:
    """Every Pygments token class on a span inside a highlighted block, whitespace excluded."""
    classes: set[str] = set()
    for block in re.findall(r'<div class="highlight">.*?</div>', html, re.S):
        for value in re.findall(r'<span class="([^"]+)">', block):
            classes.update(value.split())
    return classes - {"w"}


class TestHighlightedCodeIsStyled:
    @pytest.mark.parametrize("theme_name", THEMES)
    def test_compiled_theme_css_styles_the_token_classes(self, theme_name: str) -> None:
        css = _compiled_css(theme_name)

        missing = [token for token in TOKEN_SELECTORS if not _has_token_rule(css, token)]
        assert missing == []

    @pytest.mark.parametrize("theme_name", THEMES)
    def test_a_built_python_block_carries_classes_the_built_css_styles(
        self, tmp_path: Path, theme_name: str
    ) -> None:
        (tmp_path / "content").mkdir()
        (tmp_path / "content" / "index.md").write_text(PYTHON_BLOCK, encoding="utf-8")
        (tmp_path / "bartleby.yml").write_text(
            "site:\n  title: Code\n  url: https://example.com\n", encoding="utf-8"
        )

        build(tmp_path / "bartleby.yml", theme=bundled_theme(theme_name))

        html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
        css = (tmp_path / "site" / "css" / "main.css").read_text(encoding="utf-8")
        used = _token_classes(html)
        assert {"k", "kn", "nf", "s2", "c1", "nd", "mi", "o", "p"} <= used
        assert sorted(token for token in used if not _has_token_rule(css, token)) == []

    @pytest.mark.parametrize("theme_name", THEMES)
    def test_both_color_modes_define_every_token_color(self, theme_name: str) -> None:
        css = _compiled_css(theme_name)
        prefix = "sc" if theme_name == "scrivener" else "bm"
        light, dark = css.split(":root{", 1)[1], css.split("[data-theme=dark]{", 1)[1]

        for block in (light, dark):
            assert f"--{prefix}-tok-keyword:" in block.split("}", 1)[0]
            assert f"--{prefix}-tok-string:" in block.split("}", 1)[0]


class TestDocsFeedsCarryEntries:
    @pytest.fixture(scope="class")
    def docs_site(self, tmp_path_factory: pytest.TempPathFactory) -> Path:
        """Build a copy of the docs site strictly and return its output directory."""
        docs = tmp_path_factory.mktemp("docs") / "docs"
        shutil.copytree(
            Path(__file__).parent.parent / "docs", docs, ignore=shutil.ignore_patterns("site")
        )
        build(docs / "bartleby.yml", strict=True)
        return docs / "site"

    def test_every_enabled_type_with_feeds_has_entries_in_each_format(
        self, docs_site: Path
    ) -> None:
        config = load_config(docs_site.parent / "bartleby.yml")
        feed_types = {
            name: kind for name, kind in config.enabled_content_types().items() if kind.feeds
        }
        assert feed_types, "the docs enable no feed, so their feed links point at nothing"

        for kind in feed_types.values():
            rss = rss_entries(
                (docs_site / kind.path.split("/")[0] / "feed.xml").read_text(encoding="utf-8")
            )
            atom = atom_entries(
                (docs_site / kind.path.split("/")[0] / "atom.xml").read_text(encoding="utf-8")
            )
            assert rss
            assert rss == atom

    def test_the_aggregate_feed_is_not_empty(self, docs_site: Path) -> None:
        rss = rss_entries((docs_site / "feed.xml").read_text(encoding="utf-8"))
        atom = atom_entries((docs_site / "atom.xml").read_text(encoding="utf-8"))

        assert rss
        assert rss == atom
