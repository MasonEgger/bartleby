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
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

from jinja2 import TemplateError

import bartleby
from bartleby.agent_surface import write_agent_surface
from bartleby.assets import (
    AssetCollisionError,
    copy_colocated_assets,
    copy_static_files,
    drop_draft_only_assets,
)
from bartleby.authors import load_authors
from bartleby.config import load_config
from bartleby.content import discover_content
from bartleby.content_query import select_published
from bartleby.crossrefs import resolve_all_crossrefs
from bartleby.feeds import generate_feeds
from bartleby.icons import DEFAULT_ICON_PACKS, tree_shake_icons
from bartleby.listings import LISTING_KIND_KEY, ListingKind, generate_listing_pages
from bartleby.llm import (
    generate_llms_full_txt,
    generate_llms_txt,
    write_markdown_variant,
)
from bartleby.markdown_pipeline import create_markdown_renderer, render_markdown
from bartleby.metadata import validate_all_metadata
from bartleby.navigation import build_navigation, link_pages
from bartleby.plugins import PluginCollection, discover_hooks, discover_plugins
from bartleby.search import build_search_index, write_search_index
from bartleby.shortcodes import ShortcodeError, process_shortcodes
from bartleby.sitemap import write_robots_txt, write_sitemap
from bartleby.taxonomies import (
    TAXONOMY_KIND_KEY,
    AllTaxonomies,
    TaxonomyKind,
    build_taxonomies,
    generate_taxonomy_pages,
)
from bartleby.templates import (
    BuildInfo,
    build_page_context,
    create_jinja_env,
    load_data_files,
    resolve_template_name,
)
from bartleby.theme import get_theme_templates_dir
from bartleby.urls import generate_all_urls

if TYPE_CHECKING:
    from jinja2 import Environment

    from bartleby.authors import Author
    from bartleby.config import BartlebyConfig
    from bartleby.content import ColocatedAsset, Page


@dataclass(slots=True)
class _BuildState:
    """Mutable workspace threaded through the build's phase helpers.

    Each phase (load inputs, filter/validate, render, emit) reads and extends
    this one object instead of passing a dozen positional arguments around. It
    is an internal implementation detail of :func:`build`, not a public type.
    """

    plugins: PluginCollection
    config: BartlebyConfig
    project_dir: Path
    content_dir: Path
    authors: dict[str, Author]
    pages: list[Page]
    assets: list[ColocatedAsset]
    all_pages: list[Page] = field(default_factory=list)
    taxonomy_data: AllTaxonomies | None = None
    nav: Any = None
    env: Environment | None = None
    md_renderer: Any = None
    data: dict[str, object] = field(default_factory=dict)
    build_info: BuildInfo | None = None
    output_dir: Path | None = None
    final_output_dir: Path | None = None
    static_file_count: int = 0


@dataclass(slots=True)
class BuildResult:
    """Summary returned from :func:`build`.

    :ivar page_count: Number of pages written (content + generated pages).
    :ivar duration_seconds: Wall-clock build time.
    :ivar static_file_count: Static files and co-located assets copied into the
        output tree (theme static, project ``static/``, and co-located
        assets). Excludes generated artifacts (search index, feeds, markdown
        variants, llms.txt files, sitemap, agent-surface JSON, robots.txt,
        tree-shaken icon SVGs).
    :ivar output_dir: The directory the finished site was written to.
    """

    page_count: int
    duration_seconds: float
    static_file_count: int = 0
    output_dir: str = "site"


@dataclass(slots=True)
class DryRunResult:
    """What a ``--dry-run`` build would change, relative to the current ``site/``.

    :ivar added: Output paths that would be newly created.
    :ivar modified: Output paths whose bytes would change.
    :ivar unchanged: Output paths that would be written identically.
    :ivar deleted: Existing output paths that would no longer be produced.
    """

    added: list[str]
    modified: list[str]
    unchanged: list[str]
    deleted: list[str]


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


