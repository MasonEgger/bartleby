# ABOUTME: Build pipeline orchestrator wiring all components together.
# Loads config, discovers content, renders, and writes the site/ output.

from __future__ import annotations

import datetime
import logging
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

from jinja2 import TemplateError

import bartleby
from bartleby.assets import copy_colocated_assets, copy_static_files
from bartleby.authors import load_authors
from bartleby.config import load_config
from bartleby.content import discover_content
from bartleby.crossrefs import resolve_all_crossrefs
from bartleby.feeds import generate_feeds
from bartleby.icons import tree_shake_icons
from bartleby.listings import generate_listing_pages
from bartleby.llm import (
    generate_llms_full_txt,
    generate_llms_txt,
    write_markdown_variant,
)
from bartleby.markdown_pipeline import create_markdown_renderer, render_markdown
from bartleby.metadata import validate_all_metadata
from bartleby.navigation import build_navigation, link_pages
from bartleby.plugins import PluginCollection, discover_hooks
from bartleby.search import build_search_index, write_search_index
from bartleby.shortcodes import ShortcodeError, process_shortcodes
from bartleby.sitemap import write_robots_txt, write_sitemap
from bartleby.taxonomies import AllTaxonomies, build_taxonomies, generate_taxonomy_pages
from bartleby.templates import (
    BuildInfo,
    build_page_context,
    create_jinja_env,
    load_data_files,
    resolve_template_name,
)
from bartleby.urls import generate_all_urls

if TYPE_CHECKING:
    from jinja2 import Environment

    from bartleby.authors import Author
    from bartleby.config import BartlebyConfig
    from bartleby.content import Page


@dataclass(slots=True)
class BuildResult:
    """Summary returned from :func:`build`.

    :ivar page_count: Number of pages written (content + generated pages).
    :ivar duration_seconds: Wall-clock build time.
    :ivar static_file_count: Non-HTML asset files copied into the output tree.
    :ivar output_dir: The directory the finished site was written to.
    """

    page_count: int
    duration_seconds: float
    static_file_count: int = 0
    output_dir: str = "site"


@dataclass(slots=True)
class PageError:
    """A single page-level failure collected during the render pass.

    :ivar file_path: Path to the offending content file.
    :ivar message: Human-readable description of what went wrong.
    """

    file_path: str
    message: str


class BuildError(Exception):
    """Raised at the end of a render pass that produced one or more errors.

    The render pass collects every page-level failure instead of stopping on
    the first, so :attr:`errors` carries the full list. The pre-existing
    ``site/`` output is left untouched when this is raised.

    :ivar errors: Every :class:`PageError` collected during the build.
    """

    def __init__(self, errors: list[PageError]) -> None:
        self.errors = errors
        summary = "; ".join(format_page_error(error) for error in errors)
        super().__init__(f"build failed with {len(errors)} error(s): {summary}")


_LOGGER = logging.getLogger("bartleby")

_WORDS_PER_MINUTE = 265
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def format_page_error(error: PageError) -> str:
    """Render a :class:`PageError` as a single stable ``path: message`` line.

    Both the text CLI output and the JSON formatter route page-level failures
    through this helper so the wording stays identical across output modes.

    :param error: The collected page failure to format.
    :returns: ``"<file_path>: <message>"``.
    """
    return f"{error.file_path}: {error.message}"


