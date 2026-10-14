# ABOUTME: Pins the reference pages under docs/ to the code surfaces they describe.
# Each surface is a pair of sets (found in code, found in docs) that must be equal.

from __future__ import annotations

import argparse
import atexit
import dataclasses
import datetime
import inspect
import json
import re
import shutil
import tempfile
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2
import pytest

import bartleby.config as config_module
import bartleby.themes as themes_package
from bartleby.agent_surface import build_content_index
from bartleby.authors import Author, load_authors
from bartleby.build import build
from bartleby.cli import _build_parser, _global_flags
from bartleby.config import AIConfig, BartlebyConfig, load_config
from bartleby.config_schema import CONFIG_SCHEMA, ConfigField
from bartleby.content import Page, TermLink, discover_content
from bartleby.linting import RULES
from bartleby.listings import generate_listing_pages
from bartleby.llm import generate_jsonld
from bartleby.navigation import NavItem
from bartleby.output import BuildOutput, ServeStartOutput
from bartleby.pagination import PaginatorPage
from bartleby.plugins import KNOWN_EVENTS, BasePlugin
from bartleby.skills import generate_skills
from bartleby.taxonomies import (
    TaxonomyData,
    TaxonomyTerm,
    build_taxonomies,
    generate_taxonomy_pages,
)
from bartleby.templates import BuildInfo, build_page_context, create_jinja_env
from bartleby.theme_loader import (
    MANIFEST_FILENAME,
    TAILWIND_SOURCES,
    THEME_ASSET_DIRS,
    THEME_FEATURES,
    ThemeManifest,
    default_theme,
    flatten_chain,
    load_manifest,
)

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).parent.parent
SAMPLE_SITE = Path(__file__).parent / "fixtures" / "site"
PAGES_DIR = ROOT / "docs" / "content" / "reference" / "pages"
GUIDES_DIR = ROOT / "docs" / "content" / "guides" / "posts"
THEMES_DIR = Path(themes_package.__file__).parent
SOURCE_DIR = Path(config_module.__file__).parent

Surface = tuple[set[str], set[str]]

# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6}) (.+)$", re.MULTILINE)
_TICK_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")


@dataclasses.dataclass(slots=True)
class Table:
    """One Markdown table: its header cells, its body rows, and the prose above it."""

    header: list[str]
    rows: list[list[str]]
    context: str


def _read(page: str) -> str:
    return (PAGES_DIR / page).read_text(encoding="utf-8")


def _sections(text: str) -> dict[str, str]:
    """Map each heading's text to the body that follows it, up to the next heading."""
    matches = list(_HEADING_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(2)] = text[match.end() : end]
    return sections


def _subheadings(text: str, parent: str) -> list[str]:
    """Level-3 headings between the level-2 heading ``parent`` and the next level-2 heading."""
    body = re.split(rf"^## {re.escape(parent)}$", text, maxsplit=1, flags=re.MULTILINE)[1]
    body = re.split(r"^## ", body, maxsplit=1, flags=re.MULTILINE)[0]
    return re.findall(r"^### (.+)$", body, flags=re.MULTILINE)


def _ticks(text: str) -> list[str]:
    return _TICK_RE.findall(text)


def _tables(body: str) -> list[Table]:
    """Parse every pipe table in ``body``, keeping the prose lines that precede each one."""
    tables: list[Table] = []
    context: list[str] = []
    current: Table | None = None
    for line in body.splitlines():
        if not line.startswith("|"):
            current = None
            context.append(line)
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if current is None:
            current = Table(header=cells, rows=[], context="\n".join(context))
            tables.append(current)
            context = []
        elif not set(line) <= set("|- :"):
            current.rows.append(cells)
    return tables


def _table_with_header(body: str, first_cell: str) -> Table:
    matches = [table for table in _tables(body) if table.header[0] == first_cell]
    assert len(matches) == 1, f"expected one table headed {first_cell!r}, found {len(matches)}"
    return matches[0]


def _first_table_with_header(body: str, first_cell: str) -> Table:
    return next(table for table in _tables(body) if table.header[0] == first_cell)


