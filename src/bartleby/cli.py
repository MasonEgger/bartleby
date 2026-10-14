# ABOUTME: CLI commands using argparse: new, build, validate, serve.
# Top-level entry point for the bartleby executable.

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
import os
import shlex
import shutil
import sys
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

from jinja2 import TemplateNotFound
from slugify import slugify

from bartleby.agent_surface import AgentSurfaceError
from bartleby.authors import AuthorError, load_authors
from bartleby.build import (
    BuildError,
    async_build,
    build_dry_run,
    calculate_readtime,
    format_page_error,
    render_content,
)
from bartleby.config import (
    ConfigError,
    load_config,
    read_config_text,
    validate_config_text,
)
from bartleby.config_edit import append_to_list, render_full_config, set_key, write_config_text
from bartleby.config_schema import CONFIG_SCHEMA, override_value, resolve_parsed_with_sources
from bartleby.content import ContentError, discover_content
from bartleby.content_query import (
    ContentGet,
    ContentList,
    ContentQueryError,
    get_content,
    list_content,
    select_published,
)
from bartleby.content_shapes import CONTENT_SHAPES
from bartleby.crossrefs import resolve_all_crossrefs, resolve_page_crossrefs
from bartleby.errors import format_error
from bartleby.export import export_content
from bartleby.linting import lint_site
from bartleby.markdown_pipeline import create_markdown_renderer, render_markdown
from bartleby.metadata import validate_all_metadata
from bartleby.output import (
    BuildOutput,
    ConfigGetOutput,
    ConfigSchemaOutput,
    ConfigSetOutput,
    ConfigShowOutput,
    ConfigValue,
    ContentTypeToggleOutput,
    DryRunOutput,
    ErrorOutput,
    GenerateSkillOutput,
    LintOutput,
    NewPostOutput,
    NewSiteOutput,
    RawOutput,
    RenderOutput,
    Result,
    ValidateOutput,
    ValidationError,
    Warning,
    render,
)
from bartleby.schema_introspection import (
    SchemaError,
    derive_authors_schema,
    derive_content_type_schema,
    derive_taxonomies_schema,
)
from bartleby.shortcodes import ShortcodeError, process_shortcodes
from bartleby.skills import generate_skills
from bartleby.theme_compile import ThemeCompileError, ThemeCompileResult, compile_theme_css
from bartleby.theme_loader import (
    EjectResult,
    InspectResult,
    ThemeError,
    flatten_chain,
    inspect_chain,
    select_theme,
)
from bartleby.urls import generate_all_urls

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bartleby.config import BartlebyConfig
    from bartleby.content import Page
    from bartleby.content_shapes import ContentShape

# Stable, machine-recognizable error codes per failure type. These strings are
# part of the CLI error contract (text and JSON output) and must not change
# without a versioning bump.
_ERROR_CODES: dict[type[Exception], str] = {
    BuildError: "build_error",
    ConfigError: "config_error",
    AuthorError: "author_error",
    ThemeCompileError: "theme_compile_error",
    ThemeError: "theme_error",
    ContentError: "content_error",
    AgentSurfaceError: "agent_surface_error",
}

# The author-facing error types the CLI reports without a traceback. The dev
# server catches the same tuple so a bad edit mid-serve is reported, not fatal.
LABELED_ERRORS: tuple[type[Exception], ...] = tuple(_ERROR_CODES)


class UsageError(Exception):
    """A non-recoverable usage problem (missing/invalid params, no config).

    Carries a stable error code so the JSON contract is consistent; always
    surfaces as exit code 2.
    """

    def __init__(self, message: str, *, code: str = "usage_error") -> None:
        super().__init__(message)
        self.code = code