def build(config_path: Path, *, include_drafts: bool = False, strict: bool = False) -> BuildResult:
    """Run the full Bartleby build pipeline against ``config_path``.

    :param config_path: Path to ``bartleby.yml``.
    :param include_drafts: When ``True``, draft pages are written to the
        output. Defaults to ``False`` for production builds.
    :param strict: When ``True``, broken cross-references abort the build.
        Cross-reference errors are always printed to stderr; ``strict`` only
        controls whether they are fatal.
    :returns: A :class:`BuildResult` carrying the page count and wall time.
    :raises ValueError: When metadata validation fails, or when ``strict``
        is on and any cross-reference cannot be resolved.
    """
    started = time.perf_counter()
    plugins = PluginCollection()

    config = load_config(config_path)
    project_dir = config.config_dir
    plugins.merge(discover_hooks(project_dir))
    config = plugins.run_event("on_config", config)
    authors_path = project_dir / config.authors_file
    authors = load_authors(authors_path)

    content_dir = project_dir / "content"
    pages, assets = discover_content(config, content_dir)

    if not include_drafts:
        pages = [page for page in pages if not page.draft]

    # Dispatch on_pages only after drafts are filtered out so plugins never
    # operate on pages that the build is about to discard.
    pages = list(plugins.run_event("on_pages", pages, config=config))

    metadata_errors = validate_all_metadata(pages, config, authors)
    if metadata_errors:
        message = "\n".join(f"  {error.file_path}: {error.message}" for error in metadata_errors)
        raise ValueError(f"metadata validation failed:\n{message}")

    generate_all_urls(pages, config)
    taxonomy_data = build_taxonomies(pages, config)
    taxonomy_pages = generate_taxonomy_pages(taxonomy_data, config)
    listing_pages = generate_listing_pages(pages, config, content_dir)
    all_pages = pages + taxonomy_pages + listing_pages
    nav = build_navigation(config, pages)
    link_pages(nav)

    md_renderer = create_markdown_renderer(config)
    env = create_jinja_env(config, project_dir)
    env = plugins.run_event("on_env", env, config=config)

    data = load_data_files(project_dir)
    build_info = BuildInfo(date=datetime.date.today(), bartleby_version=bartleby.__version__)

    final_output_dir = project_dir / "site"
    # Render into a sibling temp directory and swap it into place only on full
    # success, so a failed build never touches the previous good site/.
    build_dir = Path(tempfile.mkdtemp(prefix=".bartleby-build-", dir=project_dir))
    output_dir = build_dir

    page_errors: list[PageError] = []

    for page in all_pages:
        try:
            source = process_shortcodes(page.raw_content, {"build": build_info, "page": page}, env)
            source = plugins.run_event("on_page_markdown", source, page=page, config=config)
            rendered = render_markdown(source, md_renderer)
            page.rendered_content = rendered.html
        except (ShortcodeError, ValueError) as exc:
            page_errors.append(PageError(file_path=str(page.source_path), message=str(exc)))
            continue

        content_type = (
            config.content_types.get(page.content_type_name) if page.content_type_name else None
        )
        if content_type is not None and content_type.readtime and page.raw_content:
            page.readtime = calculate_readtime(page.raw_content)
        if content_type is not None and content_type.excerpt_separator and page.raw_content:
            page.excerpt = extract_excerpt(page.raw_content, content_type.excerpt_separator)

    if page_errors:
        _fail_build(page_errors, build_dir, plugins)

    # Cross-reference resolution needs every page rendered before any rewriting,
    # so it lives outside the render loop above and below the template render below.
    crossref_errors = resolve_all_crossrefs(all_pages, content_dir)
    if crossref_errors:
        for error in crossref_errors:
            _LOGGER.warning(
                "crossref: %s -> %s: %s",
                error.source_path,
                error.target_path,
                error.message,
            )
        if strict:
            raise ValueError(f"strict mode: {len(crossref_errors)} unresolved cross-reference(s)")

    rendered_html: list[str] = []
    for page in all_pages:
        content_type = (
            config.content_types.get(page.content_type_name) if page.content_type_name else None
        )
        template_type = _template_type_for(page, content_type)
        try:
            template_name = resolve_template_name(page, template_type, project_dir)
            template = env.get_template(template_name)
            context = build_page_context(
                page=page,
                site_config=config.site,
                nav=nav.items,
                all_pages=all_pages,
                taxonomy_data=_taxonomy_context(taxonomy_data),
                config=config,
                build_info=build_info,
                data=data,
                authors=authors,
            )
            html = template.render(**context)
            html = plugins.run_event("on_post_page", html, page=page, config=config)
            _write_page(output_dir, page, html)
            rendered_html.append(html)
        except (TemplateError, ValueError) as exc:
            page_errors.append(PageError(file_path=str(page.source_path), message=str(exc)))

    if page_errors:
        _fail_build(page_errors, build_dir, plugins)

    not_found_html = _render_404(
        env=env,
        config=config,
        nav=nav.items,
        all_pages=all_pages,
        taxonomy_data=_taxonomy_context(taxonomy_data),
        build_info=build_info,
        data=data,
        authors=authors,
        project_dir=project_dir,
    )
    (output_dir / "404.html").write_text(not_found_html, encoding="utf-8")
    rendered_html.append(not_found_html)

    from bartleby.theme import get_theme_templates_dir as _theme_dir

    theme_static = _theme_dir().parent / "static"
    copy_static_files(theme_static, output_dir)
    copy_static_files(project_dir / "static", output_dir)
    _apply_compiled_theme_css(project_dir, output_dir)
    copy_colocated_assets(assets, pages, content_dir, output_dir)
    icon_packs = {pack: bool(value) for pack, value in config.theme.icon_packs.items()} or {
        "material": True,
        "fontawesome": True,
        "octicons": True,
        "simple": True,
    }
    tree_shake_icons(
        rendered_html + _template_sources(project_dir),
        icon_packs,
        output_dir,
    )
    write_search_index(build_search_index(pages, config), output_dir)
    generate_feeds(pages, config, output_dir)
    if config.ai.markdown_variants:
        for page in pages:
            if not page.draft and page.raw_content:
                write_markdown_variant(page, output_dir)
    if config.ai.llms_txt:
        (output_dir / "llms.txt").write_text(generate_llms_txt(pages, config), encoding="utf-8")
    if config.ai.llms_full_txt:
        (output_dir / "llms-full.txt").write_text(
            generate_llms_full_txt(pages, config), encoding="utf-8"
        )
    write_sitemap(all_pages, config.site, output_dir)
    static_robots_exists = (project_dir / "static" / "robots.txt").exists()
    write_robots_txt(
        config.site, config.ai, output_dir, static_override_exists=static_robots_exists
    )

    _swap_output_into_place(build_dir, final_output_dir)

    static_file_count = sum(
        1
        for path in final_output_dir.rglob("*")
        if path.is_file() and path.suffix.lower() != ".html"
    )

    duration = time.perf_counter() - started
    return BuildResult(
        page_count=len(all_pages),
        duration_seconds=duration,
        static_file_count=static_file_count,
        output_dir=f"{final_output_dir.name}/",
    )


