# ABOUTME: CLI commands using argparse — new, build, validate, serve.
# Top-level entry point for the bartleby executable.

from __future__ import annotations

import argparse
import asyncio
import datetime
import logging
import os
import sys
from pathlib import Path

from slugify import slugify

from bartleby.authors import AuthorError, load_authors
from bartleby.build import BuildError, async_build, format_page_error
from bartleby.config import ConfigError, load_config
from bartleby.content import discover_content
from bartleby.metadata import validate_all_metadata
from bartleby.output import (
    BuildOutput,
    ErrorOutput,
    NewPostOutput,
    NewSiteOutput,
    Result,
    ValidateOutput,
    ValidationError,
    render,
)
from bartleby.theme_compile import ThemeCompileError, ThemeCompileResult, compile_theme_css

# Stable, machine-recognizable error codes per failure type. These strings are
# part of the CLI error contract (text and JSON output) and must not change
# without a versioning bump.
_ERROR_CODES: dict[type[Exception], str] = {
    BuildError: "build_error",
    ConfigError: "config_error",
    AuthorError: "author_error",
    ThemeCompileError: "theme_compile_error",
}


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
    _configure_logging()
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        raise SystemExit(1)
    fmt: str = getattr(args, "output", "text")
    try:
        result = handler(args)
    except UsageError as exc:
        _emit_error(ErrorOutput(message=str(exc), code=exc.code, usage=True), fmt)
    except (BuildError, ConfigError, AuthorError, ThemeCompileError) as exc:
        _report_error(exc, fmt)
    else:
        if result is not None:
            _emit_result(result, fmt)


def _emit_result(result: Result, fmt: str) -> None:
    """Print a successful command result in the requested format and exit non-zero on error.

    Successful results print to stdout. A result whose ``exit_code`` is non-zero
    (e.g. a failed validation) still prints, then raises ``SystemExit``.
    """
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


def _configure_logging() -> None:
    """Route the ``bartleby`` logger's non-essential output to stderr.

    Build results stay on stdout (printed directly); warnings such as broken
    cross-references go through ``logging`` to stderr. ``BARTLEBY_DEBUG`` lowers
    the threshold to ``DEBUG`` for development.

    The handler is attached once; repeat ``main()`` calls (e.g. in tests) do not
    stack duplicate handlers.
    """
    logger = logging.getLogger("bartleby")
    level = logging.DEBUG if os.environ.get("BARTLEBY_DEBUG") else logging.INFO
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)


def _report_error(
    exc: BuildError | ConfigError | AuthorError | ThemeCompileError, fmt: str
) -> None:
    """Surface a build/config/author failure in the requested format and exit 1.

    Honors ``BARTLEBY_DEBUG``: when set to a truthy value, the exception is
    re-raised so Python prints the full traceback for development. In text mode
    each collected page error prints to stderr; in JSON mode a single error
    object (carrying the first offending file) prints to stdout.

    :param exc: The build/config/author failure to surface.
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
    else:
        _emit_error(ErrorOutput(message=str(exc), code=code), fmt)
        return
    raise SystemExit(1)


def _global_flags() -> argparse.ArgumentParser:
    """A parent parser carrying the global flags shared by every subcommand.

    Attaching these to each subparser (rather than only the top parser) lets
    them appear after the subcommand, e.g. ``bartleby build --output json``.
    """
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Output format: text (default) or json (machine-readable)",
    )
    parent.add_argument(
        "--config", default=None, help="Path to bartleby.yml (default: ./bartleby.yml)"
    )
    parent.add_argument("--quiet", action="store_true", help="Suppress non-essential output")
    parent.add_argument("--verbose", action="store_true", help="Show detailed progress")
    return parent


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argparse tree for every ``bartleby`` subcommand."""
    flags = _global_flags()
    parser = argparse.ArgumentParser(
        prog="bartleby",
        description="Bartleby static site generator",
        parents=[flags],
    )
    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser("new", help="Scaffold sites or content")
    new_sub = new_parser.add_subparsers(dest="new_command")

    new_site = new_sub.add_parser("site", help="Create a new site directory", parents=[flags])
    new_site.add_argument("name", help="Directory name for the new site")
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
    build_parser.set_defaults(_handler=_cmd_build)

    validate_parser = subparsers.add_parser(
        "validate", help="Validate config + metadata", parents=[flags]
    )
    validate_parser.set_defaults(_handler=_cmd_validate)

    serve_parser = subparsers.add_parser(
        "serve", help="Run the development server", parents=[flags]
    )
    serve_parser.add_argument("--host", default=None, help="Bind host (default from config)")
    serve_parser.add_argument(
        "--port", type=int, default=None, help="Bind port (default from config)"
    )
    serve_parser.add_argument(
        "--dirty", action="store_true", help="Only rebuild files that changed"
    )
    serve_parser.set_defaults(_handler=_cmd_serve)

    theme_parser = subparsers.add_parser("theme", help="Theme asset commands")
    theme_sub = theme_parser.add_subparsers(dest="theme_command")
    theme_compile = theme_sub.add_parser(
        "compile", help="Recompile theme CSS including project overrides", parents=[flags]
    )
    theme_compile.add_argument(
        "--refresh", action="store_true", help="Force re-download of the Tailwind binary"
    )
    theme_compile.set_defaults(_handler=_cmd_theme_compile)

    return parser