def main(argv: list[str] | None = None) -> None:
    """Top-level CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(
        quiet=getattr(args, "quiet", False), verbose=getattr(args, "verbose", False)
    )
    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        raise SystemExit(1)
    fmt: str = getattr(args, "output", "text")
    try:
        result = handler(args)
    except UsageError as exc:
        _emit_error(ErrorOutput(message=str(exc), code=exc.code, usage=True), fmt)
    except LABELED_ERRORS as exc:
        _report_error(exc, fmt)
    else:
        if result is not None:
            _emit_result(result, fmt, quiet=getattr(args, "quiet", False))


# Results that only confirm a command ran. ``--quiet`` drops their text form; every
# other result (a report, a query payload, a failure) is the command's product.
_STATUS_RESULTS = (BuildOutput, NewSiteOutput, NewPostOutput, GenerateSkillOutput)


def _emit_result(result: Result, fmt: str, *, quiet: bool = False) -> None:
    """Print a successful command result in the requested format and exit non-zero on error.

    Successful results print to stdout. A result whose ``exit_code`` is non-zero
    (e.g. a failed validation) still prints, then raises ``SystemExit``. With
    ``quiet``, a text-mode confirmation (:data:`_STATUS_RESULTS`) with exit code 0
    is not printed; JSON output is a machine contract and always prints.
    """
    confirmation_only = (
        quiet and fmt == "text" and result.exit_code == 0 and isinstance(result, _STATUS_RESULTS)
    )
    if not confirmation_only:
        print(render(result, fmt))
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)


def _emit_error(error: ErrorOutput, fmt: str) -> None:
    """Surface an error: JSON object on stdout, or clean text on stderr; then exit."""
    if fmt == "json":
        print(render(error, fmt))
    else:
        print(render(error, fmt), file=sys.stderr)
    raise SystemExit(error.exit_code)


def _configure_logging(*, quiet: bool = False, verbose: bool = False) -> None:
    """Route the ``bartleby`` logger's non-essential output to stderr.

    Build results stay on stdout (printed directly); warnings such as broken
    cross-references go through ``logging`` to stderr. ``--verbose`` or
    ``BARTLEBY_DEBUG`` lowers the threshold to ``DEBUG``; ``--quiet`` raises it to
    ``ERROR`` so only failures reach stderr.

    The handler is attached once; repeat ``main()`` calls (e.g. in tests) do not
    stack duplicate handlers.
    """
    logger = logging.getLogger("bartleby")
    if verbose or os.environ.get("BARTLEBY_DEBUG"):
        level = logging.DEBUG
    elif quiet:
        level = logging.ERROR
    else:
        level = logging.INFO
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)


def _report_error(exc: Exception, fmt: str) -> None:
    """Surface a build/config/author/content failure in the requested format and exit 1.

    Honors ``BARTLEBY_DEBUG``: when set to a truthy value, the exception is
    re-raised so Python prints the full traceback for development. In text mode
    each collected page error prints to stderr; in JSON mode a single error
    object (carrying the first offending file) prints to stdout.

    :param exc: The build/config/author/content failure to surface.
    :param fmt: ``"text"`` or ``"json"``.
    :raises SystemExit: Always, with code 1, in non-debug mode.
    """
    if os.environ.get("BARTLEBY_DEBUG"):
        raise exc
    code = _ERROR_CODES[type(exc)]
    if isinstance(exc, BuildError):
        if fmt == "json":
            first = exc.errors[0]
            error = ErrorOutput(message=first.message, code=code, file=first.file_path)
            print(render(error, fmt))
        else:
            for page_error in exc.errors:
                print(f"error [{code}] {format_page_error(page_error)}", file=sys.stderr)
    elif isinstance(exc, ContentError):
        _emit_error(ErrorOutput(message=str(exc), code=code, file=exc.source_path), fmt)
        return
    else:
        _emit_error(ErrorOutput(message=str(exc), code=code), fmt)
        return
    raise SystemExit(1)


def _global_flags(*, on_subcommand: bool = False) -> argparse.ArgumentParser:
    """A parent parser carrying the global flags shared by every subcommand.

    The top-level parser attaches the copy that holds the real defaults. Each
    subparser attaches a copy with ``on_subcommand`` set, whose defaults are
    ``argparse.SUPPRESS``: the flags then parse after the subcommand name
    (``bartleby build --output json``) without resetting a value given before it
    (``bartleby --output json build``), and a flag given after still wins.
    """
    defaults: dict[str, object] = {
        "output": "text",
        "config": None,
        "quiet": False,
        "verbose": False,
    }
    if on_subcommand:
        defaults = dict.fromkeys(defaults, argparse.SUPPRESS)
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--output",
        choices=("text", "json"),
        default=defaults["output"],
        help="Output format: text (default) or json (machine-readable)",
    )
    parent.add_argument(
        "--config",
        default=defaults["config"],
        help="Path to bartleby.yml (default: ./bartleby.yml)",
    )
    verbosity = parent.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--quiet",
        action="store_true",
        default=defaults["quiet"],
        help="Suppress warnings and success confirmations (errors and data still print)",
    )
    verbosity.add_argument(
        "--verbose",
        action="store_true",
        default=defaults["verbose"],
        help="Log detailed progress to stderr",
    )
    return parent


def _add_set_flag(parser: argparse.ArgumentParser) -> None:
    """Add the repeatable ``--set key.path=value`` config override to ``parser``."""
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY.PATH=VALUE",
        help="Override a config value for this run (typed by the key's schema, repeatable)",
    )


def _add_base_url_flag(parser: argparse.ArgumentParser) -> None:
    """Add ``--base-url``, a one-run override of ``site.url``, to ``parser``."""
    parser.add_argument(
        "--base-url",
        default=None,
        metavar="URL",
        help="Override site.url for this run (canonical and absolute URLs use it)",
    )


def _config_overrides(args: argparse.Namespace) -> list[str]:
    """Return the ``--set`` overrides plus ``--base-url`` as a ``site.url`` override.

    ``--base-url`` is appended last, so it wins over a ``--set site.url=...``.
    """
    overrides: list[str] = list(args.set)
    if args.base_url is not None:
        overrides.append(f"site.url={args.base_url}")
    return overrides


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argparse tree for every ``bartleby`` subcommand."""
    parser = argparse.ArgumentParser(
        prog="bartleby",
        description="Bartleby static site generator",
        parents=[_global_flags()],
    )
    flags = _global_flags(on_subcommand=True)
    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser("new", help="Scaffold sites or content")
    new_sub = new_parser.add_subparsers(dest="new_command")

    new_site = new_sub.add_parser("site", help="Create a new site directory", parents=[flags])
    new_site.add_argument("name", help="Directory name for the new site")
    new_site.add_argument(
        "--full-config",
        action="store_true",
        help="Write a bartleby.yml listing every option with its description as a comment",
    )
    new_site.add_argument(
        "--blog",
        action="store_true",
        help="Also add a blog content type, the tags taxonomy, a nav entry, and a sample post",
    )
    new_site.set_defaults(_handler=_cmd_new_site)

    new_post = new_sub.add_parser("post", help="Create a new content file", parents=[flags])
    new_post.add_argument("title", help="Post title (used as front matter and slug source)")
    new_post.add_argument("--type", default="blog", help="Content type (default: blog)")
    new_post.set_defaults(_handler=_cmd_new_post)

    build_parser = subparsers.add_parser("build", help="Render the site", parents=[flags])
    build_parser.add_argument(
        "--strict", action="store_true", help="Fail on cross-reference and validation errors"
    )
    build_parser.add_argument("--include-drafts", action="store_true", help="Include drafts")
    build_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing to disk",
    )
    _add_set_flag(build_parser)
    _add_base_url_flag(build_parser)
    build_parser.set_defaults(_handler=_cmd_build)

    validate_parser = subparsers.add_parser(
        "validate", help="Validate config + metadata", parents=[flags]
    )
    _add_set_flag(validate_parser)
    _add_base_url_flag(validate_parser)
    validate_parser.set_defaults(_handler=_cmd_validate)

    serve_parser = subparsers.add_parser(
        "serve", help="Run the development server", parents=[flags]
    )
    serve_parser.add_argument("--host", default=None, help="Bind host (default from config)")
    serve_parser.add_argument(
        "--port",
        type=_port_number,
        default=None,
        help="Bind port, 0 to 65535, where 0 picks a free one (default from config)",
    )
    serve_parser.add_argument(
        "--events",
        action="store_true",
        help="Emit structured JSON events (one object per line) for changes and rebuilds",
    )
    _add_set_flag(serve_parser)
    _add_base_url_flag(serve_parser)
    serve_parser.set_defaults(_handler=_cmd_serve)

    schema_parser = subparsers.add_parser(
        "schema",
        help="Introspect content-type, author, and taxonomy schemas for agents",
        parents=[flags],
    )
    schema_parser.add_argument(
        "target",
        help="A content type name, or 'authors', or 'taxonomies'",
    )
    schema_parser.set_defaults(_handler=_cmd_schema)

    content_parser = subparsers.add_parser("content", help="Query site content")
    content_sub = content_parser.add_subparsers(dest="content_command")
    content_list = content_sub.add_parser(
        "list", help="List published content with metadata", parents=[flags]
    )
    content_list.add_argument("--type", default=None, help="Filter by content type")
    content_list.add_argument(
        "--sort",
        default="date",
        choices=["date", "title", "path"],
        help="Sort field (default: date)",
    )
    content_list.add_argument("--limit", type=int, default=None, help="Limit number of results")
    content_list.set_defaults(_handler=_cmd_content_list)

    content_get = content_sub.add_parser(
        "get", help="Get one page's metadata and content", parents=[flags]
    )
    content_get.add_argument("path", help="Source path of the page (as shown in content list)")
    content_get.set_defaults(_handler=_cmd_content_get)

    render_parser = subparsers.add_parser(
        "render", help="Render a single content file for fast feedback", parents=[flags]
    )
    render_parser.add_argument("path", help="Source path of the page to render")
    render_parser.add_argument(
        "--format",
        dest="render_format",
        default="html",
        choices=["html", "markdown", "metadata"],
        help="Render format: html (default), markdown, or metadata",
    )
    render_parser.set_defaults(_handler=_cmd_render)

    lint_parser = subparsers.add_parser(
        "lint", help="Check content quality (links, descriptions, orphans)", parents=[flags]
    )
    lint_parser.add_argument(
        "--check-external",
        action="store_true",
        help="Also verify external URLs (slow, disabled by default)",
    )
    lint_parser.set_defaults(_handler=_cmd_lint)

    export_parser = subparsers.add_parser(
        "export", help="Export site content as JSONL/JSON/CSV", parents=[flags]
    )
    export_parser.add_argument(
        "--format",
        dest="export_format",
        default="jsonl",
        choices=["jsonl", "json", "csv"],
        help="Export format: jsonl (default), json, or csv",
    )
    export_parser.add_argument("--type", default=None, help="Filter by content type")
    export_parser.add_argument(
        "--include-content", action="store_true", help="Include the markdown body"
    )
    export_parser.add_argument(
        "--include-html", action="store_true", help="Include the rendered HTML"
    )
    export_parser.add_argument("--file", default=None, help="Write to this file instead of stdout")
    export_parser.set_defaults(_handler=_cmd_export)

    skill_parser = subparsers.add_parser(
        "generate-skill", help="Generate agent skills from site content", parents=[flags]
    )
    skill_parser.add_argument(
        "--force", action="store_true", help="Overwrite skills even if unchanged"
    )
    skill_parser.set_defaults(_handler=_cmd_generate_skill)

    theme_parser = subparsers.add_parser("theme", help="Theme asset commands")
    theme_sub = theme_parser.add_subparsers(dest="theme_command")
    theme_compile = theme_sub.add_parser(
        "compile", help="Recompile theme CSS including project overrides", parents=[flags]
    )
    theme_compile.add_argument(
        "--refresh", action="store_true", help="Force re-download of the Tailwind binary"
    )
    theme_compile.set_defaults(_handler=_cmd_theme_compile)
    theme_eject = theme_sub.add_parser(
        "eject",
        help="Copy the active theme, flattened, into one editable directory",
        parents=[flags],
    )
    theme_eject.add_argument(
        "--to", help="Destination directory (default: themes/<theme-name> in the project)"
    )
    theme_eject.add_argument(
        "--force", action="store_true", help="Overwrite files in an existing destination"
    )
    theme_eject.set_defaults(_handler=_cmd_theme_eject)
    theme_inspect = theme_sub.add_parser(
        "inspect",
        help="List every theme file with the layer that provides it",
        parents=[flags],
    )
    theme_inspect.set_defaults(_handler=_cmd_theme_inspect)

    config_parser = subparsers.add_parser("config", help="Inspect and edit bartleby.yml")
    config_sub = config_parser.add_subparsers(dest="config_command")
    config_show = config_sub.add_parser(
        "show", help="Print every resolved config value with its source", parents=[flags]
    )
    _add_set_flag(config_show)
    _add_base_url_flag(config_show)
    config_show.set_defaults(_handler=_cmd_config_show)
    config_get = config_sub.add_parser(
        "get", help="Print one resolved config value", parents=[flags]
    )
    config_get.add_argument("key", help="Dotted key path, such as site.title")
    _add_set_flag(config_get)
    _add_base_url_flag(config_get)
    config_get.set_defaults(_handler=_cmd_config_get)
    config_set = config_sub.add_parser(
        "set", help="Validate a value and write it to bartleby.yml", parents=[flags]
    )
    config_set.add_argument("key", help="Dotted key path, such as site.title")
    config_set.add_argument(
        "value", help="New value: text for a string key, YAML otherwise (42 is an integer)"
    )
    config_set.set_defaults(_handler=_cmd_config_set)
    config_schema = config_sub.add_parser(
        "schema", help="List every accepted config key with its type and default", parents=[flags]
    )
    config_schema.set_defaults(_handler=_cmd_config_schema)

    enable_summary = "Add a content type of a given shape to bartleby.yml"
    enable_parser = subparsers.add_parser(
        "enable", help=enable_summary, description=enable_summary, parents=[flags]
    )
    enable_parser.add_argument(
        "shape", choices=sorted(CONTENT_SHAPES), help="The shape of the content type"
    )
    enable_parser.add_argument(
        "name",
        type=_instance_name,
        help="The content type's name, such as tutorials; one shape may be used many times",
    )
    enable_parser.set_defaults(_handler=_cmd_enable)

    disable_summary = "Stop building a content type, keeping its config"
    disable_parser = subparsers.add_parser(
        "disable", help=disable_summary, description=disable_summary, parents=[flags]
    )
    disable_parser.add_argument(
        "name", type=_instance_name, help="The name of a content type in bartleby.yml"
    )
    disable_parser.set_defaults(_handler=_cmd_disable)

    return parser