def _first_column_ticks(table: Table) -> set[str]:
    return {name for row in table.rows for name in _ticks(row[0])}


# ---------------------------------------------------------------------------
# Plugin hooks
# ---------------------------------------------------------------------------


def _hook_events() -> Surface:
    docs = {
        heading.strip("`")
        for heading in _sections(_read("plugin-hooks.md"))
        if heading.startswith("`on_")
    }
    return set(KNOWN_EVENTS), docs


def _hook_signatures() -> Surface:
    code = {
        f"{name}({','.join(list(inspect.signature(getattr(BasePlugin, name)).parameters)[1:])})"
        for name in KNOWN_EVENTS
    }
    docs: set[str] = set()
    for match in re.finditer(r"def (on_\w+)\(([^)]*)\)", _read("plugin-hooks.md")):
        names = re.findall(r"\b(\w+)\s*:", match.group(2)) or re.findall(
            r"\b(\w+)\b", match.group(2)
        )
        docs.add(f"{match.group(1)}({','.join(names)})")
    return code, docs


def _hook_pipeline_steps() -> Surface:
    table = _table_with_header(
        _sections(_read("build-pipeline.md"))["Plugin Hook Locations"], "Event"
    )
    # on_serve fires from the dev server, so the build-step table leaves it out by design.
    return set(KNOWN_EVENTS) - {"on_serve"}, _first_column_ticks(table)


def test_base_class_defines_every_known_event() -> None:
    """The BasePlugin methods and KNOWN_EVENTS are the same 16 names."""
    methods = {name for name in vars(BasePlugin) if name.startswith("on_")}
    assert methods == set(KNOWN_EVENTS)


# ---------------------------------------------------------------------------
# bartleby.yml keys
# ---------------------------------------------------------------------------

_NO_DEFAULT = object()
_INTERNAL_FIELDS = {"config_dir", "disabled_plugins"}
# Mapping-valued fields whose accepted keys the dataclass cannot express.
_MAPPING_KEYS = {"theme.color_mode": ("default",)}


def _dataclass_named(annotation: str) -> type | None:
    candidate = vars(config_module).get(annotation)
    return (
        candidate if isinstance(candidate, type) and dataclasses.is_dataclass(candidate) else None
    )


def _dict_item_dataclass(annotation: str) -> type | None:
    match = re.fullmatch(r"dict\[str, (\w+)\]", annotation)
    return _dataclass_named(match.group(1)) if match else None


def _flatten(cls: type, prefix: str, *, drop_name: bool) -> dict[str, object]:
    """Walk a config dataclass into ``{dotted key path: default}``."""
    paths: dict[str, object] = {}
    for field in dataclasses.fields(cls):
        if drop_name and field.name == "name":
            continue
        key = "type" if field.name == "field_type" else field.name
        path = f"{prefix}.{key}" if prefix else key
        annotation = str(field.type)
        nested = _dataclass_named(annotation)
        item = _dict_item_dataclass(annotation)
        if nested is not None:
            paths.update(_flatten(nested, path, drop_name=False))
        elif item is not None:
            paths[path] = _NO_DEFAULT
            paths.update(_flatten(item, f"{path}.<field>", drop_name=False))
        elif path in _MAPPING_KEYS:
            paths.update({f"{path}.{child}": _NO_DEFAULT for child in _MAPPING_KEYS[path]})
        else:
            paths[path] = (
                field.default if field.default is not dataclasses.MISSING else _NO_DEFAULT
            )
    return paths


def _config_code_keys() -> dict[str, object]:
    """Every ``bartleby.yml`` key path the loader accepts, with its dataclass default."""
    top_level = {field.name: field for field in dataclasses.fields(BartlebyConfig)}
    keys: dict[str, object] = {}
    for key in config_module._TOP_LEVEL_KEYS:
        annotation = str(top_level[key].type)
        nested = _dataclass_named(annotation)
        item = _dict_item_dataclass(annotation)
        if nested is not None:
            keys.update(_flatten(nested, key, drop_name=False))
        elif item is not None:
            keys.update(_flatten(item, key, drop_name=True))
        else:
            keys[key] = top_level[key].default
    return keys