def build(
    config_path: Path,
    *,
    include_drafts: bool = False,
    strict: bool = False,
    dry_run: bool = False,
) -> BuildResult | DryRunResult:
    """Run the full Bartleby build pipeline against ``config_path``.

    :param config_path: Path to ``bartleby.yml``.
    :param include_drafts: When ``True``, draft pages are written to the
        output. Defaults to ``False`` for production builds.
    :param strict: When ``True``, broken cross-references abort the build.
        Cross-reference errors are always printed to stderr; ``strict`` only
        controls whether they are fatal.
    :param dry_run: When ``True``, the freshly rendered output is compared to
        the existing ``site/`` and a :class:`DryRunResult` is returned; nothing
        is written to disk and the previous ``site/`` is left untouched.
    :returns: A :class:`BuildResult` for a normal build, or a
        :class:`DryRunResult` when ``dry_run`` is set.
    :raises BuildError: When metadata validation fails, or when ``strict``
        is on and any cross-reference cannot be resolved.

    The temp build directory created partway through this pipeline is removed
    on every exit path that does not swap it into place, regardless of which
    phase raises; see the ``finally`` block below.
    """
    started = time.perf_counter()

    state = _load_inputs(config_path)
    try:
        _filter_and_validate(state, include_drafts=include_drafts)
        rendered_html = _render_all_pages(state, strict=strict)
        _emit_outputs(state, rendered_html)

        return _finish_build(state, started=started, dry_run=dry_run)
    finally:
        # Backstop for every exit path that did not swap or discard the temp
        # dir itself (a raised BuildError, or any other exception out of the
        # pipeline). On the success and dry-run paths the temp dir is already
        # gone by this point (renamed away or explicitly removed), so this is
        # a no-op; the existence check makes the double-removal safe.
        if state.output_dir is not None and state.output_dir.exists():
            shutil.rmtree(state.output_dir, ignore_errors=True)


def _load_inputs(config_path: Path) -> _BuildState:
    """Phase 1: load config, discover plugins/hooks, and read authors + content.

    Fires the early lifecycle hooks (``on_startup``, ``on_config``,
    ``on_pre_build``) and returns a populated :class:`_BuildState` carrying the
    config, plugin collection, authors, and the discovered pages/assets.
    """
    plugins = PluginCollection()
    config = load_config(config_path)
    project_dir = config.config_dir
    # Registration order at equal priority: internal handlers (already on
    # `plugins`), then installed plugins (alphabetical), then project hooks last.
    plugins.merge(discover_plugins(config.disabled_plugins))
    plugins.merge(discover_hooks(project_dir))
    plugins.run_event("on_startup", "build")
    config = plugins.run_event("on_config", config)
    plugins.run_event("on_pre_build", config)
    authors = load_authors(project_dir / config.authors_file)

    content_dir = project_dir / "content"
    pages, assets = discover_content(config, content_dir)

    return _BuildState(
        plugins=plugins,
        config=config,
        project_dir=project_dir,
        content_dir=content_dir,
        authors=authors,
        pages=pages,
        assets=assets,
    )


def _filter_and_validate(state: _BuildState, *, include_drafts: bool) -> None:
    """Phase 2: drop drafts, validate metadata, and build the page/nav graph.

    Populates ``state`` with the full page list (content + taxonomy + listing
    pages), navigation, the Jinja environment, the markdown renderer, data
    files, build info, and the temp/final output directories.

    :raises BuildError: When metadata validation fails.
    """
    config = state.config
    plugins = state.plugins
    pages = state.pages

    if not include_drafts:
        published_pages = select_published(pages)
        state.assets = drop_draft_only_assets(state.assets, pages, published_pages)
        pages = published_pages

    # Dispatch on_files only after drafts are filtered out so plugins never
    # operate on pages that the build is about to discard.
    pages = list(plugins.run_event("on_files", pages, config=config))
    state.pages = pages

    metadata_errors = validate_all_metadata(pages, config, state.authors)
    if metadata_errors:
        raise BuildError(
            [
                PageError(file_path=error.file_path, message=error.message)
                for error in metadata_errors
            ]
        )

    generate_all_urls(pages, config)
    state.taxonomy_data = build_taxonomies(pages, config)
    taxonomy_pages = generate_taxonomy_pages(state.taxonomy_data, config)
    # Built before listing generation so listing intro content (content/{type}/index.md)
    # renders through the same renderer instance the page render loop uses below.
    state.md_renderer = create_markdown_renderer(config)
    listing_pages = generate_listing_pages(pages, config, state.content_dir, state.md_renderer)
    state.all_pages = pages + taxonomy_pages + listing_pages

    nav = build_navigation(config, pages)
    link_pages(nav)
    state.nav = plugins.run_event("on_nav", nav, config=config)

    env = create_jinja_env(config, state.project_dir)
    state.env = plugins.run_event("on_env", env, config=config)

    state.data = load_data_files(state.project_dir)
    state.build_info = BuildInfo(date=datetime.date.today(), bartleby_version=bartleby.__version__)

    state.final_output_dir = state.project_dir / config.output_dir
    # Render into a sibling temp directory and swap it into place only on full
    # success, so a failed build never touches the previous good output dir.
    state.output_dir = Path(tempfile.mkdtemp(prefix=".bartleby-build-", dir=state.project_dir))


