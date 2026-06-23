# ABOUTME: Tests for Jinja2 template environment, lookup cascade, and context building.
# Covers the 6-level template lookup, data files, partials, and extra_css/js plumbing.

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from bartleby.authors import Author
from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    ContentTypeConfig,
    DevServerConfig,
    PaginationConfig,
    SiteConfig,
    TaxonomyConfig,
    ThemeConfig,
)
from bartleby.content import Page
from bartleby.templates import (
    BuildInfo,
    build_page_context,
    create_jinja_env,
    load_data_files,
    make_feature_checker,
    resolve_template_name,
)

FIXTURE_TEMPLATES = Path(__file__).parent / "fixtures" / "templates"
FIXTURE_OVERRIDES_SITE = Path(__file__).parent / "fixtures" / "site_with_overrides"
FIXTURE_PARTIALS_SITE = Path(__file__).parent / "fixtures" / "site_with_partials"
FIXTURE_DATA_SITE = Path(__file__).parent / "fixtures" / "site_with_data"


def _empty_config(
    *, extra_css: list[str] | None = None, extra_js: list[str] | None = None
) -> BartlebyConfig:
    return BartlebyConfig(
        site=SiteConfig(title="t", url="https://example.com"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={
            "blog": ContentTypeConfig(
                name="blog", path="blog/posts", pagination=PaginationConfig()
            ),
        },
        taxonomies={"tags": TaxonomyConfig(name="tags", slug_format="{slug}")},
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=extra_css or [],
        extra_js=extra_js or [],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp"),
    )


def _page(
    *,
    source: str = "blog/posts/post.md",
    title: str = "Sample",
    content_type_name: str | None = "blog",
    template_override: str | None = None,
) -> Page:
    return Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        template_override=template_override,
        content_type_name=content_type_name,
    )


def test_theme_fallback_resolves(tmp_path: Path) -> None:
    """With no user templates, the built-in theme template name is returned."""
    page = _page(content_type_name=None)
    name = resolve_template_name(page, "page", tmp_path)
    env = create_jinja_env(_empty_config(), tmp_path)
    template = env.get_template(name)
    rendered = template.render(
        page={"title": "Sample", "content": "<p>hi</p>"},
        site={"title": "t"},
        build={"date": "2026-05-23", "bartleby_version": "0.1.0"},
        extra_css=[],
        extra_js=[],
    )
    assert "Sample" in rendered


def test_page_template_override(tmp_path: Path) -> None:
    """A page with ``template_override`` resolves to that template name directly."""
    page = _page(template_override="custom_override.html")
    name = resolve_template_name(page, "post", tmp_path)
    assert name == "custom_override.html"


def test_overrides_take_precedence(tmp_path: Path) -> None:
    """A template in ``overrides/`` wins over the built-in theme of the same name."""
    overrides = tmp_path / "overrides"
    overrides.mkdir()
    (overrides / "base.html").write_text("OVERRIDE:{{ page.title }}")
    env = create_jinja_env(_empty_config(), tmp_path)
    template = env.get_template("base.html")
    assert "OVERRIDE" in template.render(page={"title": "Sample"})


def test_overrides_above_templates(tmp_path: Path) -> None:
    """When both ``overrides/foo.html`` and ``templates/foo.html`` exist, overrides wins."""
    (tmp_path / "overrides").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "overrides" / "base.html").write_text("OVERRIDE:{{ page.title }}")
    (tmp_path / "templates" / "base.html").write_text("TEMPLATES:{{ page.title }}")
    env = create_jinja_env(_empty_config(), tmp_path)
    assert "OVERRIDE" in env.get_template("base.html").render(page={"title": "Sample"})


def test_content_type_template(tmp_path: Path) -> None:
    """A blog post resolves to ``blog/post.html`` when present under templates/."""
    (tmp_path / "templates" / "blog").mkdir(parents=True)
    (tmp_path / "templates" / "blog" / "post.html").write_text("BLOG_POST:{{ page.title }}")
    page = _page(content_type_name="blog")
    name = resolve_template_name(page, "post", tmp_path)
    assert name == "blog/post.html"