def _leaves(keys: set[str]) -> set[str]:
    """Drop container paths such as ``site.feed`` when ``site.feed.limit`` is present."""
    return {key for key in keys if not any(other.startswith(f"{key}.") for other in keys)}


_SCHEMA_BEGIN = "<!-- config-schema:begin -->"
_SCHEMA_END = "<!-- config-schema:end -->"
_SCHEMA_COLUMNS = ("Path", "Type", "Default", "Allowed Values", "Required", "Description")


def _schema_default_cell(field: ConfigField) -> str:
    value = field.default
    if value is None:
        return "none"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, str):
        return f"`{value}`" if value else '`""`'
    if isinstance(value, int):
        return f"`{value}`"
    return f"`{json.dumps(value)}`"


def render_schema_block() -> str:
    """The configuration reference tables, one per top-level key, in CONFIG_SCHEMA order."""
    groups: dict[str, list[ConfigField]] = {}
    for field in CONFIG_SCHEMA:
        groups.setdefault(field.path.split(".")[0], []).append(field)
    lines: list[str] = []
    for section, fields in groups.items():
        lines += [f"### Options for `{section}`", ""]
        lines.append("| " + " | ".join(_SCHEMA_COLUMNS) + " |")
        lines.append("|" + "|".join("---" for _ in _SCHEMA_COLUMNS) + "|")
        for field in fields:
            assert "|" not in field.description, f"{field.path}: a pipe breaks the table row"
            choices = ", ".join(f"`{choice}`" for choice in field.choices or ()) or "any"
            required = "yes" if field.required else "no"
            cells = (
                f"`{field.path}`",
                field.type_name,
                _schema_default_cell(field),
                choices,
                required,
                field.description,
            )
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def _schema_block_in(page: str) -> str:
    """The text between the config-schema markers of ``page``."""
    after_begin = page.split(_SCHEMA_BEGIN, maxsplit=1)[1]
    return after_begin.split(_SCHEMA_END, maxsplit=1)[0].strip("\n")


def _normalized_path(path: str) -> str:
    """Drop the ``<name>`` segment so a schema path lines up with the dataclass walk."""
    return path.replace(".<name>.", ".")


def _config_doc_rows() -> dict[str, str]:
    """Every documented key path, mapped to its Default cell, read from the schema tables."""
    rows: dict[str, str] = {}
    block = _schema_block_in(_read("configuration.md"))
    for table in _tables(block):
        assert tuple(table.header) == _SCHEMA_COLUMNS
        for row in table.rows:
            rows[_normalized_path(row[0].strip("`"))] = row[2]
    return rows


def _config_keys() -> Surface:
    return _leaves(set(_config_code_keys())), _leaves(set(_config_doc_rows()))


def test_configuration_reference_is_the_schema() -> None:
    """The block between the markers is CONFIG_SCHEMA rendered, byte for byte.

    On failure, replace the text between the two markers in configuration.md with
    ``render_schema_block()``.
    """
    assert _schema_block_in(_read("configuration.md")) == render_schema_block()


def test_top_level_keys_are_the_dataclass_fields() -> None:
    """``_TOP_LEVEL_KEYS`` and the public BartlebyConfig fields are the same set."""
    fields = {field.name for field in dataclasses.fields(BartlebyConfig)} - _INTERNAL_FIELDS
    assert fields == set(config_module._TOP_LEVEL_KEYS)


def _format_default(value: object) -> str | None:
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, int):
        return f"`{value}`"
    if isinstance(value, str):
        return f"`{value}`" if value else '`""`'
    return None


def test_documented_defaults_match_the_dataclasses() -> None:
    """A Default cell that states a bool, int, or string default states the real one."""
    docs = _config_doc_rows()
    mismatches: list[str] = []
    for path, default in _config_code_keys().items():
        expected = _format_default(default)
        if expected is None or docs.get(path, "none") == "none":
            continue
        if docs[path] != expected:
            mismatches.append(f"{path}: docs say {docs[path]!r}, code says {expected!r}")
    assert not mismatches


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _leaf_parsers(
    parser: argparse.ArgumentParser, prefix: str = ""
) -> dict[str, argparse.ArgumentParser]:
    leaves: dict[str, argparse.ArgumentParser] = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                path = f"{prefix} {name}".strip()
                children = _leaf_parsers(child, path)
                leaves.update(children or {path: child})
    return leaves