def _resolve_config_path(args: argparse.Namespace) -> Path:
    """Resolve ``bartleby.yml`` from ``--config`` or the current directory.

    :raises UsageError: When no config file exists at the resolved location.
    """
    config_path = Path(args.config) if args.config else Path.cwd() / "bartleby.yml"
    if not config_path.exists():
        raise UsageError(
            format_error(
                f"no bartleby.yml at {config_path}",
                hint="run from the directory holding bartleby.yml, pass --config PATH, "
                "or create a project with `bartleby new site <name>`",
            ),
            code="usage_error",
        )
    return config_path


def _instance_name(value: str) -> str:
    """Argparse type for a content-type instance name: letters, digits, ``-`` and ``_``."""
    if not value or not value.isascii() or not value.replace("-", "").replace("_", "").isalnum():
        raise argparse.ArgumentTypeError(
            f"invalid content type name {value!r} (use letters, digits, '-' and '_')"
        )
    return value


def _unknown_content_type(name: str, config: BartlebyConfig) -> UsageError:
    """Build the usage error for a ``--type`` that bartleby.yml does not define."""
    defined = ", ".join(config.content_types) or "none defined"
    return UsageError(
        format_error(
            f"unknown content type {name!r}",
            hint=f"use one of the content types in bartleby.yml ({defined})",
        )
    )


