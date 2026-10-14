# ABOUTME: Tests for the accessibility rules behind `bartleby lint`.
# ABOUTME: One fixture page per rule proves the id, path, line, and hint; clean pages stay clean.

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bartleby.cli import main
from bartleby.config import load_config
from bartleby.content import Page
from bartleby.linting import RULES, Finding, lint_site
from bartleby.linting_a11y import ACCESSIBILITY_RULES, Rule, lint_accessibility
from bartleby.markdown_pipeline import create_markdown_renderer, render_markdown

if TYPE_CHECKING:
    from collections.abc import Callable

    from bartleby.config import BartlebyConfig

    PageFactory = Callable[[str], Page]

FRONT_MATTER = '---\ntitle: "Fixture"\ndescription: "A fixture page."\n---\n\n'
# The front matter above is five lines, so body line N is file line N + 5.
BODY_OFFSET = 5

FIXTURE_FILE = "docs/fixture.md"
FIXTURE_SITE = Path(__file__).parent / "fixtures" / "site"
REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def config() -> BartlebyConfig:
    return load_config(FIXTURE_SITE / "bartleby.yml")


@pytest.fixture
def page_from(tmp_path: Path, config: BartlebyConfig) -> PageFactory:
    """A factory that writes ``body`` under front matter and renders it through the pipeline."""
    renderer = create_markdown_renderer(config)

    def make(body: str) -> Page:
        path = tmp_path / FIXTURE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(FRONT_MATTER + body, encoding="utf-8")
        page = Page(
            source_path=path.relative_to(tmp_path),
            abs_source_path=path,
            title="Fixture",
            description="A fixture page.",
            raw_content=body,
        )
        page.output_url = "/docs/fixture/"
        page.rendered_content = render_markdown(body, renderer).html
        return page

    return make


def _only(findings: list[Finding], rule: str) -> Finding:
    matching = [finding for finding in findings if finding.rule == rule]
    assert len(matching) == 1, [finding.to_dict() for finding in findings]
    return matching[0]


def _rule(rule_id: str) -> Rule:
    return next(rule for rule in ACCESSIBILITY_RULES if rule.id == rule_id)