def _value_suffix(action: argparse.Action) -> str:
    if action.choices:
        return " {" + ",".join(str(choice) for choice in action.choices) + "}"
    return ""


def _cli_commands() -> Surface:
    code = set(_leaf_parsers(_build_parser()))
    docs = {" ".join(_usage_command(block)) for block in _usage_blocks()}
    return code, docs


def _usage_blocks() -> list[str]:
    """Each ``bartleby ...`` usage line in cli.md, with indented continuation lines joined."""
    blocks: list[str] = []
    for fence in re.findall(r"```\n(.*?)```", _read("cli.md"), flags=re.DOTALL):
        in_usage = False
        for line in fence.splitlines():
            if line.startswith("bartleby "):
                blocks.append(line)
                in_usage = True
            elif line.startswith(" ") and in_usage:
                blocks[-1] += " " + line.strip()
            else:
                in_usage = False
    return blocks


def _usage_command(block: str) -> list[str]:
    words: list[str] = []
    for word in block.split()[1:]:
        if not re.fullmatch(r"[a-z][a-z-]*", word):
            break
        words.append(word)
    return words


def _cli_arguments() -> Surface:
    global_dests = {action.dest for action in _global_flags()._actions}
    code: set[str] = set()
    for command, parser in _leaf_parsers(_build_parser()).items():
        for action in parser._actions:
            if action.dest in global_dests or isinstance(action, argparse._HelpAction):
                continue
            if action.option_strings:
                code.add(f"{command} {action.option_strings[-1]}{_value_suffix(action)}")
            else:
                code.add(f"{command} {action.dest.upper()}")
    docs: set[str] = set()
    for block in _usage_blocks():
        command = " ".join(_usage_command(block))
        rest = block.split(maxsplit=1 + len(command.split()))[-1] if command else block
        for flag, choices in re.findall(r"(--[\w-]+)(?:\s+(\{[^}]*\}))?", rest):
            docs.add(f"{command} {flag}" + (f" {choices}" if choices else ""))
        for positional in re.findall(
            r"(?<![\[\w-])([A-Z]{2,})\b", re.sub(r"\[[^\]]*\]", "", rest)
        ):
            docs.add(f"{command} {positional}")
    return code, docs


def _lint_rules() -> Surface:
    """Each lint rule as ``id|severity|description``; the docs table must match the code."""
    code = {f"{rule.id}|{rule.severity}|{rule.description}" for rule in RULES}
    body = _sections(_read("cli.md"))["`bartleby lint`"]
    docs = {
        f"{row[0].strip('`')}|{row[1]}|{row[2].replace('`', '')}"
        for row in _table_with_header(body, "Rule").rows
    }
    return code, docs


def _cli_global_flags() -> Surface:
    code: set[str] = set()
    for action in _global_flags()._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        flag = action.option_strings[-1]
        if action.choices:
            code.add(f"{flag}{_value_suffix(action)}")
        elif action.nargs == 0:
            code.add(flag)
        else:
            code.add(f"{flag} {action.dest.upper()}")
    body = _sections(_read("cli.md"))["Global Flags"]
    docs = {row[0].strip("`") for row in _table_with_header(body, "Flag").rows}
    return code, docs


def _serve_event_types() -> Surface:
    """Every ``type`` the ``serve --events`` stream prints."""
    server_source = (Path(__file__).parent.parent / "src" / "bartleby" / "server.py").read_text(
        encoding="utf-8"
    )
    code = set(re.findall(r'"type": "(\w+)"', server_source))
    code.add(str(_ready_event()["type"]))
    body = _sections(_read("cli.md"))["The Event Stream"]
    return code, _first_column_ticks(_table_with_header(body, "`type`"))


def _ready_event() -> dict[str, object]:
    build = BuildOutput(pages=1, static_files=1, duration_ms=1, output_dir="site/")
    return ServeStartOutput(url="http://127.0.0.1:8000/", build=build).to_dict()