# The starter files `new site` copies, laid out as they land in the new project.
# ${name}, ${title} (the name as a quoted YAML scalar), and ${today} are filled in with
# string.Template.
_SCAFFOLD_ROOT = Path(__file__).parent / "scaffold"
# The files `new site --blog` adds on top of the docs-shaped starter.
_SCAFFOLD_BLOG_ROOT = Path(__file__).parent / "scaffold_blog"
# Copied byte for byte: the tour shows `$` math, which string.Template would reject.
_VERBATIM_STARTER_DIRS = (Path("content") / "tour",)


def _copy_starter_tree(root: Path, target: Path, values: dict[str, str]) -> None:
    """Copy every file under ``root`` into ``target``, filling in ``values`` as it goes."""
    for source in root.rglob("*"):
        if source.is_dir():
            continue
        relative = source.relative_to(root)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8")
        if not any(relative.is_relative_to(verbatim) for verbatim in _VERBATIM_STARTER_DIRS):
            text = Template(text).substitute(values)
        destination.write_text(text, encoding="utf-8")


def _merge_content_shape(
    text: str, shape: ContentShape, name: str, config: BartlebyConfig, *, source: Path
) -> str:
    """Return config ``text`` with a content type of ``shape`` named ``name`` merged in.

    Taxonomies the shape refers to are added unless the site already has them. When the
    site has an explicit ``nav`` with no entry for the type, ``- <Title>: <name>/`` is
    appended, so the new listing is reachable; a site without ``nav`` builds its
    navigation from the content tree. The result is not validated or written; the
    caller does both. Shared by ``enable`` and ``new site --blog`` so the two paths
    cannot drift.

    :param text: The current ``bartleby.yml`` text.
    :param shape: The shape to instantiate.
    :param name: The content type's name.
    :param config: ``text`` as loaded, for the taxonomies and nav it already holds.
    :param source: The file ``text`` came from, named in a YAML error.
    """
    edited = set_key(text, f"content_types.{name}", shape.content_type(name), source=source)
    for taxonomy, block in shape.taxonomies.items():
        if taxonomy not in config.taxonomies:
            edited = set_key(edited, f"taxonomies.{taxonomy}", dict(block), source=source)

    target = f"{name}/"
    if config.nav is not None and not _nav_links_to(config.nav, target):
        title = name.replace("-", " ").replace("_", " ").title()
        edited = append_to_list(edited, "nav", {title: target}, source=source)
    return edited


def _nav_links_to(entries: Sequence[object], target: str) -> bool:
    """Whether any entry in a ``nav`` tree, sections included, points at ``target``."""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for value in entry.values():
            if value == target or (isinstance(value, list) and _nav_links_to(value, target)):
                return True
    return False


