# ABOUTME: CLI commands using argparse — new, build, validate, serve.
# Top-level entry point for the bartleby executable.

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from slugify import slugify

from bartleby.authors import load_authors
from bartleby.build import build
from bartleby.config import ConfigError, load_config
from bartleby.content import discover_content
from bartleby.metadata import validate_all_metadata


def main(argv: list[str] | None = None) -> None:
    """Top-level CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        raise SystemExit(1)
    handler(args)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argparse tree for every ``bartleby`` subcommand."""
    parser = argparse.ArgumentParser(prog="bartleby", description="Bartleby static site generator")
    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser("new", help="Scaffold sites or content")
    new_sub = new_parser.add_subparsers(dest="new_command")

    new_site = new_sub.add_parser("site", help="Create a new site directory")
    new_site.add_argument("name", help="Directory name for the new site")
    new_site.set_defaults(_handler=_cmd_new_site)

    new_post = new_sub.add_parser("post", help="Create a new content file")
    new_post.add_argument("title", help="Post title (used as front matter and slug source)")
    new_post.add_argument("--type", default="blog", help="Content type (default: blog)")
    new_post.set_defaults(_handler=_cmd_new_post)

    build_parser = subparsers.add_parser("build", help="Render the site")
    build_parser.add_argument(
        "--strict", action="store_true", help="Fail on cross-reference and validation errors"
    )
    build_parser.add_argument("--include-drafts", action="store_true", help="Include drafts")
    build_parser.set_defaults(_handler=_cmd_build)

    validate_parser = subparsers.add_parser("validate", help="Validate config + metadata")
    validate_parser.set_defaults(_handler=_cmd_validate)

    serve_parser = subparsers.add_parser("serve", help="Run the development server")
    serve_parser.add_argument("--host", default=None, help="Bind host (default from config)")
    serve_parser.add_argument(
        "--port", type=int, default=None, help="Bind port (default from config)"
    )
    serve_parser.add_argument(
        "--dirty", action="store_true", help="Only rebuild files that changed"
    )
    serve_parser.set_defaults(_handler=_cmd_serve)

    return parser


def _cmd_new_site(args: argparse.Namespace) -> None:
    """Scaffold a fresh project under ``./{args.name}/``."""
    target = Path.cwd() / args.name
    if target.exists():
        print(f"error: {target} already exists", file=sys.stderr)
        raise SystemExit(1)

    target.mkdir(parents=True)
    (target / "content" / "blog" / "posts").mkdir(parents=True)
    (target / "templates").mkdir()
    (target / "static").mkdir()
    (target / "hooks").mkdir()

    (target / "bartleby.yml").write_text(_DEFAULT_CONFIG.format(name=args.name), encoding="utf-8")
    (target / ".authors.yml").write_text(_DEFAULT_AUTHORS, encoding="utf-8")
    (target / "content" / "index.md").write_text(_DEFAULT_INDEX, encoding="utf-8")
    print(f"Created site at {target}")


def _cmd_new_post(args: argparse.Namespace) -> None:
    """Create a new post under ``content/{type}/posts/<slug>.md``."""
    project_dir = Path.cwd()
    config_path = project_dir / "bartleby.yml"
    if not config_path.exists():
        print("error: no bartleby.yml in current directory", file=sys.stderr)
        raise SystemExit(1)
    config = load_config(config_path)
    if args.type not in config.content_types:
        print(f"error: unknown content type {args.type!r}", file=sys.stderr)
        raise SystemExit(1)
    content_type = config.content_types[args.type]
    posts_dir = project_dir / "content" / content_type.path
    posts_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(args.title)
    destination = posts_dir / f"{slug}.md"
    if destination.exists():
        print(f"error: {destination} already exists", file=sys.stderr)
        raise SystemExit(1)
    today = datetime.date.today().isoformat()
    front_matter = (
        f'---\ntitle: "{args.title}"\ndate: {today}\ndraft: true\n---\n\nWrite something here.\n'
    )
    destination.write_text(front_matter, encoding="utf-8")
    print(f"Created post {destination}")


def _cmd_build(args: argparse.Namespace) -> None:
    """Run a full site build from ``./bartleby.yml``."""
    config_path = Path.cwd() / "bartleby.yml"
    if not config_path.exists():
        print("error: no bartleby.yml in current directory", file=sys.stderr)
        raise SystemExit(1)
    result = build(config_path, include_drafts=args.include_drafts)
    print(f"Built {result.page_count} pages in {result.duration_seconds:.2f}s")


def _cmd_validate(args: argparse.Namespace) -> None:
    """Validate the config and page metadata without running a full build."""
    del args
    config_path = Path.cwd() / "bartleby.yml"
    if not config_path.exists():
        print("error: no bartleby.yml in current directory", file=sys.stderr)
        raise SystemExit(1)
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    authors = load_authors(config.config_dir / config.authors_file)
    pages, _assets = discover_content(config, config.config_dir / "content")
    errors = validate_all_metadata(pages, config, authors)
    if errors:
        for error in errors:
            print(f"{error.file_path}: {error.message}", file=sys.stderr)
        raise SystemExit(1)
    print("validation passed")


def _cmd_serve(args: argparse.Namespace) -> None:
    """Start the development server (HTTP + initial build + change-driven rebuilds)."""
    config_path = Path.cwd() / "bartleby.yml"
    if not config_path.exists():
        print("error: no bartleby.yml in current directory", file=sys.stderr)
        raise SystemExit(1)
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