def _resolve_config_path(args: argparse.Namespace) -> Path:
    """Resolve ``bartleby.yml`` from ``--config`` or the current directory.

    :raises UsageError: When no config file exists at the resolved location.
    """
    config_path = Path(args.config) if args.config else Path.cwd() / "bartleby.yml"
    if not config_path.exists():
        raise UsageError(f"no bartleby.yml at {config_path}", code="usage_error")
    return config_path


def _cmd_new_site(args: argparse.Namespace) -> NewSiteOutput:
    """Scaffold a fresh project under ``./{args.name}/``."""
    target = Path.cwd() / args.name
    if target.exists():
        raise UsageError(f"{target} already exists")

    target.mkdir(parents=True)
    (target / "content" / "blog" / "posts").mkdir(parents=True)
    (target / "templates").mkdir()
    (target / "static").mkdir()
    (target / "hooks").mkdir()

    (target / "bartleby.yml").write_text(_DEFAULT_CONFIG.format(name=args.name), encoding="utf-8")
    (target / ".authors.yml").write_text(_DEFAULT_AUTHORS, encoding="utf-8")
    (target / "content" / "index.md").write_text(_DEFAULT_INDEX, encoding="utf-8")
    return NewSiteOutput(path=f"{args.name}/", config=f"{args.name}/bartleby.yml")


def _cmd_new_post(args: argparse.Namespace) -> NewPostOutput:
    """Create a new post under ``content/{type}/posts/<slug>.md``."""
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    config = load_config(config_path)
    if args.type not in config.content_types:
        raise UsageError(f"unknown content type {args.type!r}")
    content_type = config.content_types[args.type]
    posts_dir = project_dir / "content" / content_type.path
    posts_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(args.title)
    destination = posts_dir / f"{slug}.md"
    if destination.exists():
        raise UsageError(f"{destination} already exists")
    today = datetime.date.today().isoformat()
    front_matter = (
        f'---\ntitle: "{args.title}"\ndate: {today}\ndraft: true\n---\n\nWrite something here.\n'
    )
    destination.write_text(front_matter, encoding="utf-8")
    return NewPostOutput(path=str(destination))


def _cmd_build(args: argparse.Namespace) -> BuildOutput:
    """Run a full site build from ``./bartleby.yml`` via the async pipeline."""
    config_path = _resolve_config_path(args)
    result = asyncio.run(
        async_build(config_path, include_drafts=args.include_drafts, strict=args.strict)
    )
    return BuildOutput(
        pages=result.page_count,
        static_files=result.static_file_count,
        duration_ms=round(result.duration_seconds * 1000),
        output_dir=result.output_dir,
    )


def _cmd_validate(args: argparse.Namespace) -> ValidateOutput:
    """Validate the config and page metadata without running a full build."""
    config_path = _resolve_config_path(args)
    config = load_config(config_path)
    authors = load_authors(config.config_dir / config.authors_file)
    pages, _assets = discover_content(config, config.config_dir / "content")
    errors = validate_all_metadata(pages, config, authors)
    return ValidateOutput(
        valid=not errors,
        files_checked=len(pages),
        errors=[
            ValidationError(
                file=error.file_path,
                line=0,
                field="",
                message=error.message,
                code="E001",
            )
            for error in errors
        ],
    )


def _cmd_theme_compile(args: argparse.Namespace) -> ThemeCompileResult:
    """Recompile the theme CSS including project overrides via the Tailwind CLI."""
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    from bartleby.theme import get_theme_templates_dir

    return compile_theme_css(project_dir, get_theme_templates_dir(), refresh=args.refresh)


def _cmd_serve(args: argparse.Namespace) -> None:
    """Start the development server (HTTP + initial build + change-driven rebuilds)."""
    config_path = _resolve_config_path(args)
    from bartleby.server import DevServer

    config = load_config(config_path)
    host = args.host or config.dev_server.host
    port = args.port if args.port is not None else config.dev_server.port
    DevServer(config_path, host=host, port=port, dirty=args.dirty).run()


_DEFAULT_CONFIG = """site:
  title: "{name}"
  url: "https://example.com"
  description: "A Bartleby site."

content_types:
  blog:
    path: blog/posts
    readtime: true
    excerpt_separator: "<!-- more -->"
    taxonomies:
      - tags

taxonomies:
  tags:
    slug_format: "{{slug}}"

exclude_patterns:
  - "_drafts/**"
  - "_*.md"
  - ".git/**"
"""

_DEFAULT_AUTHORS = """authors:
  default:
    name: Site Author
"""

_DEFAULT_INDEX = """---
title: Home
---

Welcome to your new Bartleby site.
"""