def _cmd_new_site(args: argparse.Namespace) -> NewSiteOutput:
    """Scaffold a docs-shaped project under ``./{args.name}/`` from the files in ``scaffold/``.

    With ``--full-config`` the complete annotated config replaces the minimal one. With
    ``--blog`` the blog files from ``scaffold_blog/`` are added and the blog block is merged
    into whichever config was written, so the two flags combine.
    """
    name = args.name.rstrip("/") or args.name
    target = Path.cwd() / name
    if target.exists():
        raise UsageError(
            format_error(
                f"{target} already exists", hint="choose another name or delete the directory"
            )
        )

    target.mkdir(parents=True)
    # A JSON string is a valid double-quoted YAML scalar, so a quote or a backslash in
    # the name reaches site.title intact. A failure past this point removes the
    # directory, so a retry does not stop at "already exists".
    values = {
        "name": name,
        "title": json.dumps(name, ensure_ascii=False),
        "today": datetime.date.today().isoformat(),
    }
    try:
        (target / "templates").mkdir()
        (target / "static").mkdir()
        (target / "hooks").mkdir()
        _copy_starter_tree(_SCAFFOLD_ROOT, target, values)
        config_path = target / "bartleby.yml"

        if args.full_config:
            full = render_full_config(CONFIG_SCHEMA, base=read_config_text(config_path))
            write_config_text(config_path, full)

        if args.blog:
            _copy_starter_tree(_SCAFFOLD_BLOG_ROOT, target, values)
            edited = _merge_content_shape(
                read_config_text(config_path),
                CONTENT_SHAPES["blog"],
                "blog",
                load_config(config_path),
                source=config_path,
            )
            validate_config_text(edited, config_path)
            write_config_text(config_path, edited)
    except Exception:
        shutil.rmtree(target)
        raise

    created = sorted(
        f"{entry.name}/" if entry.is_dir() else entry.name for entry in target.iterdir()
    )
    return NewSiteOutput(
        path=f"{name}/",
        config=f"{name}/bartleby.yml",
        created=created,
        next_command=f"cd {shlex.quote(name)} && bartleby serve",
        blog=args.blog,
        full_config=args.full_config,
    )


def _cmd_new_post(args: argparse.Namespace) -> NewPostOutput:
    """Create a new post under ``content/{type}/posts/<slug>.md``."""
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    config = load_config(config_path)
    if args.type not in config.content_types:
        raise _unknown_content_type(args.type, config)
    content_type = config.content_types[args.type]
    if not content_type.enabled:
        raise UsageError(
            format_error(
                f"content type {args.type!r} is disabled, so nothing would build the post",
                hint=f"run bartleby enable blog {args.type}",
            )
        )
    posts_dir = project_dir / "content" / content_type.path
    posts_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(args.title)
    destination = posts_dir / f"{slug}.md"
    if destination.exists():
        raise UsageError(
            format_error(
                f"{destination} already exists", hint="choose a different title or edit that file"
            )
        )
    today = datetime.date.today().isoformat()
    front_matter = (
        f'---\ntitle: "{args.title}"\ndate: {today}\ndraft: true\n---\n\nWrite something here.\n'
    )
    destination.write_text(front_matter, encoding="utf-8")
    return NewPostOutput(path=str(destination))


def _cmd_build(args: argparse.Namespace) -> BuildOutput | DryRunOutput:
    """Run a full site build from ``./bartleby.yml`` via the async pipeline.

    With ``--dry-run`` the build renders into a temp tree, diffs it against the
    existing ``site/``, and reports the change set without writing to disk.
    When ``ai.skills.regenerate_on_build`` is set, a real build also rewrites the
    agent skills (as ``generate-skill`` does); a dry run never does.
    """
    config_path = _resolve_config_path(args)
    if args.dry_run:
        diff = build_dry_run(
            config_path,
            include_drafts=args.include_drafts,
            strict=args.strict,
            overrides=_config_overrides(args),
        )
        return DryRunOutput(
            added=diff.added,
            modified=diff.modified,
            unchanged=len(diff.unchanged),
            deleted=diff.deleted,
        )
    result = asyncio.run(
        async_build(
            config_path,
            include_drafts=args.include_drafts,
            strict=args.strict,
            overrides=_config_overrides(args),
        )
    )
    if result.config.ai.skills.regenerate_on_build:
        _write_skills(config_path, result.config)
    return BuildOutput.from_result(result)


def _cmd_validate(args: argparse.Namespace) -> ValidateOutput:
    """Validate the config and content without running a full build.

    Beyond metadata validation this dry-runs URL generation, checks that every
    page-level ``template:`` override resolves to an existing template, and scans
    rendered HTML for broken cross-references (Design 17).
    """
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    config = load_config(config_path, _config_overrides(args))
    content_dir = project_dir / "content"
    authors = load_authors(config.config_dir / config.authors_file)
    pages, _assets = discover_content(config, content_dir)

    errors: list[ValidationError] = [
        ValidationError(file=error.file_path, line=0, field="", message=error.message, code="E001")
        for error in validate_all_metadata(pages, config, authors)
    ]
    errors += _validate_urls(pages, config)
    errors += _validate_template_overrides(pages, config, project_dir)
    errors += _validate_crossrefs(pages, config, project_dir, content_dir)

    return ValidateOutput(valid=not errors, files_checked=len(pages), errors=errors)


def _validate_urls(pages: list[Page], config: BartlebyConfig) -> list[ValidationError]:
    """Dry-run URL generation, reporting any page whose URL cannot be built."""
    errors: list[ValidationError] = []
    try:
        generate_all_urls(pages, config)
    except ValueError as exc:
        errors.append(ValidationError(file="", line=0, field="url", message=str(exc), code="E002"))
    return errors


def _validate_template_overrides(
    pages: list[Page], config: BartlebyConfig, project_dir: Path
) -> list[ValidationError]:
    """Report pages whose ``template:`` override does not resolve to a real template."""
    from bartleby.templates import create_jinja_env

    env = create_jinja_env(config, project_dir)
    errors: list[ValidationError] = []
    for page in pages:
        if page.template_override is None:
            continue
        try:
            env.get_template(page.template_override)
        except TemplateNotFound:
            errors.append(
                ValidationError(
                    file=str(page.source_path),
                    line=0,
                    field="template",
                    message=f"template override not found: {page.template_override}",
                    code="E003",
                )
            )
    return errors