def _render_all_pages(state: _BuildState, *, strict: bool) -> list[str]:
    """Phase 3: render markdown, resolve crossrefs, render templates, and the 404.

    Both the markdown render loop and the template render loop collect every
    page-level failure and abort the build (discarding the temp dir) if any
    occurred, instead of stopping on the first error.

    :raises BuildError: When ``strict`` is set and a cross-reference is broken.
    :returns: Every rendered HTML document, including ``404.html``, for icon
        tree-shaking downstream.
    """
    config = state.config
    plugins = state.plugins
    assert state.env is not None
    assert state.build_info is not None
    assert state.output_dir is not None
    assert state.taxonomy_data is not None
    env = state.env
    build_info = state.build_info
    output_dir = state.output_dir
    taxonomy_context = _taxonomy_context(state.taxonomy_data)

    page_errors: list[PageError] = []
    for page in state.all_pages:
        plugins.run_event("on_pre_page", page, config=config)
        # on_page_read_source may return a replacement source string; None falls
        # back to the page's own raw content read at discovery time.
        overridden_source = plugins.run_query("on_page_read_source", page=page, config=config)
        raw_source = overridden_source if overridden_source is not None else page.raw_content
        try:
            source = process_shortcodes(raw_source, {"build": build_info, "page": page}, env)
            source = plugins.run_event("on_page_markdown", source, page=page, config=config)
            rendered = render_markdown(source, state.md_renderer)
            html_content = plugins.run_event(
                "on_page_content", rendered.html, page=page, config=config
            )
            page.rendered_content = html_content
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
        _fail_build(page_errors, plugins)

    # Cross-reference resolution needs every page rendered before any rewriting,
    # so it lives between the markdown loop above and the template loop below.
    crossref_errors = resolve_all_crossrefs(state.all_pages, state.content_dir)
    if crossref_errors:
        for error in crossref_errors:
            _LOGGER.warning(
                "crossref: %s -> %s: %s",
                error.source_path,
                error.target_path,
                error.message,
            )
        if strict:
            raise BuildError(
                [
                    PageError(
                        file_path=error.source_path,
                        message=f"strict mode: unresolved cross-reference to "
                        f"{error.target_path!r}: {error.message}",
                    )
                    for error in crossref_errors
                ]
            )

    rendered_html: list[str] = []
    for page in state.all_pages:
        content_type = (
            config.content_types.get(page.content_type_name) if page.content_type_name else None
        )
        template_type = _template_type_for(page, content_type)
        try:
            template_name = resolve_template_name(page, template_type, state.project_dir)
            template = env.get_template(template_name)
            context = build_page_context(
                page=page,
                site_config=config.site,
                nav=state.nav.items,
                all_pages=state.all_pages,
                taxonomy_data=taxonomy_context,
                config=config,
                build_info=build_info,
                data=state.data,
                authors=state.authors,
            )
            context = plugins.run_event("on_page_context", context, page=page, config=config)
            html = template.render(**context)
            html = plugins.run_event("on_post_page", html, page=page, config=config)
            _write_page(output_dir, page, html)
            rendered_html.append(html)
        except (TemplateError, ValueError) as exc:
            page_errors.append(PageError(file_path=str(page.source_path), message=str(exc)))

    if page_errors:
        _fail_build(page_errors, plugins)

    not_found_html = _render_404(
        env=env,
        config=config,
        nav=state.nav.items,
        all_pages=state.all_pages,
        taxonomy_data=taxonomy_context,
        build_info=build_info,
        data=state.data,
        authors=state.authors,
        project_dir=state.project_dir,
    )
    (output_dir / "404.html").write_text(not_found_html, encoding="utf-8")
    rendered_html.append(not_found_html)
    return rendered_html