def _serve_ready_fields() -> Surface:
    """The fields of the ``ready`` event are the ones its row in the event table names."""
    body = _sections(_read("cli.md"))["The Event Stream"]
    row = next(row for row in _table_with_header(body, "`type`").rows if row[0] == "`ready`")
    return set(_ready_event()) - {"type"}, set(_ticks(row[2]))


# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------


def _theme_features() -> Surface:
    themes = _sections(_read("themes.md"))["Features"]
    config = _sections(_read("configuration.md"))["Features"]
    docs = _first_column_ticks(_table_with_header(themes, "Feature"))
    assert docs == _first_column_ticks(_table_with_header(config, "Feature"))
    return set(THEME_FEATURES), docs


def _theme_manifest_keys() -> Surface:
    body = _sections(_read("themes.md"))["Manifest Keys"]
    code = {field.name for field in dataclasses.fields(ThemeManifest)}
    return code, _first_column_ticks(_table_with_header(body, "Key"))


def _theme_layout() -> Surface:
    body = _sections(_read("themes.md"))["Theme Directory Layout"]
    code = {MANIFEST_FILENAME, *(f"{name}/" for name in THEME_ASSET_DIRS), *TAILWIND_SOURCES}
    return code, _first_column_ticks(_table_with_header(body, "Path"))


def _theme_base_blocks() -> Surface:
    template = (THEMES_DIR / "base" / "templates" / "base.html").read_text(encoding="utf-8")
    body = _sections(_read("themes.md"))["Base Blocks"]
    code = set(re.findall(r"{% block (\w+) %}", template))
    return code, _first_column_ticks(_table_with_header(body, "Block"))


_COUNT_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}


def _bundled_themes() -> Surface:
    body = _sections(_read("themes.md"))["Bundled Themes"]
    table = _table_with_header(body, "Name")
    code: set[str] = set()
    docs: set[str] = set()
    for root in sorted(THEMES_DIR.iterdir()):
        if not (root / MANIFEST_FILENAME).is_file():
            continue
        manifest = load_manifest(root)
        features = (
            "none"
            if not manifest.features
            else f"all {_COUNT_WORDS[len(THEME_FEATURES)]}"
            if set(manifest.features) == THEME_FEATURES
            else ", ".join(manifest.features)
        )
        sources = [source for source in TAILWIND_SOURCES if (root / source).is_file()]
        sources_cell = ", ".join(f"`{source}`" for source in sources) or "none"
        extends = f"`{manifest.extends}`" if manifest.extends else "none"
        code.add(f"`{manifest.name}` | {extends} | {features} | {sources_cell}")
    for row in table.rows:
        docs.add(" | ".join(row))
    return code, docs


_THEME_COLUMNS = ("base", "material", "scrivener")


def _theme_token_text(theme: str) -> str:
    root = THEMES_DIR / theme
    files = [root / source for source in TAILWIND_SOURCES] + sorted(root.glob("static/css/*.css"))
    return "\n".join(path.read_text(encoding="utf-8") for path in files if path.is_file())


def _theme_tokens() -> Surface:
    """Per theme, whether each documented token is read (``token:theme:yes`` strings)."""
    body = _sections(_read("themes.md"))["Tokens"]
    table = _table_with_header(body, "Token")
    assert tuple(cell.strip("`") for cell in table.header[1:]) == _THEME_COLUMNS
    docs: set[str] = set()
    code: set[str] = set()
    for row in table.rows:
        token = row[0].strip("`")
        variable = "--bb-" + token.replace(".", "-")
        for theme, cell in zip(_THEME_COLUMNS, row[1:], strict=True):
            docs.add(f"{token}:{theme}:{cell}")
            read = re.search(re.escape(variable) + r"(?![\w-])", _theme_token_text(theme))
            code.add(f"{token}:{theme}:{'yes' if read else 'no'}")
    return code, docs