def _validate_crossrefs(
    pages: list[Page], config: BartlebyConfig, project_dir: Path, content_dir: Path
) -> list[ValidationError]:
    """Render every page and report markdown links that resolve to no page."""
    from bartleby.templates import create_jinja_env

    env = create_jinja_env(config, project_dir)
    md_renderer = create_markdown_renderer(config)
    errors: list[ValidationError] = []
    for page in pages:
        try:
            processed = process_shortcodes(page.raw_content, {"page": page}, env)
        except ShortcodeError:
            continue
        html = render_markdown(processed, md_renderer).html
        _rewritten, crossref_errors = resolve_page_crossrefs(html, page, pages, content_dir)
        errors += [
            ValidationError(
                file=error.source_path,
                line=0,
                field="",
                message=error.message,
                code="E004",
            )
            for error in crossref_errors
        ]
    return errors


def _cmd_schema(args: argparse.Namespace) -> Result:
    """Introspect a schema: ``schema <content-type|authors|taxonomies>``.

    The positional ``target`` selects the schema. ``authors`` and ``taxonomies``
    are reserved names; anything else is treated as a content type name.

    :raises UsageError: When ``target`` names an undefined content type.
    """
    config_path = _resolve_config_path(args)
    config = load_config(config_path)
    target: str = args.target
    if target == "authors":
        authors = load_authors(config.config_dir / config.authors_file)
        return derive_authors_schema(authors)
    if target == "taxonomies":
        pages, _assets = discover_content(config, config.config_dir / "content")
        return derive_taxonomies_schema(pages, config)
    try:
        return derive_content_type_schema(target, config)
    except SchemaError as exc:
        raise UsageError(str(exc)) from exc


def _cmd_content_list(args: argparse.Namespace) -> ContentList:
    """List published content (``content list``) with curated fields."""
    config_path = _resolve_config_path(args)
    config = load_config(config_path)
    pages, _assets = discover_content(config, config.config_dir / "content")
    return list_content(
        pages,
        config,
        content_type=args.type,
        sort=args.sort,
        limit=args.limit,
    )


def _cmd_content_get(args: argparse.Namespace) -> ContentGet:
    """Return one page's metadata and body (``content get <path>``).

    :raises UsageError: When ``path`` names a page that does not exist.
    """
    config_path = _resolve_config_path(args)
    config = load_config(config_path)
    pages, _assets = discover_content(config, config.config_dir / "content")
    try:
        return get_content(args.path, pages, config)
    except ContentQueryError as exc:
        raise UsageError(str(exc)) from exc


def _cmd_render(args: argparse.Namespace) -> RenderOutput:
    """Render one content file without a full build (``render <path>``).

    Resolves shortcodes and cross-references and runs markdown rendering for the
    single page, never touching the ``site/`` output tree. ``--format`` selects
    HTML (default), processed markdown, or just the parsed metadata.

    :raises UsageError: When ``path`` names a page that does not exist.
    """
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    config = load_config(config_path)
    content_dir = project_dir / "content"
    pages, _assets = discover_content(config, content_dir)
    page = _find_page(args.path, pages)
    if page is None:
        raise UsageError(f"no content page at {args.path!r}")

    generate_all_urls(pages, config)
    metadata = _render_metadata(page)
    word_count = len(page.raw_content.split())
    read_time = calculate_readtime(page.raw_content)

    render_format: str = args.render_format
    if render_format == "metadata":
        return RenderOutput(
            path=args.path,
            url=page.output_url,
            metadata=metadata,
            word_count=word_count,
            read_time_minutes=read_time,
        )

    from bartleby.templates import create_jinja_env

    env = create_jinja_env(config, project_dir)
    try:
        processed = process_shortcodes(page.raw_content, {"page": page}, env)
    except ShortcodeError as exc:
        raise UsageError(str(exc)) from exc

    if render_format == "markdown":
        return RenderOutput(
            path=args.path,
            url=page.output_url,
            metadata=metadata,
            word_count=word_count,
            read_time_minutes=read_time,
            markdown=processed,
        )

    md_renderer = create_markdown_renderer(config)
    html = render_markdown(processed, md_renderer).html
    html, crossref_errors = resolve_page_crossrefs(html, page, pages, content_dir)
    warnings = [
        Warning(file=error.source_path, message=error.message, code="broken-crossref")
        for error in crossref_errors
    ]
    return RenderOutput(
        path=args.path,
        url=page.output_url,
        metadata=metadata,
        word_count=word_count,
        read_time_minutes=read_time,
        warnings=warnings,
        html=html,
    )


def _cmd_lint(args: argparse.Namespace) -> LintOutput:
    """Check content quality (``lint``): broken links, missing desc, orphans.

    Renders every published page in-memory (no ``site/`` output) so cross-
    reference and inbound-link analysis has rendered HTML to scan, then runs the
    linting checks. ``--check-external`` opts into (slow) external URL probing.
    """
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    config = load_config(config_path)
    content_dir = project_dir / "content"
    pages, _assets = discover_content(config, content_dir)
    pages = select_published(pages)
    generate_all_urls(pages, config)

    from bartleby.templates import create_jinja_env

    env = create_jinja_env(config, project_dir)
    md_renderer = create_markdown_renderer(config)
    for page in pages:
        try:
            processed = process_shortcodes(page.raw_content, {"page": page}, env)
        except ShortcodeError:
            processed = page.raw_content
        page.rendered_content = render_markdown(processed, md_renderer).html

    # Rewrite .md hrefs to output URLs before linting, mirroring build.py's
    # pipeline, so the orphan pass sees resolved inbound links, not .md targets.
    resolve_all_crossrefs(pages, content_dir)

    findings = lint_site(pages, config, content_dir, check_external=args.check_external)
    issues = [finding.to_dict() for finding in findings]
    errors = sum(1 for finding in findings if finding.severity == "error")
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    info = sum(1 for finding in findings if finding.severity == "info")
    return LintOutput(issues=issues, errors=errors, warnings=warnings, info=info)