def _emit_outputs(state: _BuildState, rendered_html: list[str]) -> None:
    """Phase 4: copy assets and write search, feeds, sitemap, robots, AI surfaces.

    Everything written here lands in the temp output dir; the swap into the
    final location happens later in :func:`_finish_build`.

    :raises BuildError: When two pages share a source directory that holds a
        co-located asset (see :class:`bartleby.assets.AssetCollisionError`).
    """
    config = state.config
    assert state.output_dir is not None
    output_dir = state.output_dir
    project_dir = state.project_dir

    theme_static = get_theme_templates_dir().parent / "static"
    static_file_count = copy_static_files(theme_static, output_dir)
    static_file_count += copy_static_files(project_dir / "static", output_dir)
    _apply_compiled_theme_css(project_dir, output_dir)
    try:
        static_file_count += copy_colocated_assets(
            state.assets, state.pages, state.content_dir, output_dir
        )
    except AssetCollisionError as exc:
        raise BuildError(
            [
                PageError(
                    file_path=page_path,
                    message=(
                        f"co-located asset in shared directory {exc.directory!r} cannot "
                        "be assigned to one page; split it into one bundle directory per page"
                    ),
                )
                for page_path in exc.page_paths
            ]
        ) from exc
    icon_packs = {
        **DEFAULT_ICON_PACKS,
        **{pack: bool(value) for pack, value in config.theme.icon_packs.items()},
    }
    tree_shake_icons(
        rendered_html + _template_sources(project_dir),
        icon_packs,
        output_dir,
    )
    write_search_index(build_search_index(state.pages, config), output_dir)
    generate_feeds(state.pages, config, output_dir)
    if config.ai.markdown_variants:
        for page in state.pages:
            if not page.draft and page.raw_content:
                write_markdown_variant(page, output_dir)
    if config.ai.llms_txt:
        (output_dir / "llms.txt").write_text(
            generate_llms_txt(state.pages, config), encoding="utf-8"
        )
    if config.ai.llms_full_txt:
        (output_dir / "llms-full.txt").write_text(
            generate_llms_full_txt(state.pages, config), encoding="utf-8"
        )
    write_sitemap(state.all_pages, config.site, output_dir)
    if config.ai.agent_surface:
        write_agent_surface(state.pages, config, state.authors, output_dir)
    static_robots_exists = (project_dir / "static" / "robots.txt").exists()
    write_robots_txt(
        config.site, config.ai, output_dir, static_override_exists=static_robots_exists
    )
    state.static_file_count = static_file_count