def _apply_compiled_theme_css(project_dir: Path, output_dir: Path) -> None:
    """Override the shipped CSS with the project's compiled ``.bartleby/theme.css``.

    The compiled CSS wins only when it exists and is at least as new as the
    template tree (see :func:`bartleby.theme_compile.active_theme_css`). The
    build never downloads the Tailwind binary; it only consumes an already
    compiled stylesheet produced by ``bartleby theme compile``.
    """
    from bartleby.theme_compile import active_theme_css

    compiled = active_theme_css(project_dir)
    if compiled is None:
        return
    destination = output_dir / "css" / "main.css"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(compiled, destination)


def _fail_build(
    page_errors: list[PageError], build_dir: Path, plugins: PluginCollection
) -> NoReturn:
    """Discard the partial build, fire ``on_build_error`` once, and raise.

    The hook receives the assembled :class:`BuildError` so a plugin can inspect
    every collected :class:`PageError` in a single call. The temp build
    directory is removed first so a failed build never leaves output behind.

    :param page_errors: Every page-level failure collected during the pass.
    :param build_dir: The temp directory holding the partial build output.
    :param plugins: The active plugin collection to dispatch the hook through.
    :raises BuildError: Always, carrying ``page_errors``.
    """
    shutil.rmtree(build_dir, ignore_errors=True)
    error = BuildError(page_errors)
    plugins.run_event("on_build_error", error)
    raise error


def _template_type_for(page: Page, content_type: object) -> str:
    """Pick the template type bucket — taxonomy and listing pages bypass post/page logic."""
    taxonomy_kind = page.custom_metadata.get("taxonomy_kind")
    if taxonomy_kind == "term":
        return "taxonomy"
    if taxonomy_kind == "index":
        return "taxonomy_index"
    if page.custom_metadata.get("listing_kind") == "content_type":
        return "list"
    return "post" if content_type is not None else "page"


def _taxonomy_context(taxonomy_data: AllTaxonomies) -> dict[str, object]:
    """Adapt :class:`AllTaxonomies` into a template-friendly dict."""
    return {
        "global": taxonomy_data.global_taxonomies,
        "by_content_type": taxonomy_data.content_type_taxonomies,
    }