def _theme_token_names() -> Surface:
    """Every ``--bb-*`` variable a bundled theme reads is a documented token, and the reverse."""
    code: set[str] = set()
    for theme in _THEME_COLUMNS:
        code.update(re.findall(r"--bb-([a-z][\w-]*)", _theme_token_text(theme)))
    themes_doc = _table_with_header(_sections(_read("themes.md"))["Tokens"], "Token")
    config_doc = _table_with_header(_sections(_read("configuration.md"))["Tokens"], "Token")
    themes_names = {name.replace(".", "-") for name in _first_column_ticks(themes_doc)}
    config_names = {name.replace(".", "-") for name in _first_column_ticks(config_doc)}
    assert config_names == themes_names
    return code, themes_names


# ---------------------------------------------------------------------------
# Template context
# ---------------------------------------------------------------------------


def _sample_config() -> BartlebyConfig:
    return load_config(SAMPLE_SITE / "bartleby.yml")


def _blank_page() -> Page:
    return Page(source_path=Path("a.md"), abs_source_path=Path("/a.md"), title="A")


def _context_keys() -> Surface:
    config = _sample_config()
    page = _blank_page()
    context = build_page_context(
        page=page,
        site_config=config.site,
        nav=[],
        all_pages=[page],
        taxonomy_data={},
        config=config,
        build_info=BuildInfo(date=datetime.date(2026, 1, 1), bartleby_version="0"),
        data={},
    )
    body = _read("template-context.md")
    docs = {name for heading in _subheadings(body, "Top-Level Keys") for name in _ticks(heading)}
    return set(context), docs


def _page_attributes() -> Surface:
    properties = {name for name, member in vars(Page).items() if isinstance(member, property)}
    code = {field.name for field in dataclasses.fields(Page)} | properties
    body = _sections(_read("template-context.md"))["`page`"]
    return code, _first_column_ticks(_table_with_header(body, "Attribute"))


def _global_functions() -> Surface:
    env = create_jinja_env(_sample_config(), SAMPLE_SITE, default_theme())
    code = set(env.globals) - set(jinja2.Environment().globals)
    body = _read("template-context.md")
    docs = {
        re.sub(r"\(.*\)", "", name)
        for heading in _subheadings(body, "Global Functions")
        for name in _ticks(heading)
    }
    return code, docs


_NESTED_OBJECTS: dict[str, tuple[type, str]] = {
    "nav item": (NavItem, "`nav`"),
    "author": (Author, "`page`"),
    "term link": (TermLink, "`page`"),
    "taxonomy data": (TaxonomyData, "`taxonomies`"),
    "taxonomy term": (TaxonomyTerm, "`taxonomies`"),
    "paginator page": (PaginatorPage, "Listing Pages"),
    "build info": (BuildInfo, "`build`"),
}


def _nested_object_fields() -> Surface:
    """Each field of an object a template can reach is named in the section that covers it."""
    sections = _sections(_read("template-context.md"))
    code: set[str] = set()
    docs: set[str] = set()
    for label, (cls, heading) in _NESTED_OBJECTS.items():
        body = sections[heading]
        mentioned = set(_ticks(body))
        for field in dataclasses.fields(cls):
            code.add(f"{label}:{field.name}")
            if field.name in mentioned:
                docs.add(f"{label}:{field.name}")
    return code, docs


def _generated_page_keys() -> Surface:
    """The ``custom_metadata`` keys on generated listing and taxonomy pages."""
    config = load_config(SAMPLE_SITE / "bartleby.yml")
    pages, _assets = discover_content(config, SAMPLE_SITE / "content")
    generated = generate_listing_pages(pages, config, SAMPLE_SITE / "content")
    generated += generate_taxonomy_pages(build_taxonomies(pages, config), config)
    code = {key for page in generated for key in page.custom_metadata}
    code.add("paginator")
    body = _read("template-context.md")
    docs = {
        name
        for heading in ("Listing Pages", "Taxonomy Pages")
        for name in _first_column_ticks(_table_with_header(_sections(body)[heading], "Key"))
    }
    return code, docs


# ---------------------------------------------------------------------------
# Agent output formats
# ---------------------------------------------------------------------------


@cache
def _sample_build() -> Path:
    """Build the sample site once into a scratch copy and return its output directory."""
    scratch = Path(tempfile.mkdtemp(prefix="bartleby-docs-reference-"))
    atexit.register(shutil.rmtree, scratch, ignore_errors=True)
    site = scratch / "site-src"
    shutil.copytree(SAMPLE_SITE, site)
    build(site / "bartleby.yml")
    return site / "site"