def test_defaults_template(tmp_path: Path) -> None:
    """A page outside any content type with a defaults template uses it."""
    (tmp_path / "templates" / "defaults").mkdir(parents=True)
    (tmp_path / "templates" / "defaults" / "page.html").write_text("DEFAULT_PAGE:{{ page.title }}")
    page = _page(content_type_name=None)
    name = resolve_template_name(page, "page", tmp_path)
    assert name == "defaults/page.html"


def test_user_overrides_theme(tmp_path: Path) -> None:
    """A user template with the same name as a theme template wins."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "page.html").write_text("USER_PAGE:{{ page.title }}")
    env = create_jinja_env(_empty_config(), tmp_path)
    assert "USER_PAGE" in env.get_template("page.html").render(page={"title": "Sample"})


def test_partials_are_resolvable(tmp_path: Path) -> None:
    """``{% include "partials/banner.html" %}`` finds files under project_dir/partials/."""
    (tmp_path / "partials").mkdir()
    (tmp_path / "partials" / "banner.html").write_text("<aside>Promo</aside>")
    env = create_jinja_env(_empty_config(), tmp_path)
    template = env.from_string("{% include 'partials/banner.html' %}")
    assert "<aside>Promo</aside>" in template.render()


def test_context_has_required_keys(tmp_path: Path) -> None:
    """``build_page_context`` returns every key the templates expect."""
    page = _page()
    page.output_url = "/blog/posts/post/"
    config = _empty_config()
    context = build_page_context(
        page=page,
        site_config=config.site,
        nav=[],
        all_pages=[page],
        taxonomy_data={},
        config=config,
        build_info=BuildInfo(date=datetime.date(2026, 5, 23), bartleby_version="0.1.0"),
        data={},
    )
    for key in ("site", "page", "nav", "pages", "taxonomies", "config", "build", "data"):
        assert key in context


def test_context_page_fields(tmp_path: Path) -> None:
    """The ``page`` object exposes the standard rendering attributes."""
    page = _page(title="Field Test")
    page.output_url = "/blog/posts/post/"
    page.date = datetime.date(2026, 4, 15)
    page.description = "desc"
    page.rendered_content = "<p>body</p>"
    page.readtime = 3
    context = build_page_context(
        page=page,
        site_config=_empty_config().site,
        nav=[],
        all_pages=[page],
        taxonomy_data={},
        config=_empty_config(),
        build_info=BuildInfo(date=datetime.date(2026, 5, 23), bartleby_version="0.1.0"),
        data={},
    )
    page_ctx = context["page"]
    assert isinstance(page_ctx, Page)
    assert page_ctx.title == "Field Test"
    assert page_ctx.content == "<p>body</p>"
    assert page_ctx.url == "/blog/posts/post/"
    assert page_ctx.readtime == 3
    assert page_ctx.date == datetime.date(2026, 4, 15)
    assert page_ctx.description == "desc"
    assert page_ctx.previous is None
    assert page_ctx.next is None
    assert page_ctx.toc == []
    assert page_ctx.authors == []


def test_context_page_is_the_dataclass() -> None:
    """``build_page_context`` exposes the Page object itself under ``page``.

    Passing the dataclass through (rather than a flattened dict) keeps the
    schema open: every Page attribute is reachable without ``build_page_context``
    having to enumerate it.
    """
    page = _page(title="Dataclass Page")
    page.output_url = "/blog/posts/post/"
    page.date = datetime.date(2026, 4, 15)
    page.description = "desc"
    page.rendered_content = "<p>body</p>"
    page.readtime = 7
    page.taxonomy_values = {"tags": ["python", "ssg"]}
    context = build_page_context(
        page=page,
        site_config=_empty_config().site,
        nav=[],
        all_pages=[page],
        taxonomy_data={},
        config=_empty_config(),
        build_info=BuildInfo(date=datetime.date(2026, 5, 23), bartleby_version="0.1.0"),
        data={},
    )
    ctx_page = context["page"]
    assert ctx_page is page
    assert isinstance(ctx_page, Page)
    # Template-facing aliases for the underlying source fields.
    assert ctx_page.content == "<p>body</p>"
    assert ctx_page.url == "/blog/posts/post/"
    assert ctx_page.taxonomies == {"tags": ["python", "ssg"]}
    # Real source attributes remain reachable too.
    assert ctx_page.title == "Dataclass Page"
    assert ctx_page.date == datetime.date(2026, 4, 15)
    assert ctx_page.description == "desc"
    assert ctx_page.readtime == 7
    assert ctx_page.custom_metadata == {}


def test_context_new_page_field_reachable_without_editing_builder() -> None:
    """A value set on the Page renders without ``build_page_context`` knowing it.

    This is the whole point of passing the dataclass: a template author who adds
    a custom_metadata field reaches it in the template with no builder change.
    """
    page = _page()
    page.custom_metadata = {"hero_image": "/img/hero.png"}
    context = build_page_context(
        page=page,
        site_config=_empty_config().site,
        nav=[],
        all_pages=[page],
        taxonomy_data={},
        config=_empty_config(),
        build_info=BuildInfo(date=datetime.date(2026, 5, 23), bartleby_version="0.1.0"),
        data={},
    )
    env = create_jinja_env(_empty_config(), Path("/nonexistent-project"))
    template = env.from_string("{{ page.custom_metadata.hero_image }}")
    assert template.render(**context) == "/img/hero.png"


def test_context_authors_resolve_to_author_objects() -> None:
    """``page.authors`` carries resolved :class:`Author` objects, not raw keys."""
    page = _page()
    page.author_keys = ["mason", "ghost"]
    authors = {
        "mason": Author(
            key="mason",
            name="Mason Egger",
            description=None,
            avatar=None,
            url="https://masonegger.com",
        )
    }
    context = build_page_context(
        page=page,
        site_config=_empty_config().site,
        nav=[],
        all_pages=[page],
        taxonomy_data={},
        config=_empty_config(),
        build_info=BuildInfo(date=datetime.date(2026, 5, 23), bartleby_version="0.1.0"),
        data={},
        authors=authors,
    )
    ctx_page = context["page"]
    assert isinstance(ctx_page, Page)
    resolved = ctx_page.authors
    assert isinstance(resolved[0], Author)
    assert resolved[0].name == "Mason Egger"
    # Unknown keys fall back to the bare string so the build keeps going.
    assert resolved[1] == "ghost"


def test_context_build_metadata() -> None:
    """The ``build`` namespace carries date and bartleby_version."""
    page = _page()
    context = build_page_context(
        page=page,
        site_config=_empty_config().site,
        nav=[],
        all_pages=[page],
        taxonomy_data={},
        config=_empty_config(),
        build_info=BuildInfo(date=datetime.date(2026, 5, 23), bartleby_version="0.1.0"),
        data={},
    )
    build_ctx = context["build"]
    assert isinstance(build_ctx, dict)
    assert build_ctx["date"] == datetime.date(2026, 5, 23)
    assert build_ctx["bartleby_version"] == "0.1.0"


def test_context_data_loaded() -> None:
    """``load_data_files`` reads YAML and TOML files under data/ keyed by stem."""
    data = load_data_files(FIXTURE_DATA_SITE)
    schedule = data["schedule"]
    contacts = data["contacts"]
    assert isinstance(schedule, dict)
    assert schedule["days"] == ["Friday", "Saturday"]
    assert isinstance(contacts, dict)
    primary = contacts["primary"]
    assert isinstance(primary, dict)
    assert primary["name"] == "Mason"


def test_data_missing_directory_is_ok(tmp_path: Path) -> None:
    """A site without a data/ directory loads to an empty namespace."""
    assert load_data_files(tmp_path) == {}


def test_taxonomy_template_lookup(tmp_path: Path) -> None:
    """Taxonomy pages look for ``{content_type}/taxonomy/{name}.html`` first."""
    (tmp_path / "templates" / "blog" / "taxonomy").mkdir(parents=True)
    (tmp_path / "templates" / "blog" / "taxonomy" / "tags.html").write_text("TAG_TPL")
    page = _page(content_type_name="blog")
    page.custom_metadata = {"taxonomy_name": "tags"}
    name = resolve_template_name(page, "taxonomy", tmp_path)
    assert name == "blog/taxonomy/tags.html"


def test_jinja_env_has_correct_search_paths(tmp_path: Path) -> None:
    """Search paths are overrides → templates → project_dir → theme, in order."""
    env = create_jinja_env(_empty_config(), tmp_path)
    loader = env.loader
    assert loader is not None
    paths = getattr(loader, "searchpath", [])
    assert paths[0].endswith("overrides")
    assert paths[1].endswith("templates")
    assert paths[2] == str(tmp_path)
    assert paths[3].endswith("theme/templates")


def test_extra_css_paths_in_context(tmp_path: Path) -> None:
    """``extra_css`` lists from config surface in the build context."""
    page = _page()
    context = build_page_context(
        page=page,
        site_config=_empty_config(extra_css=["extra.css"]).site,
        nav=[],
        all_pages=[page],
        taxonomy_data={},
        config=_empty_config(extra_css=["extra.css"]),
        build_info=BuildInfo(date=datetime.date(2026, 5, 23), bartleby_version="0.1.0"),
        data={},
    )
    assert context["extra_css"] == ["extra.css"]


def test_extra_js_paths_in_context() -> None:
    """``extra_js`` lists from config surface in the build context."""
    page = _page()
    context = build_page_context(
        page=page,
        site_config=_empty_config(extra_js=["js/site.js"]).site,
        nav=[],
        all_pages=[page],
        taxonomy_data={},
        config=_empty_config(extra_js=["js/site.js"]),
        build_info=BuildInfo(date=datetime.date(2026, 5, 23), bartleby_version="0.1.0"),
        data={},
    )
    assert context["extra_js"] == ["js/site.js"]


def test_built_in_theme_base_renders_seo_meta() -> None:
    """The built-in base.html includes Open Graph and Twitter Card meta tags."""
    env = create_jinja_env(_empty_config(), Path("/nonexistent-project"))
    base = env.get_template("base.html")
    rendered = base.render(
        page={
            "title": "Hello",
            "description": "Page desc",
            "url": "/blog/post/",
            "content": "<p>body</p>",
        },
        site={"title": "Site", "url": "https://example.com", "description": "Site desc"},
        build={"date": "2026-05-23", "bartleby_version": "0.1.0"},
        extra_css=[],
        extra_js=[],
        nav=[],
        pages=[],
    )
    assert 'property="og:title"' in rendered
    assert 'name="twitter:card"' in rendered
    assert "application/ld+json" in rendered


def test_feature_checker_reports_enabled_and_disabled() -> None:
    """``make_feature_checker`` returns True only for enabled feature names."""
    feature = make_feature_checker(["search", "navigation.top"])
    assert feature("search") is True
    assert feature("navigation.top") is True
    assert feature("content.code.copy") is False


def test_create_jinja_env_registers_feature_global(tmp_path: Path) -> None:
    """The env exposes a ``feature`` global backed by the config's feature list."""
    config = _empty_config()
    config.theme.features = ["search"]
    env = create_jinja_env(config, tmp_path)
    checker = env.globals["feature"]
    assert checker("search") is True
    assert checker("content.code.copy") is False


pytest.importorskip("jinja2")