def _cmd_export(args: argparse.Namespace) -> RawOutput:
    """Export published content (``export``) as JSONL/JSON/CSV.

    The payload is written to ``--file`` when given (and an empty result is
    returned so nothing is echoed), otherwise it is emitted on stdout verbatim.
    """
    config_path = _resolve_config_path(args)
    if args.include_html:
        # Rendering HTML needs the build's render phase, so the export runs it.
        rendered = render_content(config_path)
        config, pages = rendered.config, rendered.pages
    else:
        config = load_config(config_path)
        pages, _assets = discover_content(config, config.config_dir / "content")
    if args.type is not None and args.type not in config.content_types:
        raise _unknown_content_type(args.type, config)
    payload = export_content(
        pages,
        config,
        fmt=args.export_format,
        content_type=args.type,
        include_content=args.include_content,
        include_html=args.include_html,
    )
    if args.file is not None:
        Path(args.file).write_text(payload + "\n", encoding="utf-8")
        return RawOutput(text=f"wrote {args.file}")
    return RawOutput(text=payload)


def _cmd_generate_skill(args: argparse.Namespace) -> GenerateSkillOutput:
    """Generate the agent skills (``generate-skill``) and write them to disk.

    Skills are rendered deterministically from the site's shape and written to
    ``ai.skills.output_dir``. ``--force`` is accepted for parity with the spec;
    generation is deterministic, so writes are always idempotent.
    """
    config_path = _resolve_config_path(args)
    return _write_skills(config_path, load_config(config_path))


def _write_skills(config_path: Path, config: BartlebyConfig) -> GenerateSkillOutput:
    """Render the agent skills for the site at ``config_path`` and write them to disk."""
    project_dir = config_path.parent
    authors = load_authors(project_dir / config.authors_file)
    pages, _assets = discover_content(config, project_dir / "content")
    generate_all_urls(pages, config)

    shortcodes = _discover_shortcode_names(project_dir)
    style_guide_text = _load_style_guide(project_dir, config.ai.skills.style_guide)
    skills = generate_skills(
        pages,
        config,
        authors,
        select_theme(config.theme, project_dir),
        shortcodes=shortcodes,
        style_guide_text=style_guide_text,
    )

    output_dir = project_dir / config.ai.skills.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[dict[str, object]] = []
    for skill in skills:
        destination = output_dir / skill.filename
        destination.write_text(skill.content, encoding="utf-8")
        generated.append({"type": skill.name.removeprefix("bartleby-"), "path": str(destination)})
    return GenerateSkillOutput(skills_generated=generated, output_dir=config.ai.skills.output_dir)


def _discover_shortcode_names(project_dir: Path) -> list[str]:
    """Return the names of the project's shortcode templates, sorted.

    Scans every location ``shortcode_search_roots`` mirrors from the Jinja
    loader's cascade (``overrides/shortcodes``, ``templates/shortcodes``,
    project root, then the built-in theme) and de-duplicates by stem.
    """
    from bartleby.templates import shortcode_search_roots

    names: set[str] = set()
    for directory in shortcode_search_roots(project_dir):
        if directory.is_dir():
            names.update(path.stem for path in directory.glob("*.html"))
    return sorted(names)


def _load_style_guide(project_dir: Path, style_guide: str | None) -> str | None:
    """Read the configured style-guide markdown, if any.

    :raises UsageError: When ``style_guide`` points to a missing file.
    """
    if style_guide is None:
        return None
    path = project_dir / style_guide
    if not path.exists():
        raise UsageError(
            format_error(
                f"style guide not found at {path}",
                hint="fix ai.skills.style_guide in bartleby.yml, which is relative to the project",
            )
        )
    return path.read_text(encoding="utf-8")


def _find_page(path: str, pages: list[Page]) -> Page | None:
    """Return the page whose source path matches ``path`` (content-relative ok)."""
    from bartleby.content_query import normalise_source_path

    target = normalise_source_path(path)
    for page in pages:
        if normalise_source_path(page.source_path.as_posix()) == target:
            return page
    return None


def _render_metadata(page: Page) -> dict[str, object]:
    """Build the metadata map for a single rendered page."""
    metadata: dict[str, object] = {"title": page.title}
    if page.date is not None:
        metadata["date"] = page.date.isoformat()
    if page.description is not None:
        metadata["description"] = page.description
    if page.author_keys:
        metadata["authors"] = list(page.author_keys)
    return metadata


def _cmd_theme_compile(args: argparse.Namespace) -> ThemeCompileResult:
    """Recompile the theme CSS including project overrides via the Tailwind CLI."""
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    config = load_config(config_path)
    theme = select_theme(config.theme, project_dir)
    return compile_theme_css(project_dir, theme, config.theme.tokens, refresh=args.refresh)


def _cmd_theme_eject(args: argparse.Namespace) -> EjectResult:
    """Flatten the active theme chain into one directory a person or agent can read."""
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    config = load_config(config_path)
    theme = select_theme(config.theme, project_dir)
    if args.to:
        destination = Path(args.to)
        if not destination.is_absolute():
            destination = project_dir / destination
    else:
        destination = project_dir / "themes" / theme.chain[0].name
    return flatten_chain(theme, destination, project_dir=project_dir, force=args.force)


def _cmd_theme_inspect(args: argparse.Namespace) -> InspectResult:
    """List each theme file, its providing layer, and any project overrides/ shadowing."""
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    config = load_config(config_path)
    theme = select_theme(config.theme, project_dir)
    return inspect_chain(theme, project_dir)