def _agent_toggles() -> Surface:
    body = _sections(_read("agent-surface.md"))["Files"]
    docs = {
        name.removeprefix("ai.")
        for row in _table_with_header(body, "File").rows
        for name in _ticks(row[1])
    }
    code = {field.name for field in dataclasses.fields(AIConfig) if field.type == "bool"}
    return code, docs


def _agent_files() -> Surface:
    output = _sample_build()
    code = {path.name for path in output.iterdir() if path.suffix in {".txt", ".json"}}
    body = _sections(_read("agent-surface.md"))["Files"]
    docs = {
        name for name in _first_column_ticks(_table_with_header(body, "File")) if "<" not in name
    }
    assert (output / "blog" / "posts" / "first-post" / "index.md").is_file()
    assert any(
        name == "<url>/index.md" for name in _first_column_ticks(_table_with_header(body, "File"))
    )
    return code, docs


def _schema_json_keys() -> Surface:
    schema = json.loads((_sample_build() / "schema.json").read_text(encoding="utf-8"))
    body = _sections(_read("agent-surface.md"))["`schema.json`"]
    code = set(schema)
    return code, _first_column_ticks(_first_table_with_header(body, "Key"))


def _schema_json_nested_keys() -> Surface:
    """Every nested key of ``schema.json`` that is not data is named in the schema section."""
    schema = json.loads((_sample_build() / "schema.json").read_text(encoding="utf-8"))
    body = _sections(_read("agent-surface.md"))["`schema.json`"]
    mentioned = set(_ticks(body))
    nested = {
        *schema["site"],
        *schema["theme"],
        *schema["theme"]["features"],
        *schema["resources"],
        *{key for feed in schema["resources"]["feeds"] for key in feed},
    }
    return nested, nested & mentioned


def _content_index_keys() -> Surface:
    config = _sample_config()
    page = Page(
        source_path=Path("a.md"),
        abs_source_path=Path("/a.md"),
        title="A",
        description="d",
        date=datetime.date(2026, 1, 1),
        author_keys=["mason"],
        content_type_name="blog",
    )
    page.output_url = "/a/"
    entry = build_content_index([page], config)["content"]
    assert isinstance(entry, list)
    code = set(entry[0])
    body = _sections(_read("agent-surface.md"))["`content-index.json`"]
    return code, _first_column_ticks(_table_with_header(body, "Key"))


def _jsonld_types_and_keys() -> Surface:
    site = _sample_config().site
    dated = _blank_page()
    dated.date = datetime.date(2026, 1, 1)
    article = dataclasses.replace(dated, content_type_name="blog")
    listing = dataclasses.replace(dated, source_path=Path("__generated__/listings/blog"))
    code: set[str] = set()
    for page in (dated, article, listing):
        payload = json.loads(generate_jsonld(page, site))
        code.add(f"type:{payload['@type']}")
        code.update(f"key:{key}" for key in payload)
    body = _sections(_read("agent-surface.md"))["JSON-LD"]
    docs = {f"type:{name}" for name in _first_column_ticks(_table_with_header(body, "Type"))}
    docs |= {f"key:{name}" for name in _first_column_ticks(_table_with_header(body, "Key"))}
    return code, docs


def _generated_skill_files() -> Surface:
    config = _sample_config()
    pages, _assets = discover_content(config, SAMPLE_SITE / "content")
    authors = load_authors(SAMPLE_SITE / ".authors.yml")
    skills = generate_skills(pages, config, authors, default_theme())
    body = _sections(_read("agent-surface.md"))["Generated Skills"]
    docs = _first_column_ticks(_table_with_header(body, "File"))
    return {f"{skill.name}.md" for skill in skills}, docs


# ---------------------------------------------------------------------------
# Registry and the one test that walks it
# ---------------------------------------------------------------------------