class TestRuleTable:
    def test_every_rule_has_a_stable_id_severity_description_and_hint(self) -> None:
        assert {rule.id for rule in ACCESSIBILITY_RULES} == {
            "image-missing-alt",
            "image-alt-is-filename",
            "heading-level-skip",
            "heading-empty",
            "link-empty",
            "link-generic-text",
            "link-raw-url-text",
            "duplicate-id",
            "table-missing-header",
            "iframe-missing-title",
            "emphasis-as-heading",
            "language-invalid",
        }
        for rule in ACCESSIBILITY_RULES:
            assert rule.severity in {"error", "warning"}, rule.id
            assert rule.description.endswith("."), rule.id
            assert rule.hint, rule.id

    def test_the_combined_table_lists_content_rules_then_accessibility_rules(self) -> None:
        ids = [rule.id for rule in RULES]
        assert ids[:4] == [
            "broken-crossref",
            "missing-description",
            "orphaned-page",
            "broken-external",
        ]
        assert ids[4:] == [rule.id for rule in ACCESSIBILITY_RULES]
        assert len(ids) == len(set(ids))

    def test_rules_are_frozen_so_the_table_is_deterministic(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            ACCESSIBILITY_RULES[0].id = "other"  # type: ignore[misc]  # the write is the test


class TestImages:
    def test_image_missing_alt(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from('Intro.\n\n<img src="chart.png">\n')
        finding = _only(lint_accessibility([page], config), "image-missing-alt")
        assert finding.severity == "error"
        assert finding.file == FIXTURE_FILE
        assert finding.line == 3 + BODY_OFFSET
        assert "chart.png" in finding.message
        assert finding.hint == _rule("image-missing-alt").hint

    def test_empty_alt_is_decorative_and_passes(
        self, page_from: PageFactory, config: BartlebyConfig
    ) -> None:
        page = page_from('<img src="rule.png" alt="">\n\n![](divider.png)\n')
        assert lint_accessibility([page], config) == []

    @pytest.mark.parametrize(
        "alt",
        ["chart.png", "chart", "my-photo.JPG", "image", "Screenshot", " picture "],
    )
    def test_image_alt_is_filename(
        self, page_from: PageFactory, config: BartlebyConfig, alt: str
    ) -> None:
        page = page_from(f"![{alt}](chart.png)\n")
        finding = _only(lint_accessibility([page], config), "image-alt-is-filename")
        assert finding.severity == "warning"
        assert finding.line == 1 + BODY_OFFSET
        assert alt.strip() in finding.message
        assert "describe" in finding.hint

    def test_descriptive_alt_passes(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from("![Monthly revenue, rising from March](chart.png)\n")
        assert lint_accessibility([page], config) == []


class TestHeadings:
    def test_heading_level_skip(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from("## Setup\n\nText.\n\n#### Deep Dive\n")
        finding = _only(lint_accessibility([page], config), "heading-level-skip")
        assert finding.severity == "warning"
        assert finding.line == 5 + BODY_OFFSET
        assert "h4" in finding.message and "h2" in finding.message
        assert "Deep Dive" in finding.message

    def test_first_body_heading_is_measured_from_the_page_title(
        self, page_from: PageFactory, config: BartlebyConfig
    ) -> None:
        page = page_from("### Starts Too Deep\n")
        finding = _only(lint_accessibility([page], config), "heading-level-skip")
        assert "h1" in finding.message

    def test_descending_and_stepping_headings_pass(
        self, page_from: PageFactory, config: BartlebyConfig
    ) -> None:
        page = page_from("## A\n\n### B\n\n#### C\n\n## D\n\n### E\n")
        assert lint_accessibility([page], config) == []

    def test_heading_empty(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from("Text.\n\n<h2></h2>\n")
        finding = _only(lint_accessibility([page], config), "heading-empty")
        assert finding.severity == "error"
        assert finding.line == 3 + BODY_OFFSET
        assert "h2" in finding.message


class TestLinks:
    def test_link_empty(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from('See <a href="/docs/"></a> for more.\n')
        finding = _only(lint_accessibility([page], config), "link-empty")
        assert finding.severity == "error"
        assert finding.line == 1 + BODY_OFFSET
        assert "/docs/" in finding.message

    def test_link_with_aria_label_or_image_alt_passes(
        self, page_from: PageFactory, config: BartlebyConfig
    ) -> None:
        page = page_from(
            '<a href="/docs/" aria-label="Documentation"></a>\n\n'
            '<a href="/home/"><img src="logo.svg" alt="Home"></a>\n'
        )
        assert lint_accessibility([page], config) == []

    @pytest.mark.parametrize(
        "text",
        ["here", "Click here", "link", "this", "Read more", "more", "Learn more...", "(here)"],
    )
    def test_link_generic_text(
        self, page_from: PageFactory, config: BartlebyConfig, text: str
    ) -> None:
        page = page_from(f"Docs are [{text}](/docs/).\n")
        finding = _only(lint_accessibility([page], config), "link-generic-text")
        assert finding.severity == "warning"
        assert finding.line == 1 + BODY_OFFSET
        assert text in finding.message

    def test_link_raw_url_text(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        url = "https://example.com/reference/pages/configuration/#site-language"
        page = page_from(f"Read <{url}>.\n")
        finding = _only(lint_accessibility([page], config), "link-raw-url-text")
        assert finding.severity == "warning"
        assert finding.line == 1 + BODY_OFFSET
        assert url in finding.message
        assert "name" in finding.hint

    def test_short_raw_url_passes(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from("Read <https://example.com/>.\n")
        assert lint_accessibility([page], config) == []


class TestStructure:
    def test_duplicate_id(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from('<div id="note">One</div>\n\n<div id="note">Two</div>\n')
        finding = _only(lint_accessibility([page], config), "duplicate-id")
        assert finding.severity == "error"
        assert finding.line == 1 + BODY_OFFSET
        assert "note" in finding.message

    def test_duplicate_heading_anchor_names_the_heading(
        self, page_from: PageFactory, config: BartlebyConfig
    ) -> None:
        page = page_from('## Usage\n\n<h2 id="usage">Usage</h2>\n')
        finding = _only(lint_accessibility([page], config), "duplicate-id")
        assert "Usage" in finding.message
        assert "#usage" in finding.message

    def test_table_missing_header(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from("<table>\n<tr><td>a</td><td>b</td></tr>\n</table>\n")
        finding = _only(lint_accessibility([page], config), "table-missing-header")
        assert finding.severity == "warning"
        assert finding.line == 1 + BODY_OFFSET

    def test_markdown_table_and_th_first_row_pass(
        self, page_from: PageFactory, config: BartlebyConfig
    ) -> None:
        page = page_from(
            "| A | B |\n|---|---|\n| 1 | 2 |\n\n"
            "<table>\n<tr><th>a</th><th>b</th></tr>\n<tr><td>1</td><td>2</td></tr>\n</table>\n"
        )
        assert lint_accessibility([page], config) == []

    def test_iframe_missing_title(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from('<iframe src="https://example.com/embed/1"></iframe>\n')
        finding = _only(lint_accessibility([page], config), "iframe-missing-title")
        assert finding.severity == "error"
        assert finding.line == 1 + BODY_OFFSET
        assert "example.com/embed/1" in finding.message

    def test_markwright_youtube_embed_passes(
        self, page_from: PageFactory, config: BartlebyConfig
    ) -> None:
        page = page_from("[youtube jNQXAC9IVRw]\n")
        assert "<iframe" in page.rendered_content
        assert lint_accessibility([page], config) == []

    def test_emphasis_as_heading(self, page_from: PageFactory, config: BartlebyConfig) -> None:
        page = page_from("Intro.\n\n**Requirements**\n\n- Python 3.14\n- uv\n")
        finding = _only(lint_accessibility([page], config), "emphasis-as-heading")
        assert finding.severity == "warning"
        assert finding.line == 3 + BODY_OFFSET
        assert "Requirements" in finding.message
        assert "heading" in finding.hint

    def test_bold_sentence_and_bold_at_the_end_pass(
        self, page_from: PageFactory, config: BartlebyConfig
    ) -> None:
        long_run = "**" + "x" * 80 + "**"
        page = page_from(
            f"{long_run}\n\n- item\n\n**Note:** this paragraph has more than the run.\n\n"
            "**Last words**\n"
        )
        assert lint_accessibility([page], config) == []


class TestLanguage:
    @pytest.mark.parametrize("language", ["english", "e", "en-", "en_US", "en-toolongsubtag"])
    def test_language_invalid(self, config: BartlebyConfig, language: str) -> None:
        config.site.language = language
        findings = lint_accessibility([], config)
        finding = _only(findings, "language-invalid")
        assert finding.severity == "error"
        assert finding.file == "bartleby.yml"
        assert language in finding.message
        assert "site.language" in finding.message

    @pytest.mark.parametrize("language", ["en", "de-AT", "zh-Hant-TW", "pt-BR", "ast"])
    def test_language_valid(self, config: BartlebyConfig, language: str) -> None:
        config.site.language = language
        assert lint_accessibility([], config) == []


class TestDogfood:
    """The sites Bartleby ships pass its own accessibility rules."""

    @pytest.mark.parametrize("shape", [[], ["--blog"]])
    def test_scaffold_has_no_accessibility_findings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shape: list[str]
    ) -> None:
        main(["new", "site", str(tmp_path / "site"), *shape, "--quiet"])
        monkeypatch.chdir(tmp_path / "site")
        assert _accessibility_findings() == []

    def test_docs_site_has_no_findings_at_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        docs = tmp_path / "docs"
        shutil.copytree(REPO_ROOT / "docs", docs, ignore=shutil.ignore_patterns("site"))
        monkeypatch.chdir(docs)
        assert _all_findings() == []


def _all_findings() -> list[dict[str, object]]:
    """Every issue ``bartleby lint --output json`` reports for the current directory."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.suppress(SystemExit):
        main(["lint", "--output", "json"])
    payload = json.loads(buffer.getvalue().splitlines()[-1])
    issues: list[dict[str, object]] = payload["issues"]
    return issues


def _accessibility_findings() -> list[dict[str, object]]:
    accessibility_ids = {rule.id for rule in ACCESSIBILITY_RULES}
    return [issue for issue in _all_findings() if issue["rule"] in accessibility_ids]


class TestThroughLintSite:
    def test_lint_site_runs_the_accessibility_rules_by_default(
        self, page_from: PageFactory, config: BartlebyConfig, tmp_path: Path
    ) -> None:
        page = page_from('<img src="chart.png">\n')
        findings = lint_site([page], config, tmp_path)
        assert "image-missing-alt" in {finding.rule for finding in findings}

    def test_rules_and_skip_select_which_rules_run(
        self, page_from: PageFactory, config: BartlebyConfig, tmp_path: Path
    ) -> None:
        page = page_from('<img src="chart.png">\n\n[here](/docs/)\n')
        only = lint_site([page], config, tmp_path, rules={"link-generic-text"})
        assert {finding.rule for finding in only} == {"link-generic-text"}
        skipped = lint_site([page], config, tmp_path, skip={"link-generic-text"})
        rules = {finding.rule for finding in skipped}
        assert "image-missing-alt" in rules
        assert "link-generic-text" not in rules

    def test_every_finding_carries_a_hint(
        self, page_from: PageFactory, config: BartlebyConfig, tmp_path: Path
    ) -> None:
        page = page_from('<img src="chart.png">\n\n[gone](missing.md)\n')
        page.description = None
        for finding in lint_site([page], config, tmp_path):
            assert finding.hint, finding.rule
            assert finding.to_dict()["hint"] == finding.hint