def _finish_build(
    state: _BuildState, *, started: float, dry_run: bool
) -> BuildResult | DryRunResult:
    """Phase 5: swap the temp output into place (or diff it) and fire shutdown hooks.

    On ``dry_run`` the temp tree is diffed against the existing output and
    discarded; otherwise it atomically replaces the previous output directory.
    Either path fires ``on_post_build`` and ``on_shutdown`` before returning.
    """
    plugins = state.plugins
    config = state.config
    assert state.output_dir is not None
    assert state.final_output_dir is not None
    build_dir = state.output_dir
    final_output_dir = state.final_output_dir

    if dry_run:
        diff = _diff_output_trees(build_dir, final_output_dir)
        shutil.rmtree(build_dir, ignore_errors=True)
        plugins.run_event("on_post_build", config)
        plugins.run_lifecycle("on_shutdown")
        return diff

    _swap_output_into_place(build_dir, final_output_dir)
    plugins.run_event("on_post_build", config)
    plugins.run_lifecycle("on_shutdown")

    duration = time.perf_counter() - started
    return BuildResult(
        page_count=len(state.all_pages),
        duration_seconds=duration,
        static_file_count=state.static_file_count,
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


def _fail_build(page_errors: list[PageError], plugins: PluginCollection) -> NoReturn:
    """Fire ``on_build_error`` once and raise, discarding the partial build.

    The hook receives the assembled :class:`BuildError` so a plugin can inspect
    every collected :class:`PageError` in a single call. This function does not
    remove the temp build directory itself; :func:`build`'s ``finally`` block
    is the single removal site and cleans it up once this raise propagates out
    of it, so a failed build never leaves output behind.

    :param page_errors: Every page-level failure collected during the pass.
    :param plugins: The active plugin collection to dispatch the hook through.
    :raises BuildError: Always, carrying ``page_errors``.
    """
    error = BuildError(page_errors)
    plugins.run_event("on_build_error", error)
    plugins.run_lifecycle("on_shutdown")
    raise error


def _template_type_for(page: Page, content_type: object) -> str:
    """Pick the template type bucket — taxonomy and listing pages bypass post/page logic."""
    taxonomy_kind = page.custom_metadata.get(TAXONOMY_KIND_KEY)
    if taxonomy_kind == TaxonomyKind.TERM:
        return "taxonomy"
    if taxonomy_kind == TaxonomyKind.INDEX:
        return "taxonomy_index"
    if page.custom_metadata.get(LISTING_KIND_KEY) == ListingKind.CONTENT_TYPE:
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
    sources: list[str] = []
    template_roots = [get_theme_templates_dir(), project_dir / "templates"]
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

    result = await asyncio.to_thread(
        build, config_path, include_drafts=include_drafts, strict=strict
    )
    # async_build never requests a dry run, so the result is always a BuildResult.
    assert isinstance(result, BuildResult)
    return result


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


def build_dry_run(
    config_path: Path, *, include_drafts: bool = False, strict: bool = False
) -> DryRunResult:
    """Run the build pipeline in dry-run mode and return what would change.

    Convenience wrapper around :func:`build` with ``dry_run=True``; the return
    type is narrowed to :class:`DryRunResult` for callers that only want a diff.

    :param config_path: Path to ``bartleby.yml``.
    :param include_drafts: Forwarded to :func:`build`.
    :param strict: Forwarded to :func:`build`.
    :returns: The :class:`DryRunResult` describing added/modified/unchanged/deleted output.
    """
    result = build(config_path, include_drafts=include_drafts, strict=strict, dry_run=True)
    assert isinstance(result, DryRunResult)
    return result


def _diff_output_trees(new_dir: Path, current_dir: Path) -> DryRunResult:
    """Compare a freshly rendered output tree against the existing ``site/``.

    Files are compared by relative path and byte content. A path present only in
    the new tree is *added*; present in both with differing bytes is *modified*;
    identical in both is *unchanged*; present only in the current tree is *deleted*.

    :param new_dir: The freshly rendered (temp) output tree.
    :param current_dir: The existing ``site/`` directory (may not exist).
    :returns: A :class:`DryRunResult` with sorted path lists.
    """
    new_files = _relative_files(new_dir)
    current_files = _relative_files(current_dir) if current_dir.exists() else set()

    added: list[str] = []
    modified: list[str] = []
    unchanged: list[str] = []
    for relative in sorted(new_files):
        display = f"{current_dir.name}/{relative}"
        if relative not in current_files:
            added.append(display)
        elif (new_dir / relative).read_bytes() == (current_dir / relative).read_bytes():
            unchanged.append(display)
        else:
            modified.append(display)
    deleted = sorted(f"{current_dir.name}/{relative}" for relative in current_files - new_files)
    return DryRunResult(added=added, modified=modified, unchanged=unchanged, deleted=deleted)


def _relative_files(root: Path) -> set[str]:
    """Return every file under ``root`` as a POSIX path relative to ``root``."""
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


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
