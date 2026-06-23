# ABOUTME: Jinja2 template environment, lookup cascade, and context building.
# Implements the 6-level template lookup, data loading, and per-page context dicts.

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import jinja2
import yaml

from bartleby.seo import generate_all_meta_tags
from bartleby.theme import get_theme_templates_dir

if TYPE_CHECKING:
    import datetime
    from pathlib import Path

    from bartleby.authors import Author
    from bartleby.config import BartlebyConfig, SiteConfig
    from bartleby.content import Page


@dataclass(slots=True)
class BuildInfo:
    """Build-level metadata exposed to every template under ``build``."""

    date: datetime.date
    bartleby_version: str


def create_jinja_env(config: BartlebyConfig, project_dir: Path) -> jinja2.Environment:
    """Build the project's Jinja2 environment with the 6-level search cascade.

    :param config: Parsed Bartleby config.
    :param project_dir: Directory containing the user's site (where
        ``overrides/``, ``templates/``, ``partials/``, ``shortcodes/``, and
        ``data/`` live).
    :returns: A configured :class:`jinja2.Environment` with autoescaping on
        for ``.html`` files.
    """
    search_paths: list[str] = [
        str(project_dir / "overrides"),
        str(project_dir / "templates"),
        str(project_dir),
        str(get_theme_templates_dir()),
    ]
    loader = jinja2.FileSystemLoader(search_paths)
    return jinja2.Environment(
        loader=loader,
        autoescape=jinja2.select_autoescape(["html", "htm", "xml"]),
        keep_trailing_newline=True,
    )


def resolve_template_name(page: Page, template_type: str, project_dir: Path) -> str:
    """Return the template name to render for ``page``.

    Implements the 6-level lookup cascade documented in spec.md:

    1. Page front matter ``template`` override
    2. ``overrides/{template_name}`` at project root
    3. ``templates/{content_type}/{template_type}.html``
    4. ``templates/{content_type}/base.html``
    5. ``templates/defaults/{template_type}.html``
    6. Built-in theme fallback (``{template_type}.html`` or ``page.html``)

    :param page: The page being rendered.
    :param template_type: One of ``"post"``, ``"list"``, ``"page"``,
        ``"taxonomy"``, ``"taxonomy_index"``.
    :param project_dir: The user's project directory.
    :returns: A template name resolvable by the Jinja2 environment.
    """
    if page.template_override:
        return page.template_override

    candidates: list[str] = []
    content_type = page.content_type_name
    if template_type == "taxonomy" and content_type:
        taxonomy_name = page.custom_metadata.get("taxonomy_name")
        if isinstance(taxonomy_name, str):
            candidates.append(f"{content_type}/taxonomy/{taxonomy_name}.html")
        candidates.append(f"{content_type}/taxonomy.html")
    if content_type:
        candidates.append(f"{content_type}/{template_type}.html")
        candidates.append(f"{content_type}/base.html")
    candidates.append(f"defaults/{template_type}.html")
    candidates.append(f"{template_type}.html")
    if template_type != "page":
        candidates.append("page.html")

    overrides_dir = project_dir / "overrides"
    templates_dir = project_dir / "templates"
    theme_dir = get_theme_templates_dir()

    for candidate in candidates:
        if (overrides_dir / candidate).exists():
            return candidate
        if (templates_dir / candidate).exists():
            return candidate
        if (theme_dir / candidate).exists():
            return candidate
    # Fall through to the very last candidate name — Jinja2 will surface the
    # missing-template error if it really isn't anywhere on the search path.
    return candidates[-1]


def load_data_files(project_dir: Path) -> dict[str, object]:
    """Load every YAML/TOML file under ``project_dir/data/`` keyed by stem.

    :param project_dir: The user's project directory.
    :returns: Mapping of file stem to parsed file contents. Returns ``{}``
        when the ``data/`` directory does not exist.
    """
    data_dir = project_dir / "data"
    if not data_dir.exists():
        return {}

    result: dict[str, object] = {}
    for path in sorted(data_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix in {".yaml", ".yml"}:
            parsed: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
            result[path.stem] = parsed
        elif path.suffix == ".toml":
            with path.open("rb") as handle:
                result[path.stem] = tomllib.load(handle)
    return result


def build_page_context(
    *,
    page: Page,
    site_config: SiteConfig,
    nav: list[Any],
    all_pages: list[Page],
    taxonomy_data: dict[str, Any],
    config: BartlebyConfig,
    build_info: BuildInfo,
    data: dict[str, object],
    authors: dict[str, Author] | None = None,
) -> dict[str, object]:
    """Build the template context dict for one page.

    :param authors: Optional mapping of author key to :class:`Author` object,
        used to resolve ``page.author_keys`` into rich objects with ``name``,
        ``url``, ``avatar``, etc. for templates. Keys with no matching entry
        are exposed as the raw key string.
    :returns: Mapping with the standard Bartleby context keys: ``site``,
        ``page``, ``nav``, ``pages``, ``taxonomies``, ``config``, ``build``,
        ``data``, ``extra_css``, ``extra_js``, ``seo``. The ``page`` value is
        the :class:`Page` dataclass itself, so every page attribute is reachable
        in templates without this builder enumerating it.
    """
    page.authors = _resolve_author_objects(page.author_keys, authors or {})
    return {
        "site": _site_namespace(site_config),
        "page": page,
        "nav": nav,
        "pages": all_pages,
        "taxonomies": taxonomy_data,
        "config": config,
        "build": {
            "date": build_info.date,
            "bartleby_version": build_info.bartleby_version,
        },
        "data": data,
        "extra_css": list(config.extra_css),
        "extra_js": list(config.extra_js),
        "seo": generate_all_meta_tags(page, site_config),
    }


def _site_namespace(site_config: SiteConfig) -> dict[str, object]:
    """Expose :class:`SiteConfig` as a plain dict for templates."""
    return {
        "title": site_config.title,
        "url": site_config.url,
        "description": site_config.description,
        "author": site_config.author,
        "default_image": site_config.default_image,
        "twitter": site_config.twitter,
    }


def _resolve_author_objects(
    author_keys: list[str], authors: dict[str, Author]
) -> list[Author | str]:
    """Map ``author_keys`` to :class:`Author` objects, falling back to the key itself.

    Returning the bare key string for unknown authors keeps the build going —
    metadata validation is the right place to fail on unknown keys, not here.
    """
    resolved: list[Author | str] = []
    for key in author_keys:
        author = authors.get(key)
        resolved.append(author if author is not None else key)
    return resolved