def _render_404(
    *,
    env: Environment,
    config: BartlebyConfig,
    nav: list[Any],
    all_pages: list[Page],
    taxonomy_data: dict[str, Any],
    build_info: BuildInfo,
    data: dict[str, object],
    authors: dict[str, Author],
    project_dir: Path,
) -> str:
    """Render the standalone ``404.html`` from the theme's 404 template.

    The 404 page is not a content page, so it carries a synthetic
    :class:`~bartleby.content.Page` that supplies the title and URL the base
    template expects. The project may override ``404.html`` in its own
    templates directory; resolution goes through Jinja's loader so the 5-level
    cascade still applies.

    :returns: The fully rendered 404 HTML.
    """
    from bartleby.content import Page

    not_found_source = project_dir / "content" / "404.md"
    not_found_page = Page(
        source_path=Path("404.md"),
        abs_source_path=not_found_source,
        title="404 — Not Found",
        description="The requested page could not be found.",
    )
    not_found_page.output_url = "/404.html"
    template = env.get_template("404.html")
    context = build_page_context(
        page=not_found_page,
        site_config=config.site,
        nav=nav,
        all_pages=all_pages,
        taxonomy_data=taxonomy_data,
        config=config,
        build_info=build_info,
        data=data,
        authors=authors,
    )
    return template.render(**context)


def _template_sources(project_dir: Path) -> list[str]:
    """Return the raw text of every theme and project template.

    Tree-shaking scans rendered HTML for icon references, but icons can also be
    referenced directly in template markup that never appears verbatim in any
    single rendered page (e.g. a partial included only on some pages). Reading
    the template sources ensures those references are retained too.
    """
    from bartleby.theme import get_theme_templates_dir as _theme_dir

    sources: list[str] = []
    template_roots = [_theme_dir(), project_dir / "templates"]
    for root in template_roots:
        if not root.is_dir():
            continue
        for template_file in root.rglob("*.html"):
            sources.append(template_file.read_text(encoding="utf-8"))
    return sources


async def async_build(
    config_path: Path, *, include_drafts: bool = False, strict: bool = False
) -> BuildResult:
    """Async wrapper around :func:`build` for use with ``asyncio.run``.

    The sync build does the heavy lifting; this coroutine offloads it to a
    worker thread (so the surrounding async program — e.g. the dev server's
    HTTP loop — can keep running) and returns the same :class:`BuildResult`.
    Plugin hooks always execute in the calling process: by running the build
    in a thread (not a child process) the hook registration, dispatch, and
    Jinja2 environment never cross a process boundary.
    """
    import asyncio

    return await asyncio.to_thread(
        build, config_path, include_drafts=include_drafts, strict=strict
    )


def extract_excerpt(markdown_source: str, separator: str | None) -> str:
    """Return the excerpt portion of ``markdown_source``.

    :param markdown_source: Raw markdown content.
    :param separator: The configured excerpt separator (e.g. ``<!-- more -->``)
        or ``None`` to fall back to the first paragraph.
    :returns: The excerpt as raw markdown (caller decides whether to render).
    """
    if separator and separator in markdown_source:
        return markdown_source.split(separator, 1)[0].strip()
    paragraphs = [block.strip() for block in markdown_source.split("\n\n") if block.strip()]
    return paragraphs[0] if paragraphs else ""


def calculate_readtime(text: str) -> int:
    """Estimate read time in minutes assuming ~265 words per minute.

    :param text: Page text (markdown or HTML — tags are stripped first).
    :returns: Integer number of minutes, always at least ``1``.
    """
    plain = _HTML_TAG_RE.sub(" ", text)
    word_count = len(plain.split())
    if word_count == 0:
        return 1
    minutes = max(1, round(word_count / _WORDS_PER_MINUTE))
    return minutes


def _swap_output_into_place(build_dir: Path, final_output_dir: Path) -> None:
    """Replace ``final_output_dir`` with the freshly built ``build_dir``.

    The previous output is removed only after the new build is complete, so an
    interrupted or failed build can never leave a half-written ``site/``. The
    new directory is renamed into place (an atomic operation on the same
    filesystem) once the old one is gone.

    :param build_dir: The temp directory holding the completed build output.
    :param final_output_dir: The destination ``site/`` directory to swap in.
    """
    if final_output_dir.exists():
        shutil.rmtree(final_output_dir)
    os.replace(build_dir, final_output_dir)


def _write_page(output_dir: Path, page: Page, html: str) -> None:
    """Write the rendered HTML for ``page`` to its output URL location."""
    url = page.output_url.strip("/")
    destination = output_dir / "index.html" if not url else output_dir / url / "index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
