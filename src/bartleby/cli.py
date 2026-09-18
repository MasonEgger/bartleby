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
from typing import TYPE_CHECKING

from jinja2 import TemplateNotFound
from slugify import slugify

from bartleby.authors import AuthorError, load_authors
from bartleby.build import (
    BuildError,
    async_build,
    build_dry_run,
    calculate_readtime,
    format_page_error,
)
from bartleby.config import ConfigError, load_config
from bartleby.content import ContentError, discover_content
from bartleby.content_query import (
    ContentGet,
    ContentList,
    ContentQueryError,
    get_content,
    list_content,
    select_published,
)
from bartleby.crossrefs import resolve_all_crossrefs, resolve_page_crossrefs
from bartleby.export import export_content
from bartleby.linting import lint_site
from bartleby.markdown_pipeline import create_markdown_renderer, render_markdown
from bartleby.metadata import validate_all_metadata
from bartleby.output import (
    BuildOutput,
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
from bartleby.urls import generate_all_urls

if TYPE_CHECKING:
    from bartleby.config import BartlebyConfig
    from bartleby.content import Page

# Stable, machine-recognizable error codes per failure type. These strings are
# part of the CLI error contract (text and JSON output) and must not change
# without a versioning bump.
_ERROR_CODES: dict[type[Exception], str] = {
    BuildError: "build_error",
    ConfigError: "config_error",
    AuthorError: "author_error",
    ThemeCompileError: "theme_compile_error",
    ContentError: "content_error",
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
    except (BuildError, ConfigError, AuthorError, ThemeCompileError, ContentError) as exc:
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
    exc: BuildError | ConfigError | AuthorError | ThemeCompileError | ContentError, fmt: str
) -> None:
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
    build_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing to disk",
    )
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
    serve_parser.add_argument(
        "--events",
        action="store_true",
        help="Emit structured JSON events (one object per line) for changes and rebuilds",
    )
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


def _cmd_build(args: argparse.Namespace) -> BuildOutput | DryRunOutput:
    """Run a full site build from ``./bartleby.yml`` via the async pipeline.

    With ``--dry-run`` the build renders into a temp tree, diffs it against the
    existing ``site/``, and reports the change set without writing to disk.
    """
    config_path = _resolve_config_path(args)
    if args.dry_run:
        diff = build_dry_run(config_path, include_drafts=args.include_drafts, strict=args.strict)
        return DryRunOutput(
            added=diff.added,
            modified=diff.modified,
            unchanged=len(diff.unchanged),
            deleted=diff.deleted,
        )
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
    """Validate the config and content without running a full build.

    Beyond metadata validation this dry-runs URL generation, checks that every
    page-level ``template:`` override resolves to an existing template, and scans
    rendered HTML for broken cross-references (Design 17).
    """
    config_path = _resolve_config_path(args)
    project_dir = config_path.parent
    config = load_config(config_path)
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
    config = load_config(config_path)
    pages, _assets = discover_content(config, config.config_dir / "content")
    if args.type is not None and args.type not in config.content_types:
        raise UsageError(f"unknown content type {args.type!r}")
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
    project_dir = config_path.parent
    config = load_config(config_path)
    authors = load_authors(project_dir / config.authors_file)
    pages, _assets = discover_content(config, project_dir / "content")
    generate_all_urls(pages, config)

    shortcodes = _discover_shortcode_names(project_dir)
    style_guide_text = _load_style_guide(project_dir, config.ai.skills.style_guide)
    skills = generate_skills(
        pages,
        config,
        authors,
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
        raise UsageError(f"style guide not found at {path}")
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
    from bartleby.theme import get_theme_templates_dir

    return compile_theme_css(project_dir, get_theme_templates_dir(), refresh=args.refresh)


def _cmd_serve(args: argparse.Namespace) -> None:
    """Start the development server (HTTP + initial build + change-driven rebuilds)."""
    config_path = _resolve_config_path(args)
    from bartleby.server import DevServer

    config = load_config(config_path)
    host = args.host or config.dev_server.host
    port = args.port if args.port is not None else config.dev_server.port
    DevServer(config_path, host=host, port=port, dirty=args.dirty, events=args.events).run()


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