def _cmd_config_show(args: argparse.Namespace) -> ConfigShowOutput:
    """Print the resolved config, each value tagged ``default``, ``file``, or ``--set``.

    Values are the parsed ones the build uses, not the raw YAML text, so a quoted
    ``"25"`` for an integer key shows as ``25``.
    """
    resolved = resolve_parsed_with_sources(_resolve_config_path(args), _config_overrides(args))
    return ConfigShowOutput(
        [ConfigValue(path, value, source) for path, (value, source) in resolved.items()]
    )


def _cmd_config_get(args: argparse.Namespace) -> ConfigGetOutput:
    """Print one resolved value: a string bare, anything else as JSON.

    :raises UsageError: When ``key`` is not a resolved leaf; the hint points at ``config show``.
    """
    resolved = resolve_parsed_with_sources(_resolve_config_path(args), _config_overrides(args))
    if args.key not in resolved:
        raise UsageError(
            format_error(
                f"no config value at {args.key!r}",
                key_path=args.key,
                hint="run `bartleby config show` for every value, or "
                "`bartleby config schema` for every accepted key",
            )
        )
    value, source = resolved[args.key]
    return ConfigGetOutput(args.key, value, source)


def _cmd_config_set(args: argparse.Namespace) -> ConfigSetOutput:
    """Write one value into ``bartleby.yml``, keeping its comments, after validating it.

    The key must be one the schema knows, and the value is typed by it: text for a
    string key, YAML for the rest. The edited text is validated in memory first, so a
    rejected value leaves the file untouched; a value the file already holds is not
    rewritten.
    """
    config_path = _resolve_config_path(args)
    value = override_value(args.key, args.value)

    current = read_config_text(config_path)
    edited = set_key(current, args.key, value, source=config_path)
    validate_config_text(edited, config_path)

    changed = edited != current
    if changed:
        write_config_text(config_path, edited)
    return ConfigSetOutput(args.key, value, config_path.name, changed)


def _cmd_enable(args: argparse.Namespace) -> ContentTypeToggleOutput:
    """Add a content type of shape ``args.shape`` named ``args.name`` to ``bartleby.yml``.

    The block merges in only when the name is absent, so a type the site already
    customized keeps every key. An existing disabled type is turned back on by setting
    its ``enabled`` flag; an enabled one is left alone. Taxonomies the shape refers to
    and the site lacks are added too, as is a ``nav`` entry when ``nav`` is explicit
    and has none. The edited text is validated in memory before it is written.
    """
    config_path = _resolve_config_path(args)
    config = load_config(config_path)
    existing = config.content_types.get(args.name)
    if existing is not None:
        if existing.enabled:
            return ContentTypeToggleOutput(
                "enable", args.shape, args.name, True, config_path.name, False
            )
        reenabled = set_key(
            read_config_text(config_path),
            f"content_types.{args.name}.enabled",
            True,
            source=config_path,
        )
        validate_config_text(reenabled, config_path)
        write_config_text(config_path, reenabled)
        return ContentTypeToggleOutput(
            "enable", args.shape, args.name, True, config_path.name, True, reenabled=True
        )

    edited = _merge_content_shape(
        read_config_text(config_path),
        CONTENT_SHAPES[args.shape],
        args.name,
        config,
        source=config_path,
    )
    validate_config_text(edited, config_path)

    write_config_text(config_path, edited)
    return ContentTypeToggleOutput("enable", args.shape, args.name, True, config_path.name, True)


def _cmd_disable(args: argparse.Namespace) -> ContentTypeToggleOutput:
    """Set ``enabled: false`` on the content type ``args.name``, keeping its config.

    ``nav`` is left alone; a build warns about an entry that links to a disabled type.

    :raises UsageError: When ``bartleby.yml`` defines no content type with that name.
    """
    config_path = _resolve_config_path(args)
    config = load_config(config_path)
    if args.name not in config.content_types:
        raise _unknown_content_type(args.name, config)

    current = read_config_text(config_path)
    edited = set_key(current, f"content_types.{args.name}.enabled", False, source=config_path)
    validate_config_text(edited, config_path)

    changed = edited != current
    if changed:
        write_config_text(config_path, edited)
    return ContentTypeToggleOutput("disable", None, args.name, False, config_path.name, changed)


def _cmd_config_schema(args: argparse.Namespace) -> ConfigSchemaOutput:
    """List every key ``bartleby.yml`` accepts; reads no project file."""
    return ConfigSchemaOutput(list(CONFIG_SCHEMA))


def _port_number(text: str) -> int:
    """Parse a ``--port`` value: an integer from 0 to 65535.

    :raises argparse.ArgumentTypeError: For anything else, which argparse reports
        as a usage error.
    """
    try:
        port = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{text!r} is not a port number (0 to 65535)") from exc
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"{port} is outside the port range 0 to 65535")
    return port


def _cmd_serve(args: argparse.Namespace) -> None:
    """Start the development server (HTTP + initial build + change-driven rebuilds).

    ``DevServer.run`` binds its socket before the initial build, so a busy port
    fails here at once rather than after a full build.

    :raises UsageError: When the host and port cannot be bound.
    """
    config_path = _resolve_config_path(args)
    from bartleby.server import DevServer, ServeBindError, url_host

    config = load_config(config_path, _config_overrides(args))
    host = args.host or config.dev_server.host
    port = args.port if args.port is not None else config.dev_server.port
    server = DevServer(
        config_path,
        host=host,
        port=port,
        events=args.events,
        overrides=_config_overrides(args),
    )
    try:
        server.run()
    except ServeBindError as exc:
        raise UsageError(
            format_error(
                f"cannot serve on {url_host(host)}:{port} ({exc.reason})",
                hint="pass --port with a free port, or --port 0 to pick one",
            )
        ) from exc