SURFACES: dict[str, Callable[[], Surface]] = {
    "hook events": _hook_events,
    "hook signatures": _hook_signatures,
    "hook pipeline steps": _hook_pipeline_steps,
    "config keys": _config_keys,
    "cli commands": _cli_commands,
    "cli arguments": _cli_arguments,
    "cli global flags": _cli_global_flags,
    "lint rules": _lint_rules,
    "serve event types": _serve_event_types,
    "serve ready fields": _serve_ready_fields,
    "theme features": _theme_features,
    "theme manifest keys": _theme_manifest_keys,
    "theme directory layout": _theme_layout,
    "theme base blocks": _theme_base_blocks,
    "bundled themes": _bundled_themes,
    "theme token reads": _theme_tokens,
    "theme token names": _theme_token_names,
    "context keys": _context_keys,
    "page attributes": _page_attributes,
    "global functions": _global_functions,
    "nested object fields": _nested_object_fields,
    "generated page keys": _generated_page_keys,
    "agent toggles": _agent_toggles,
    "agent files": _agent_files,
    "schema.json keys": _schema_json_keys,
    "schema.json nested keys": _schema_json_nested_keys,
    "content-index keys": _content_index_keys,
    "json-ld types and keys": _jsonld_types_and_keys,
    "generated skill files": _generated_skill_files,
}


@pytest.mark.parametrize("name", list(SURFACES))
def test_docs_list_exactly_what_the_code_defines(name: str) -> None:
    """Nothing in code is missing from the docs, and nothing in the docs is gone from code."""
    in_code, in_docs = SURFACES[name]()
    assert in_code, f"{name}: the code side is empty, so the test would pass for nothing"
    assert in_code - in_docs == set(), f"{name}: in code, missing from docs"
    assert in_docs - in_code == set(), f"{name}: in docs, missing from code"


# ---------------------------------------------------------------------------
# Prose that quotes a number the code can change
# ---------------------------------------------------------------------------

_MODULE_COUNT_CLAIMS = {
    ROOT / "README.md": re.compile(r"Bartleby is (\d+) source modules"),
    ROOT / "CLAUDE.md": re.compile(r"Bartleby is (\d+) single-responsibility modules"),
    ROOT / "spec.md": re.compile(r"The implementation is (\d+) single-responsibility modules"),
}


def _source_modules() -> set[str]:
    """Every module file under ``src/bartleby/`` except the package and entry-point files."""
    return {path.name for path in SOURCE_DIR.glob("*.py") if not path.name.startswith("__")}


def test_readme_architecture_names_every_module() -> None:
    """The README's Architecture list names each module file, and no file that is gone."""
    body = _sections((ROOT / "README.md").read_text(encoding="utf-8"))["Architecture"]
    in_docs = {tick for tick in _ticks(body) if tick.endswith(".py")}
    in_code = _source_modules()
    assert in_code - in_docs == set(), "modules missing from the README Architecture list"
    assert in_docs - in_code == set(), "README names modules that do not exist"


@pytest.mark.parametrize("path", list(_MODULE_COUNT_CLAIMS), ids=lambda path: path.name)
def test_module_count_claims_match_the_source_tree(path: Path) -> None:
    """Each prose file that states the module count states the real one."""
    match = _MODULE_COUNT_CLAIMS[path].search(path.read_text(encoding="utf-8"))
    assert match is not None, f"{path.name} no longer states the module count"
    assert int(match.group(1)) == len(_source_modules())


_EJECT_COUNT_RE = re.compile(r"Ejected theme 'scrivener' \((\d+) files\)")


@pytest.mark.parametrize(
    "page",
    [PAGES_DIR / "themes.md", GUIDES_DIR / "choose-and-customize-a-theme.md"],
    ids=lambda page: page.name,
)
def test_docs_quote_the_real_eject_file_count(page: Path, tmp_path: Path) -> None:
    """The eject output the docs quote carries the file count a fresh eject reports."""
    ejected = flatten_chain(default_theme(), tmp_path / "ejected", project_dir=tmp_path)
    quoted = {int(count) for count in _EJECT_COUNT_RE.findall(page.read_text(encoding="utf-8"))}
    assert quoted, f"{page.name} no longer quotes the eject line"
    assert quoted == {len(ejected.files)}
