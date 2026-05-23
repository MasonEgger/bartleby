# ABOUTME: Build pipeline orchestrator wiring all components together.
# Loads config, discovers content, renders, and writes the site/ output.

from __future__ import annotations

import datetime
import re
import shutil
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

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
from bartleby.shortcodes import process_shortcodes
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
    from pathlib import Path

    from bartleby.content import Page


@dataclass(slots=True)
class BuildResult:
    """Summary returned from :func:`build`."""

    page_count: int
    duration_seconds: float


_WORDS_PER_MINUTE = 265
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def build(config_path: Path, *, include_drafts: bool = False) -> BuildResult:
    """Run the full Bartleby build pipeline against ``config_path``.

    :param config_path: Path to ``bartleby.yml``.
    :param include_drafts: When ``True``, draft pages are written to the
        output. Defaults to ``False`` for production builds.
    :returns: A :class:`BuildResult` carrying the page count and wall time.
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
    pages = list(plugins.run_event("on_pages", pages, config=config))

    if not include_drafts:
        pages = [page for page in pages if not page.draft]

    errors = validate_all_metadata(pages, config, authors)
    if errors:
        message = "\n".join(f"  {error.file_path}: {error.message}" for error in errors)
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

    output_dir = project_dir / "site"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for page in all_pages:
        source = process_shortcodes(page.raw_content, {"build": build_info, "page": page}, env)
        source = plugins.run_event("on_page_markdown", source, page=page, config=config)
        rendered = render_markdown(source, md_renderer)
        page.rendered_content = rendered.html

        content_type = (
            config.content_types.get(page.content_type_name) if page.content_type_name else None
        )
        if content_type is not None and content_type.readtime and page.raw_content:
            page.readtime = calculate_readtime(page.raw_content)
        if content_type is not None and content_type.excerpt_separator and page.raw_content:
            page.excerpt = extract_excerpt(page.raw_content, content_type.excerpt_separator)

    # Cross-reference resolution needs every page rendered before any rewriting,
    # so it lives outside the render loop above and below the template render below.
    resolve_all_crossrefs(all_pages, content_dir)

    for page in all_pages:
        content_type = (
            config.content_types.get(page.content_type_name) if page.content_type_name else None
        )
        template_type = _template_type_for(page, content_type)
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
        )
        html = template.render(**context)
        html = plugins.run_event("on_post_page", html, page=page, config=config)
        _write_page(output_dir, page, html)

    from bartleby.theme import get_theme_templates_dir as _theme_dir

    theme_static = _theme_dir().parent / "static"
    copy_static_files(theme_static, output_dir)
    copy_static_files(project_dir / "static", output_dir)
    copy_colocated_assets(assets, pages, content_dir, output_dir)
    tree_shake_icons(
        [page.rendered_content for page in pages if page.rendered_content],
        {pack: bool(value) for pack, value in config.theme.icon_packs.items()}
        or {"material": True, "fontawesome": True, "octicons": True, "simple": True},
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
    write_sitemap(pages, config.site, output_dir)
    static_robots_exists = (project_dir / "static" / "robots.txt").exists()
    write_robots_txt(
        config.site, config.ai, output_dir, static_override_exists=static_robots_exists
    )

    duration = time.perf_counter() - started
    return BuildResult(page_count=len(all_pages), duration_seconds=duration)


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


def _write_page(output_dir: Path, page: Page, html: str) -> None:
    """Write the rendered HTML for ``page`` to its output URL location."""
    url = page.output_url.strip("/")
    destination = output_dir / "index.html" if not url else output_dir / url / "index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
