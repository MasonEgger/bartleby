# Bartleby Implementation Plan

## Current Status

**Step 0 of 36 complete.** Project is greenfield — `spec.md` is finalized, no code written.

## Implementation Guidelines

- **TDD**: RED (failing tests) → GREEN (minimal code to pass) → REFACTOR
- Each step ends with `just check` passing (lint + typecheck + tests)
- All code uses strict type hints (mypy strict, no `Any`)
- Every `.py` file starts with a 2-line comment: first line prefixed `ABOUTME: `
- Test application logic, not library behavior
- Build on previous steps — no orphaned code
- Refer to `spec.md` as the canonical source of truth for all behavior

## Architecture Overview

```
src/bartleby/
├── __init__.py              # Version
├── __main__.py              # Entry point
├── cli.py                   # CLI commands (argparse)
├── output.py                # Structured output formatting (text/JSON)
├── config.py                # Config loading and validation
├── authors.py               # Author loading and resolution
├── content.py               # Content discovery and front matter
├── content_query.py         # Content listing, filtering, sorting
├── metadata.py              # Build-time metadata validation
├── urls.py                  # URL generation
├── crossrefs.py             # Cross-reference resolution
├── markdown_pipeline.py     # Markdown rendering pipeline
├── shortcodes.py            # Shortcode preprocessing
├── templates.py             # Template system (Jinja2)
├── navigation.py            # Navigation building
├── taxonomies.py            # Taxonomy system
├── listings.py              # Listing page generation
├── pagination.py            # Pagination
├── search.py                # Search index generation
├── feeds.py                 # RSS/Atom feed generation
├── sitemap.py               # Sitemap and robots.txt
├── seo.py                   # SEO meta tags
├── llm.py                   # LLM output (llms.txt, etc.)
├── icons.py                 # Icon packs and tree-shaking
├── plugins.py               # Plugin system
├── skills.py                # Agent skill generation and content analysis
├── linting.py               # Content quality checks (broken links, orphans, etc.)
├── schema_introspection.py  # Schema export for agent self-discovery
├── export.py                # JSONL/JSON/CSV content export
├── build.py                 # Build pipeline orchestration
├── server.py                # Dev server
├── py.typed                 # PEP 561 marker
└── theme/                   # Built-in Material theme
    ├── __init__.py
    ├── templates/
    │   ├── base.html
    │   ├── page.html
    │   ├── defaults/
    │   │   ├── post.html
    │   │   └── list.html
    │   └── partials/
    └── static/
        ├── css/
        └── js/

tests/
├── conftest.py              # Shared fixtures
├── test_config.py
├── test_authors.py
├── test_output.py
├── test_content_query.py
├── test_schema_introspection.py
├── test_linting.py
├── test_skills.py
├── test_export.py
├── ...
└── fixtures/
    ├── configs/
    ├── content/
    └── templates/
```

---

## Phase 1: Foundation

### Step 1: Project Scaffolding

**Context**: Greenfield project. Only `spec.md`, `CLAUDE.md`, and `.gitignore` exist. No Python code, no `pyproject.toml`, no package structure.

**Goal**: Set up the Python package infrastructure so that `uv sync`, `uv run pytest`, `uv run ruff check .`, and `uv run mypy src/` all work. No application logic yet.

```text
You are building Bartleby, a Python static site generator. The full spec is in spec.md.
This is Step 1: project scaffolding. No application code exists yet.

1. Create pyproject.toml:
   - Project name: bartleby, version 0.1.0
   - Python requires: ">=3.14"
   - Build system: hatchling (use [build-system] requires = ["hatchling"], build-backend = "hatchling.build")
   - Entry point script: bartleby = "bartleby.cli:main"
   - Core dependencies:
     - markdown>=3.4
     - pymdown-extensions>=10.0
     - do-markdown>=0.1.0
     - jinja2>=3.1
     - pyyaml>=6.0
     - pygments>=2.17
     - watchdog>=4.0
     - websockets>=12.0
     - python-slugify>=8.0
     - aiofiles>=23.0
   - Dev dependency group [project.optional-dependencies] dev:
     - pytest>=8.0
     - ruff>=0.8
     - mypy>=1.13
     - types-pyyaml
     - types-markdown
     - types-pygments
     - types-aiofiles
   - [tool.ruff]: line-length = 99, target-version = "py314"
   - [tool.ruff.lint]: select = ["E", "F", "W", "I", "UP", "B", "SIM", "TCH"]
   - [tool.ruff.lint.isort]: known-first-party = ["bartleby"]
   - [tool.mypy]: strict = true, python_version = "3.14", warn_return_any = true, disallow_any_generics = true
   - [tool.pytest.ini_options]: testpaths = ["tests"], pythonpath = ["src"]
   - [tool.hatch.build.targets.wheel]: packages = ["src/bartleby"]

2. Create package structure (all files need ABOUTME comments):
   - src/bartleby/__init__.py:
     - ABOUTME: Root package for Bartleby static site generator.
     - Contains: __version__ = "0.1.0"
   - src/bartleby/py.typed (empty file, PEP 561 marker)
   - tests/__init__.py (empty)
   - tests/conftest.py:
     - ABOUTME: Shared test fixtures for Bartleby test suite.
     - Empty for now, will be populated as components are built
   - tests/fixtures/ directory — create a .gitkeep file inside

3. Create Justfile:
   - default target: check
   - check: lint typecheck test
   - lint: uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/
   - typecheck: uv run mypy src/
   - test: uv run pytest
   - format: uv run ruff format src/ tests/

4. Update .gitignore to include:
   - __pycache__/
   - *.pyc
   - .mypy_cache/
   - .pytest_cache/
   - .ruff_cache/
   - dist/
   - *.egg-info/
   - site/
   - .venv/
   - (keep existing entries)

5. RED: Write smoke tests:
   - Create tests/test_init.py:
     - ABOUTME: Smoke tests verifying the bartleby package is importable.
     - test_version_is_string: import bartleby, assert isinstance(bartleby.__version__, str)
     - test_version_not_empty: assert len(bartleby.__version__) > 0

6. GREEN: The package structure from step 2 should make these pass.

7. Run `uv sync --dev` to install dependencies, then `just check` to verify everything passes.
```

---

### Step 2: Configuration System

**Context**: Step 1 complete — package scaffolding, pyproject.toml, Justfile all working. No application logic yet.

**Goal**: Load `bartleby.yml`, validate it, and return typed dataclass objects. This is the foundation everything else builds on.

```text
Step 2: Configuration System. Step 1 is complete (project scaffolding).

Refer to spec.md "Configuration" section for the full schema.
The config file is bartleby.yml. Key sections: site, nav, theme, authors_file,
content_types, taxonomies, exclude_patterns, markdown_extensions, plugins, ai, dev_server.

1. RED: Write config loading and validation tests:
   - Create tests/fixtures/configs/minimal.yml:
     ```yaml
     site:
       title: "Test Site"
       url: "https://example.com"
     ```
   - Create tests/fixtures/configs/full.yml with ALL config options from spec.md
     (site, nav, theme with palette/color_mode/features/icon_packs/logo/favicon/font,
      authors_file, content_types with blog and tutorials including pagination/taxonomies/
      feeds/readtime/excerpt_separator/metadata, taxonomies with tags and categories,
      exclude_patterns, markdown_extensions, plugins, ai, dev_server)
   - Create tests/fixtures/configs/invalid_missing_title.yml (site without title)
   - Create tests/fixtures/configs/invalid_missing_url.yml (site without url)
   - Create tests/fixtures/configs/invalid_taxonomy_ref.yml
     (content type references taxonomy "series" not defined in taxonomies section)

   - Create tests/test_config.py:
     - ABOUTME: Tests for bartleby.yml configuration loading and validation.
     - test_load_minimal_config: loads minimal.yml, verifies site.title == "Test Site"
       and site.url == "https://example.com"
     - test_load_full_config: loads full.yml, verifies all sections populated
       (spot-check: content_types has "blog" key, taxonomies has "tags",
        theme.features is a list, ai.llms_txt is True)
     - test_missing_site_title_raises: loading invalid_missing_title.yml raises ConfigError
       with "site.title" in the message
     - test_missing_site_url_raises: loading invalid_missing_url.yml raises ConfigError
       with "site.url" in the message
     - test_undefined_taxonomy_reference_raises: loading invalid_taxonomy_ref.yml raises
       ConfigError mentioning the undefined taxonomy name
     - test_default_values_applied: load minimal.yml (no explicit defaults), verify:
       - config.authors_file == ".authors.yml"
       - config.exclude_patterns contains "_drafts/**"
       - config.dev_server.host == "127.0.0.1"
       - config.dev_server.port == 8000
       - config.ai.llms_txt is True
       - config.ai.markdown_variants is True
     - test_content_type_pagination_defaults: content type without explicit pagination
       gets enabled=False
     - test_content_type_with_metadata_schema: verify metadata field schemas parsed
       (type, required, choices)
     - test_config_file_not_found: raises FileNotFoundError
     - test_empty_config_file: raises ConfigError

2. GREEN: Create src/bartleby/config.py:
   - ABOUTME: Configuration loading and validation for bartleby.yml.
   - ConfigError(Exception) with message: str and key_path: str | None fields
   - Dataclasses (use @dataclass with slots=True where practical):
     - SiteConfig: title (str), url (str), description (str, default ""),
       author (str, default ""), default_image (str | None), twitter (str | None)
     - PaginationConfig: enabled (bool, default False), per_page (int, default 10),
       url_format (str, default "page/{page}")
     - MetadataFieldSchema: field_type (str), required (bool, default False),
       choices (list[str] | None, default None)
     - ContentTypeConfig: name (str), path (str), url_base (str | None),
       url_format (str | None), pagination (PaginationConfig),
       taxonomies (list[str]), feeds (list[str]), readtime (bool, default False),
       excerpt_separator (str | None), metadata (dict[str, MetadataFieldSchema])
     - TaxonomyConfig: name (str), slug_format (str)
     - ThemeConfig: palette (dict[str, str]), color_mode (dict[str, str | bool]),
       features (list[str]), icon_packs (dict[str, bool]),
       logo (str | None), favicon (str | None), font (dict[str, str])
     - AIConfig: llms_txt (bool, default True), llms_full_txt (bool, default True),
       markdown_variants (bool, default True),
       robots (dict[str, list[str]], default empty)
     - DevServerConfig: host (str, default "127.0.0.1"), port (int, default 8000)
     - BartlebyConfig: site (SiteConfig), nav (list[dict[str, str]] | None),
       theme (ThemeConfig), authors_file (str, default ".authors.yml"),
       content_types (dict[str, ContentTypeConfig]),
       taxonomies (dict[str, TaxonomyConfig]),
       exclude_patterns (list[str]), markdown_extensions (list[dict[str, object] | str]),
       plugins (list[str]), ai (AIConfig), dev_server (DevServerConfig),
       config_dir (Path — directory containing bartleby.yml)
   - load_config(config_path: Path) -> BartlebyConfig:
     - Read YAML file
     - Call _parse_config to convert raw dict to dataclasses
     - Call _validate_config to check cross-references
     - Return BartlebyConfig
   - _parse_config(raw: dict, config_dir: Path) -> BartlebyConfig:
     - Convert nested dicts to typed dataclasses
     - Apply defaults for missing optional sections
   - _validate_config(config: BartlebyConfig) -> None:
     - Check required fields present
     - Check taxonomy references valid
     - Raise ConfigError with clear messages

3. REFACTOR: Ensure all validation errors include the key path
   (e.g., "content_types.blog.taxonomies: references undefined taxonomy 'series'")

4. Verify: `just check` passes.
```

---

### Step 3: Authors System

**Context**: Steps 1-2 complete. Config system loads and validates `bartleby.yml`. The config includes `authors_file` path (default `.authors.yml`).

**Goal**: Load author definitions from `.authors.yml`, validate structure, and resolve author keys referenced in content front matter.

```text
Step 3: Authors System. Steps 1-2 complete (project scaffolding, config system).

Refer to spec.md "Authors" section. Authors are defined in .authors.yml (path
configurable via config.authors_file). Content references authors by key.

1. RED: Write author tests:
   - Create tests/fixtures/authors/valid.yml:
     ```yaml
     authors:
       mason:
         name: Mason Egger
         description: "Developer Advocate & Python enthusiast"
         avatar: https://example.com/avatar.jpg
         url: https://masonegger.com
       guest:
         name: Guest Author
         description: "Community contributor"
     ```
   - Create tests/fixtures/authors/minimal.yml:
     ```yaml
     authors:
       solo:
         name: Solo Author
     ```

   - Create tests/test_authors.py:
     - ABOUTME: Tests for author loading, validation, and resolution.
     - test_load_valid_authors: loads valid.yml, returns dict with "mason" and "guest" keys,
       mason.name == "Mason Egger", mason.avatar is set, guest.url is None
     - test_load_minimal_author: loads minimal.yml, solo.name == "Solo Author",
       solo.description is None, solo.avatar is None
     - test_load_missing_file_returns_empty: passing a nonexistent path returns empty dict
     - test_author_missing_name_raises: YAML with author entry missing "name" field
       raises AuthorError
     - test_resolve_valid_keys: given authors dict and keys ["mason", "guest"],
       returns list of 2 Author objects in order
     - test_resolve_missing_key_raises: resolving key "unknown" raises AuthorError
       with the missing key name in the message
     - test_resolve_empty_keys: resolving empty list returns empty list

2. GREEN: Create src/bartleby/authors.py:
   - ABOUTME: Author definition loading, validation, and resolution.
   - AuthorError(Exception)
   - @dataclass Author: key (str), name (str), description (str | None),
     avatar (str | None), url (str | None)
   - load_authors(authors_path: Path) -> dict[str, Author]:
     - If file doesn't exist, return empty dict
     - Parse YAML, validate each entry has "name"
     - Return dict mapping key -> Author
   - resolve_authors(keys: list[str], authors: dict[str, Author]) -> list[Author]:
     - Look up each key, raise AuthorError if missing
     - Return ordered list of Author objects

3. REFACTOR: Ensure error messages include the file path and offending key.

4. Verify: `just check` passes.
```

---

## Phase 2: Content Layer

### Step 4: Content Discovery and Front Matter

**Context**: Steps 1-3 complete. Config and authors systems working. Config defines content types with paths, and exclude patterns.

**Goal**: Scan content directories, parse YAML front matter, build Page objects, and apply file exclusion patterns. This is the foundation for all content processing.

```text
Step 4: Content Discovery and Front Matter. Steps 1-3 complete
(project scaffolding, config, authors).

Refer to spec.md "Content Organization" section. Content lives under content/.
Each content type has a configured path (e.g., blog/posts). Front matter is YAML
between --- delimiters. Non-markdown files are co-located assets.

1. RED: Write content discovery tests:
   - Create tests/fixtures/site/ directory with a sample site structure:
     - tests/fixtures/site/bartleby.yml (minimal config with blog and tutorials content types)
     - tests/fixtures/site/content/index.md (with title front matter)
     - tests/fixtures/site/content/about.md (with title and description)
     - tests/fixtures/site/content/blog/index.md (optional listing intro)
     - tests/fixtures/site/content/blog/posts/first-post.md
       (full front matter: title, date, description, draft: false, tags, authors)
     - tests/fixtures/site/content/blog/posts/second-post.md
       (different date, different tags)
     - tests/fixtures/site/content/blog/posts/draft-post.md (draft: true)
     - tests/fixtures/site/content/blog/posts/diagram.png (co-located asset)
     - tests/fixtures/site/content/_drafts/wip.md (should be excluded)

   - Create tests/test_content.py:
     - ABOUTME: Tests for content discovery, front matter parsing, and file exclusion.
     - test_parse_front_matter_basic: given string with --- delimiters, returns
       (metadata_dict, content_body) correctly split
     - test_parse_front_matter_no_front_matter: returns (empty_dict, full_content)
     - test_parse_front_matter_empty_front_matter: just --- and --- returns (empty_dict, "")
     - test_discover_content_finds_markdown_files: discovers index.md, about.md,
       blog posts, etc. Returns list of Page objects.
     - test_discover_content_associates_content_type: blog posts have
       content_type_name == "blog", about.md has content_type_name == None
     - test_discover_content_excludes_patterns: _drafts/wip.md not in results
     - test_discover_content_identifies_colocated_assets: diagram.png noted
       but not returned as a Page
     - test_discover_drafts_found_but_marked: draft-post.md has draft == True
     - test_page_fields_from_front_matter: first-post.md Page has correct title,
       date, description, draft, taxonomy_values, author_keys
     - test_should_exclude_matches_patterns: "_drafts/wip.md" matches "_drafts/**",
       "_secret.md" matches "_*.md", ".git/config" matches ".git/**"
     - test_should_exclude_no_match: "blog/posts/good.md" does not match any default pattern
     - test_discover_content_returns_colocated_assets_list: function returns
       both pages and a list of asset file paths

   - Add fixture to tests/conftest.py:
     - sample_site_path fixture returning Path to tests/fixtures/site/
     - sample_config fixture that loads the config from the sample site

2. GREEN: Create src/bartleby/content.py:
   - ABOUTME: Content discovery, front matter parsing, and page data objects.
   - @dataclass Page:
     - source_path: Path (relative to content/)
     - abs_source_path: Path (absolute)
     - title: str
     - description: str | None
     - date: datetime.date | None
     - draft: bool (default False)
     - template_override: str | None
     - url_override: str | None
     - url_base_override: str | None
     - author_keys: list[str]
     - taxonomy_values: dict[str, list[str]] (e.g., {"tags": ["python"]})
     - custom_metadata: dict[str, str | int | bool | list[str] | datetime.date]
     - raw_content: str
     - content_type_name: str | None
     - output_url: str (set later by URL generation)
     - rendered_content: str (set later by rendering)
     - excerpt: str (set later)
     - readtime: int | None (set later)
   - @dataclass ColocatedAsset:
     - source_path: Path (relative to content/)
     - abs_source_path: Path (absolute)
     - associated_page_source: Path | None
   - parse_front_matter(text: str) -> tuple[dict[str, object], str]
   - should_exclude(path_str: str, patterns: list[str]) -> bool
   - discover_content(config: BartlebyConfig, content_dir: Path) ->
       tuple[list[Page], list[ColocatedAsset]]:
     - Walk content_dir
     - Skip excluded files
     - For .md files: parse front matter, determine content type, build Page
     - For non-.md files: build ColocatedAsset
     - Return both lists

3. REFACTOR: Extract front matter field mapping to a helper. Ensure date parsing
   handles both string dates and datetime objects from YAML.

4. Verify: `just check` passes.
```

---

### Step 5: Metadata Validation

**Context**: Steps 1-4 complete. Content discovery returns Page objects with parsed front matter. Config defines metadata schemas per content type (type, required, choices).

**Goal**: Validate page front matter against content type metadata schemas. Catch missing required fields, type mismatches, and invalid choices at build time.

```text
Step 5: Metadata Validation. Steps 1-4 complete (config, authors, content discovery).

Refer to spec.md "Build-Time Metadata Validation" section. Content types can define
metadata schemas with required/type/choices constraints. Validation also checks
author references against loaded authors.

1. RED: Write metadata validation tests:
   - Create tests/test_metadata.py:
     - ABOUTME: Tests for build-time metadata validation against content type schemas.
     - test_valid_metadata_passes: page with all required fields matching schema
       returns empty error list
     - test_missing_required_field: page missing a required field returns error
       with field name and file path in message
     - test_optional_field_missing_ok: page missing an optional field returns no errors
     - test_wrong_type_date: field expects date, gets string "not-a-date", returns error
     - test_wrong_type_string: field expects string, gets integer, returns error
     - test_wrong_type_integer: field expects integer, gets string, returns error
     - test_wrong_type_boolean: field expects boolean, gets string, returns error
     - test_invalid_choice: field with choices ["beginner", "intermediate", "advanced"],
       value is "expert", error lists valid options
     - test_valid_choice_passes: value "intermediate" in choices passes
     - test_multiple_errors_all_reported: page with 2 invalid fields returns 2 errors
     - test_validate_author_references: page with author_keys ["mason"], authors dict
       has "mason" → passes. Key "unknown" → error.
     - test_page_without_content_type_skips_custom_validation: static pages
       (content_type_name is None) skip custom metadata validation
     - test_standard_fields_validated: title is required for all pages

2. GREEN: Create src/bartleby/metadata.py:
   - ABOUTME: Build-time metadata validation against content type schemas.
   - @dataclass ValidationError: file_path (str), field (str), message (str)
   - validate_page_metadata(page: Page, content_type: ContentTypeConfig | None,
       authors: dict[str, Author]) -> list[ValidationError]
   - validate_all_metadata(pages: list[Page], config: BartlebyConfig,
       authors: dict[str, Author]) -> list[ValidationError]:
     - For each page, find its content type config, call validate_page_metadata
     - Collect and return all errors

3. REFACTOR: Ensure validation error messages are user-friendly with exact file paths
   and field names.

4. Verify: `just check` passes.
```

---

### Step 6: URL Generation

**Context**: Steps 1-5 complete. Pages have front matter parsed. Config defines url_base, url_format per content type. Pages can have url/url_base overrides in front matter.

**Goal**: Generate output URLs for every page. Support path-based (default), format strings with placeholders, url_base overrides, and per-page overrides.

```text
Step 6: URL Generation. Steps 1-5 complete (config, authors, content, metadata).

Refer to spec.md "URL Generation" section. Default is path-based (mirrors content/).
Content types can set url_base and url_format. Pages can override with url or url_base
in front matter. Placeholders: {slug}, {date:%Y/%m/%d}, {title}, {categories}.

1. RED: Write URL generation tests:
   - Create tests/test_urls.py:
     - ABOUTME: Tests for URL generation from page data and content type config.
     - test_path_based_default: content/about.md → "/about/"
     - test_path_based_nested: content/blog/posts/my-post.md → "/blog/posts/my-post/"
     - test_path_based_index: content/blog/index.md → "/blog/"
     - test_root_index: content/index.md → "/"
     - test_url_format_date_slug: url_format="{date:%Y/%m/%d}/{slug}",
       date=2026-03-01, filename=my-post.md → includes "2026/03/01/my-post"
     - test_url_base_overrides_path: path="blog/posts", url_base="blog",
       url_format="{date:%Y/%m/%d}/{slug}" → "/blog/2026/03/01/my-post/"
     - test_url_base_without_format: url_base="blog" without url_format,
       file=my-post.md → "/blog/my-post/"
     - test_per_page_url_override: front matter url="custom/path" → "/custom/path/"
     - test_per_page_url_base_override: front matter url_base="articles",
       url_format from content type still applies
     - test_slug_from_filename: no front matter slug → slug derived from filename
     - test_slug_from_front_matter: front matter slug="custom-slug" overrides filename
     - test_categories_placeholder: {categories} uses first category slugified
     - test_title_placeholder: {title} uses slugified title
     - test_trailing_slash_always_added: all URLs end with /
     - test_generate_urls_for_all_pages: batch function sets output_url on each Page

2. GREEN: Create src/bartleby/urls.py:
   - ABOUTME: URL generation for pages based on content type config and front matter.
   - generate_url(page: Page, content_type: ContentTypeConfig | None) -> str
   - generate_all_urls(pages: list[Page], config: BartlebyConfig) -> None:
     - Sets page.output_url for each page
   - _format_url(format_str: str, page: Page) -> str:
     - Handle {slug}, {date:FORMAT}, {title}, {categories}
   - _slugify(text: str) -> str: use python-slugify
   - _path_to_url(source_path: Path) -> str: convert content path to URL

3. REFACTOR: Handle edge cases — pages without dates using {date} format should
   raise a clear error.

4. Verify: `just check` passes.
```

---

## Phase 3: Rendering Pipeline

### Step 7: Markdown Pipeline

**Context**: Steps 1-6 complete. Pages have raw markdown content and generated URLs. Config specifies markdown extension overrides.

**Goal**: Configure the Python-Markdown rendering pipeline with all default extensions (do-markdown, pymdownx, standard) in the correct processing order.

```text
Step 7: Markdown Pipeline. Steps 1-6 complete (config through URL generation).

Refer to spec.md "Markdown Pipeline" section. All extensions loaded by default.
Critical ordering: do_markdown.fence preprocessor (priority 40) runs BEFORE
pymdownx.superfences preprocessor (priority 25). The fence postprocessor runs AFTER.
Users override extension config via markdown_extensions in bartleby.yml.

1. RED: Write markdown pipeline tests:
   - Create tests/test_markdown_pipeline.py:
     - ABOUTME: Tests for the markdown rendering pipeline configuration and output.
     - test_basic_markdown_renders: "# Hello\n\nWorld" → contains <h1> and <p>
     - test_fenced_code_block: ```python block renders with syntax highlighting
     - test_admonition_renders: !!! note block renders admonition HTML
     - test_table_renders: markdown table produces <table> HTML
     - test_toc_extracted: headings produce table of contents data
     - test_do_markdown_fence_label: code block with [label script.py] produces
       label in output (test our pipeline config, not do-markdown itself)
     - test_do_markdown_highlight: <^>text<^> produces <mark> tag
     - test_pymdownx_tasklist: - [x] item renders as checkbox
     - test_extension_ordering_fence_before_superfences: a code block with BOTH
       [label ...] directive AND fenced syntax renders correctly (fence preprocessor
       extracts directives before superfences processes the block)
     - test_config_override_applied: custom superfences config (mermaid fence)
       is applied when passed through config
     - test_renderer_reusable: same renderer instance can render multiple documents

2. GREEN: Create src/bartleby/markdown_pipeline.py:
   - ABOUTME: Markdown rendering pipeline with all default extensions configured.
   - @dataclass RenderedContent: html (str), toc_tokens (list[dict[str, object]])
   - create_markdown_renderer(config: BartlebyConfig) -> markdown.Markdown:
     - Load all default extensions (see spec.md "Default Extensions" for full list):
       - do-markdown: fence, highlight, youtube, codepen, twitter, instagram,
         slideshow, image_compare
       - pymdownx: superfences, highlight, inlinehilite, tabbed, details, tasklist,
         arithmatex, keys, mark, caret, tilde, critic, smartsymbols, emoji, snippets,
         blocks.caption
       - standard: tables, toc, attr_list, def_list, footnotes, admonition,
         abbr, md_in_html
     - Apply user config overrides from config.markdown_extensions
     - Return configured Markdown instance
   - render_markdown(source: str, renderer: markdown.Markdown) -> RenderedContent:
     - Reset renderer, convert source, extract TOC
     - Return RenderedContent with html and toc_tokens

3. REFACTOR: If any extensions fail to import, produce a clear error message
   naming the missing extension.

4. Verify: `just check` passes.
```

---

### Step 8: Template System

**Context**: Steps 1-7 complete. Markdown rendering works. Config has theme settings. Pages have URLs and can be rendered to HTML.

**Goal**: Set up the Jinja2 template environment with the 5-level lookup cascade, build page context objects, and create minimal theme templates that produce valid HTML output.

```text
Step 8: Template System. Steps 1-7 complete (config through markdown rendering).

Refer to spec.md "Template System" section. Jinja2 templates with 5-level lookup:
1. Page front matter template override
2. templates/{content_type}/post.html or list.html
3. templates/{content_type}/base.html
4. templates/defaults/post.html or list.html
5. Theme fallback (built-in)

Also refer to spec.md "SEO" and "LLM Friendliness > JSON-LD" sections for
meta tags that go in the base template.

1. RED: Write template system tests:
   - Create tests/fixtures/templates/custom_override.html:
     A simple template: "CUSTOM:{{ page.title }}"
   - Create tests/fixtures/templates/blog/post.html:
     "BLOG_POST:{{ page.title }}"

   - Create tests/test_templates.py:
     - ABOUTME: Tests for Jinja2 template environment, lookup cascade, and context building.
     - test_theme_fallback_resolves: with no user templates, resolves to built-in theme template
     - test_page_template_override: page with template_override="custom_override.html"
       resolves to user template
     - test_content_type_template: blog post resolves to templates/blog/post.html
       when it exists in user templates dir
     - test_defaults_template: non-blog page without specific template falls back
       to templates/defaults/post.html or page.html
     - test_user_overrides_theme: user template with same name as theme template
       takes precedence
     - test_context_has_required_keys: built context contains:
       site, page, nav, pages, taxonomies, config, build
     - test_context_page_fields: page in context has title, content, url, authors,
       readtime, toc, date, description, previous, next
     - test_context_build_metadata: build has date and bartleby_version
     - test_taxonomy_template_lookup: taxonomy page looks for
       templates/{content_type}/taxonomy/{name}.html first
     - test_jinja_env_has_correct_search_paths: environment searches
       user templates/, then theme templates/

2. GREEN: Create src/bartleby/templates.py:
   - ABOUTME: Jinja2 template environment, lookup cascade, and context building.
   - create_jinja_env(config: BartlebyConfig, project_dir: Path) -> jinja2.Environment:
     - Template search paths: [project_dir/templates, theme_templates_dir]
     - Enable autoescape for HTML
   - resolve_template_name(page: Page, template_type: str) -> str:
     - Implement 5-level lookup cascade
     - template_type is "post", "list", "page", "taxonomy", "taxonomy_index"
     - Return template name string (not the template itself — let Jinja2 resolve)
   - build_page_context(page, site_config, nav, all_pages, taxonomy_data,
       config, build_info) -> dict[str, object]:
     - Build the context dict with all required keys

   Create minimal built-in theme templates (functional, not styled):
   - src/bartleby/theme/__init__.py:
     - ABOUTME: Built-in Material theme package for Bartleby.
     - Function to get theme templates directory path
   - src/bartleby/theme/templates/base.html:
     - Valid HTML5 skeleton with <head> (title, meta, canonical URL,
       Open Graph tags, Twitter Card tags, JSON-LD structured data)
       and <body> with {% block content %}
     - Include SEO meta tags using page context (see spec.md SEO section)
     - Include JSON-LD (Article for posts, WebPage for pages — see spec.md LLM section)
   - src/bartleby/theme/templates/page.html: extends base, renders page.content
   - src/bartleby/theme/templates/defaults/post.html: extends base, renders post
     with title, date, authors, readtime, content, tags
   - src/bartleby/theme/templates/defaults/list.html: extends base, renders
     paginated post listing with excerpts

3. REFACTOR: Extract SEO meta tag generation and JSON-LD generation into
   Jinja2 macros or include files under theme/templates/partials/ for reuse.

4. Verify: `just check` passes.
```

---

## Phase 4: First Working Build

### Step 9: Navigation System

**Context**: Steps 1-8 complete. Config has nav section. Pages are discovered with URLs. Template system is ready.

**Goal**: Build navigation structure from explicit config or auto-generate from directory structure. Set up previous/next page linking.

```text
Step 9: Navigation System. Steps 1-8 complete (config through template system).

Refer to spec.md "Configuration > nav" and "Build Pipeline > Order of Operations"
step 9 (resolve navigation) and step 14 (link pages).

Nav can be explicit (from bartleby.yml) or auto-generated from directory structure.
Auto-generated nav uses directory names as section titles, sorted alphabetically.

1. RED: Write navigation tests:
   - Create tests/test_navigation.py:
     - ABOUTME: Tests for navigation building, auto-generation, and page linking.
     - test_explicit_nav_from_config: given nav config
       [{"Home": "index.md"}, {"Blog": "blog/"}, {"About": "about.md"}],
       builds NavItem list with correct titles and URLs
     - test_explicit_nav_nested: nav with nested sections creates child NavItems
     - test_auto_generate_nav: given pages list (no nav config),
       generates nav from directory structure
     - test_auto_nav_alphabetical: auto-generated items sorted alphabetically
     - test_auto_nav_directory_names_as_sections: directory "blog" becomes
       section title "Blog" (title-cased)
     - test_auto_nav_uses_page_title: page title from front matter used,
       not filename
     - test_prev_next_linking: after linking, pages have correct previous/next
       references following nav order
     - test_prev_next_none_at_edges: first page has previous=None,
       last page has next=None
     - test_pages_not_in_nav_no_prev_next: pages excluded from nav
       don't get prev/next links

2. GREEN: Create src/bartleby/navigation.py:
   - ABOUTME: Navigation building from config or auto-generation from directory structure.
   - @dataclass NavItem: title (str), url (str | None),
     children (list[NavItem]), page (Page | None), is_section (bool)
   - @dataclass Navigation: items (list[NavItem]), pages_flat (list[Page])
   - build_navigation(config: BartlebyConfig, pages: list[Page]) -> Navigation:
     - If config.nav is not None, build from explicit config
     - Otherwise auto-generate from pages
   - _build_explicit_nav(nav_config, pages) -> list[NavItem]
   - _auto_generate_nav(pages) -> list[NavItem]
   - link_pages(nav: Navigation) -> None:
     - Walk pages_flat in order, set previous/next on each Page

3. REFACTOR: Handle edge cases — nav referencing nonexistent files should warn.

4. Verify: `just check` passes.
```

---

### Step 10: Build Pipeline v1

**Context**: Steps 1-9 complete. All core components exist independently: config, authors, content, metadata, URLs, markdown, templates, navigation. Nothing is wired together yet.

**Goal**: Create the build orchestrator that wires all components together to produce a working `site/` directory with rendered HTML pages. This is the first milestone where Bartleby can actually build a site end-to-end. Also add excerpt extraction and read time calculation.

```text
Step 10: Build Pipeline v1. Steps 1-9 complete (all core components exist independently).

Refer to spec.md "Build Pipeline > Order of Operations" for the full 29-step pipeline.
This step implements the core rendering loop (steps 1, 6, 8-9, 14, 16a-n from the spec).
Plugin hooks are stubbed as no-ops — we add the minimal PluginCollection here so hook
call sites exist from the start, but no plugins are loaded yet (that's Step 21).

Also implement excerpt extraction (spec.md "Content Features > Excerpts") and
read time calculation (spec.md "Content Features > Read time").

1. RED: Write build pipeline integration tests:
   - Expand tests/fixtures/site/ to be a complete minimal site:
     - Ensure bartleby.yml has blog content type with readtime: true
       and excerpt_separator: "<!-- more -->"
     - Ensure blog posts have front matter with dates
     - One post with <!-- more --> separator, one without
   - Create tests/test_build.py:
     - ABOUTME: Integration tests for the build pipeline orchestrator.
     - test_build_produces_output_directory: build writes to site/ dir
     - test_build_renders_index_page: site/index.html exists and contains
       rendered content from content/index.md
     - test_build_renders_blog_post: blog post HTML file exists at correct
       URL path under site/
     - test_build_html_is_valid_structure: output contains <!DOCTYPE html>,
       <html>, <head>, <body>
     - test_build_page_title_in_output: page title appears in <title> tag
     - test_build_excludes_drafts: draft post not in site/ output
     - test_build_read_time_calculated: blog post Page object has readtime
       set (integer, > 0)
     - test_build_excerpt_with_separator: post with <!-- more --> has excerpt
       containing only content before separator
     - test_build_excerpt_without_separator: post without separator uses
       first paragraph as excerpt
     - test_build_cleans_output_dir: site/ dir is cleaned before build
     - test_build_returns_result: build() returns BuildResult with page count
       and timing info

   Also write unit tests for excerpt and readtime:
   - test_extract_excerpt_with_separator: given markdown with separator, returns
     content before it (rendered to HTML)
   - test_extract_excerpt_first_paragraph: given markdown without separator,
     returns first paragraph
   - test_calculate_readtime: given text of ~1000 words, returns ~4-5 minutes
     (assuming ~265 wpm)

2. GREEN: Create src/bartleby/build.py:
   - ABOUTME: Build pipeline orchestrator wiring all components together.
   - @dataclass BuildResult: page_count (int), duration_seconds (float)
   - @dataclass BuildInfo: date (datetime.date), bartleby_version (str)
   - build(config_path: Path, *, include_drafts: bool = False) -> BuildResult:
     Pipeline:
     1. Load config (config.load_config)
     2. Load authors (authors.load_authors)
     3. Discover content (content.discover_content)
     4. Validate metadata (metadata.validate_all_metadata) — fail on errors
     5. Generate URLs (urls.generate_all_urls)
     6. Build navigation (navigation.build_navigation)
     7. Link pages (navigation.link_pages)
     8. Create markdown renderer (markdown_pipeline.create_markdown_renderer)
     9. Create Jinja2 env (templates.create_jinja_env)
     10. Clean site/ output directory
     11. For each page:
         a. Render markdown (markdown_pipeline.render_markdown)
         b. Calculate read time (if content type has readtime: true)
         c. Extract excerpt (if content type has excerpt_separator)
         d. Store rendered content, TOC, readtime, excerpt on Page
         e. Build template context (templates.build_page_context)
         f. Resolve template name (templates.resolve_template_name)
         g. Render template
         h. Write HTML to site/ at correct path
     12. Return BuildResult
   - extract_excerpt(markdown_source: str, separator: str | None) -> str
   - calculate_readtime(text: str) -> int

   Create src/bartleby/plugins.py (minimal, for hook infrastructure):
   - ABOUTME: Plugin system — base classes, hook dispatch, and plugin discovery.
   - class PluginCollection:
     - events: dict mapping event names to handler lists
     - run_event(name, item, **kwargs) -> item: call handlers, return result
     (No BasePlugin or discovery yet — just the dispatch mechanism.
      build.py imports this and can call run_event at hook points,
      but with empty events dict they're no-ops.)

3. REFACTOR:
   - Ensure the build pipeline has clear separation between phases
     (gather data vs. render vs. write)
   - Add plugin.run_event() calls at key hook points in the pipeline,
     matching spec.md's hook locations. With empty PluginCollection these
     are no-ops but establish the call sites for Step 21.

4. Verify: `just check` passes.
   Also manually verify: the test fixture site should produce valid HTML when
   the build test runs (check the tmp_path output in a failing test to inspect).
```

---

## Phase 5: Content Features

### Step 11: Taxonomy System

**Context**: Steps 1-10 complete. Build pipeline produces HTML output. Pages have taxonomy values (tags, categories) in their front matter. Config defines taxonomies and which content types opt in.

**Goal**: Build taxonomy term-to-page mappings. Generate global and per-content-type taxonomy listing pages.

```text
Step 11: Taxonomy System. Steps 1-10 complete (working build pipeline).

Refer to spec.md "Taxonomy System" section. Taxonomies defined at site level.
Content types opt in via their taxonomies list. Generated pages at two levels:
global (/tags/, /tags/python/) and per-content-type (/blog/tags/, /blog/tags/python/).

1. RED: Write taxonomy tests:
   - Update tests/fixtures/site/ to have posts with various tags and categories
   - Create tests/test_taxonomies.py:
     - ABOUTME: Tests for taxonomy term collection, page mapping, and page generation.
     - test_collect_terms_from_pages: given pages with tags ["python", "temporal"]
       and ["python", "devops"], collects terms with correct page lists
     - test_term_counts: "python" has 2 pages, "temporal" has 1
     - test_ignores_non_opted_in_taxonomy: content type only opts into tags —
       categories values from those pages ignored for taxonomy building
     - test_slug_format_applied: tag "Temporal Workflows" with
       slug_format "tag:{slug}" → slug "temporal-workflows"
     - test_global_taxonomy_pages_generated: /tags/ and /tags/python/ pages created
     - test_per_content_type_pages_generated: /blog/tags/ and /blog/tags/python/ created
     - test_taxonomy_page_has_correct_context: generated page has taxonomy.name,
       taxonomy.terms, taxonomy.term, taxonomy.pages, taxonomy.content_type
     - test_pages_sorted_by_date_within_term: pages for a term are in
       reverse chronological order
     - test_no_pages_for_term_no_page_generated: edge case handled

2. GREEN: Create src/bartleby/taxonomies.py:
   - ABOUTME: Taxonomy system — term collection, page mapping, and page generation.
   - @dataclass TaxonomyTerm: name (str), slug (str), pages (list[Page]), count (int)
   - @dataclass TaxonomyData: name (str), terms (dict[str, TaxonomyTerm]),
     content_type (str | None)
   - @dataclass AllTaxonomies: global_taxonomies (dict[str, TaxonomyData]),
     content_type_taxonomies (dict[str, dict[str, TaxonomyData]])
   - build_taxonomies(pages: list[Page], config: BartlebyConfig) -> AllTaxonomies
   - generate_taxonomy_pages(taxonomy_data: AllTaxonomies,
       config: BartlebyConfig) -> list[Page]:
     - Create Page objects for taxonomy index and term pages
     - These are "virtual" pages (no source file) rendered by taxonomy templates

3. Wire into build.py:
   - Add taxonomy building after URL generation (spec step 11)
   - Add taxonomy page generation (spec step 13)
   - Include taxonomy pages in the render loop
   - Pass AllTaxonomies to template context builder

4. Verify: `just check` passes.
```

---

### Step 12: Listing Pages and Pagination

**Context**: Steps 1-11 complete. Taxonomy system generates pages. Content types can have pagination config.

**Goal**: Generate listing pages for each content type (with optional index.md content above). Implement pagination for splitting content into multiple pages.

```text
Step 12: Listing Pages and Pagination. Steps 1-11 complete (through taxonomy system).

Refer to spec.md "Content Organization > Listing Pages" and "Pagination" sections.
Each content type gets a listing page at its base URL (e.g., /blog/).
If content/{type}/index.md exists, its content appears above the post listing.
Pagination splits into pages: /blog/, /blog/page/2/, etc.

1. RED: Write listing and pagination tests:
   - Create tests/test_pagination.py:
     - ABOUTME: Tests for pagination logic.
     - test_paginate_exact_fit: 10 items, per_page=10 → 1 page
     - test_paginate_overflow: 11 items, per_page=10 → 2 pages
       (first has 10, second has 1)
     - test_paginate_multiple_pages: 25 items, per_page=10 → 3 pages
     - test_paginate_empty: 0 items → 1 page (empty)
     - test_paginator_context: page 2 of 3 has has_next=True, has_prev=True,
       next_url, prev_url, page_range=[1,2,3]
     - test_paginator_first_page: has_prev=False, prev_url=None
     - test_paginator_last_page: has_next=False, next_url=None

   - Create tests/test_listings.py:
     - ABOUTME: Tests for content type listing page generation.
     - test_listing_page_generated: blog content type gets a listing page at /blog/
     - test_listing_posts_reverse_chronological: posts sorted newest first
     - test_listing_includes_index_md_content: when content/blog/index.md exists,
       its rendered content appears in listing page context as intro_content
     - test_listing_without_index_md: no index.md → intro_content is None
     - test_listing_with_pagination: 25 posts, per_page=10 → 3 listing pages
       at /blog/, /blog/page/2/, /blog/page/3/
     - test_listing_pagination_disabled: content type with pagination.enabled=False
       → single listing page with all posts
     - test_listing_excludes_drafts: draft posts not in listing

2. GREEN:
   - Create src/bartleby/pagination.py:
     - ABOUTME: Pagination logic for splitting content into pages.
     - @dataclass PaginatorPage: items (list[Page]), page_number (int),
       total_pages (int), has_next (bool), has_prev (bool),
       next_url (str | None), prev_url (str | None),
       page_range (list[int])
     - paginate(items: list[Page], per_page: int,
         base_url: str, url_format: str) -> list[PaginatorPage]

   - Create src/bartleby/listings.py:
     - ABOUTME: Content type listing page generation.
     - generate_listing_pages(pages: list[Page], config: BartlebyConfig,
         content_dir: Path, md_renderer: markdown.Markdown) -> list[Page]:
       - Group pages by content type
       - Sort reverse chronological
       - Apply pagination if enabled
       - Read and render index.md if it exists
       - Create virtual Page objects for listings

3. Wire into build.py:
   - Generate listing pages after taxonomy pages (spec step 12)
   - Include listing pages in the render loop
   - Pass paginator to listing template context

4. Verify: `just check` passes.
```

---

### Step 13: Cross-Reference Resolution

**Context**: Steps 1-12 complete. Pages have rendered HTML and output URLs. Markdown content may contain relative `.md` links to other content pages.

**Goal**: Rewrite relative `.md` links in rendered HTML to point to the correct output URLs. Validate that link targets exist. Report broken links.

```text
Step 13: Cross-Reference Resolution. Steps 1-12 complete (through listings/pagination).

Refer to spec.md "Content Organization > Cross-References" section.
Links like [text](../tutorials/posts/deploy.md) are rewritten to output URLs.
Relative paths resolved from current file's location within content/.

1. RED: Write cross-reference tests:
   - Create tests/test_crossrefs.py:
     - ABOUTME: Tests for cross-reference link resolution and validation.
     - test_md_link_rewritten: href="../tutorials/posts/deploy.md" in page at
       content/blog/posts/my-post.md → rewritten to deploy page's output URL
     - test_absolute_url_unchanged: href="https://example.com" left as-is
     - test_anchor_link_unchanged: href="#section" left as-is
     - test_non_md_link_unchanged: href="slides.pdf" left as-is
     - test_broken_link_detected: href="nonexistent.md" produces CrossRefError
       with source page and target path
     - test_md_link_with_anchor: href="other.md#section" → rewritten URL + #section
     - test_resolve_all_crossrefs: batch function processes all pages and
       returns list of errors
     - test_index_md_link: href="../../about.md" from nested content resolves correctly

2. GREEN: Create src/bartleby/crossrefs.py:
   - ABOUTME: Cross-reference resolution — rewrite .md links to output URLs.
   - @dataclass CrossRefError: source_path (str), target_path (str), message (str)
   - resolve_page_crossrefs(html: str, current_page: Page,
       all_pages: list[Page], content_dir: Path) -> tuple[str, list[CrossRefError]]:
     - Parse HTML, find <a> tags with .md hrefs
     - Resolve relative path from current page's source location
     - Find target page, rewrite href to output URL
     - Return modified HTML and any errors
   - resolve_all_crossrefs(pages: list[Page],
       content_dir: Path) -> list[CrossRefError]:
     - Call resolve_page_crossrefs for each page
     - Update page.rendered_content with rewritten HTML

3. Wire into build.py:
   - Add cross-reference resolution after markdown rendering (spec step 16g)
   - Log warnings for broken links (or fail in strict mode)

4. Verify: `just check` passes.
```

---

### Step 14: Shortcode Preprocessing

**Context**: Steps 1-13 complete. Markdown rendering and cross-references work. Jinja2 environment is configured.

**Goal**: Parse `[% ... %]` shortcode syntax in markdown, resolve them as Jinja2 template fragments before markdown rendering runs.

```text
Step 14: Shortcode Preprocessing. Steps 1-13 complete (through cross-references).

Refer to spec.md "Template System > Shortcodes" section.
Shortcodes use [% ... %] syntax (not {% %} to avoid Jinja2 collision).
Block: [% note %]content[% /note %]. Inline: [% version %].
Resolved during markdown preprocessing, before markdown engine runs.
Template fragments at templates/shortcodes/{name}.html.

1. RED: Write shortcode tests:
   - Create tests/fixtures/templates/shortcodes/note.html:
     ```html
     <div class="shortcode-note">{{ content }}</div>
     ```
   - Create tests/fixtures/templates/shortcodes/version.html:
     ```html
     {{ build.bartleby_version }}
     ```
   - Create tests/fixtures/templates/shortcodes/callout.html:
     ```html
     <div class="callout callout-{{ type }}"><h3>{{ title }}</h3>{{ content }}</div>
     ```

   - Create tests/test_shortcodes.py:
     - ABOUTME: Tests for shortcode parsing and rendering.
     - test_block_shortcode: "[% note %]\nImportant\n[% /note %]" →
       rendered through note.html template
     - test_inline_shortcode: "[% version %]" → replaced with version string
     - test_shortcode_with_args: "[% callout type=\"warning\" title=\"Careful\" %]
       text[% /callout %]" → rendered with type and title in context
     - test_include_shortcode: "[% include \"partials/signup.html\" %]" →
       includes the template file
     - test_unknown_shortcode_raises: "[% nonexistent %]" raises ShortcodeError
     - test_shortcode_has_page_context: shortcode templates receive page context
     - test_shortcodes_processed_before_markdown: shortcode output is valid
       for subsequent markdown processing
     - test_no_shortcodes_passthrough: markdown without shortcodes unchanged

2. GREEN: Create src/bartleby/shortcodes.py:
   - ABOUTME: Shortcode preprocessing — parse [% %] syntax and render as Jinja2 fragments.
   - ShortcodeError(Exception)
   - process_shortcodes(markdown_source: str, context: dict[str, object],
       jinja_env: jinja2.Environment) -> str:
     - Find all [% ... %] patterns
     - For block shortcodes: extract content between opening and closing tags
     - For inline shortcodes: no content
     - Parse arguments (key="value" pairs)
     - Load template from shortcodes/{name}.html
     - Render with context + content + arguments
     - Replace shortcode markers with rendered output

3. Wire into build.py:
   - Process shortcodes before markdown rendering (spec step 16c)

4. Verify: `just check` passes.
```

---

### Step 15: Static Files and Co-located Assets

**Context**: Steps 1-14 complete. Build pipeline renders HTML. Content discovery identifies co-located assets. URLs are generated for all pages.

**Goal**: Copy static/ directory contents to site root. Copy co-located content assets to the correct output location (following the page's URL, not the source path).

```text
Step 15: Static Files and Co-located Assets. Steps 1-14 complete (through shortcodes).

Refer to spec.md "Content Organization > Static Files and Co-Located Assets" section.
static/ → site root (static/logo.png → /logo.png).
Co-located assets follow page URL, not source path. This is critical when url_format
changes the output path (e.g., content/blog/posts/diagram.png →
/blog/2026/03/01/my-post/diagram.png).

1. RED: Write asset copying tests:
   - Update tests/fixtures/site/ to include:
     - tests/fixtures/site/static/logo.png (a small file, can be empty)
     - tests/fixtures/site/static/css/custom.css
   - Ensure content/blog/posts/diagram.png exists (from Step 4)

   - Create tests/test_assets.py:
     - ABOUTME: Tests for static file copying and co-located asset handling.
     - test_copy_static_to_root: static/logo.png → site/logo.png
     - test_copy_static_preserves_subdirs: static/css/custom.css → site/css/custom.css
     - test_colocated_asset_path_based: without url_format, asset stays
       at same relative path in output
     - test_colocated_asset_follows_url_format: with url_format changing page
       output path, co-located asset follows page URL directory
     - test_binary_files_copied_unchanged: file content preserved
     - test_empty_static_dir_ok: no static/ directory doesn't crash

2. GREEN: Create src/bartleby/assets.py:
   - ABOUTME: Static file copying and co-located asset handling.
   - copy_static_files(static_dir: Path, output_dir: Path) -> None:
     - Recursively copy static/ to output root
   - copy_colocated_assets(assets: list[ColocatedAsset], pages: list[Page],
       content_dir: Path, output_dir: Path) -> None:
     - For each asset, find its associated page
     - Copy to page's output URL directory
   - _find_associated_page(asset: ColocatedAsset,
       pages: list[Page]) -> Page | None:
     - Match asset to page by directory proximity

3. Wire into build.py:
   - Copy static files after rendering (spec step 26)
   - Copy co-located assets during page output (spec step 16o)

4. Verify: `just check` passes.
```

---

## Phase 6: Generated Output

### Step 16: Search Index Generation

**Context**: Steps 1-15 complete. Build pipeline produces full HTML output with all content features.

**Goal**: Generate a JSON search index from rendered page content, compatible with lunr.js.

```text
Step 16: Search Index Generation. Steps 1-15 complete (full build with content features).

Refer to spec.md "Search" section. Build-time JSON index with config, docs array.
Each doc has location, title, text (extracted from HTML), tags.
Section-level entries (per heading) for granular search.

1. RED: Write search index tests:
   - Create tests/test_search.py:
     - ABOUTME: Tests for search index generation.
     - test_index_structure: generated index has "config" and "docs" keys
     - test_config_format: config has lang, separator, pipeline
     - test_doc_entry_fields: each doc has location, title, text, tags
     - test_section_level_entries: page with 3 headings produces entries
       for each section with location including anchor
     - test_text_stripped_of_html: doc text contains no HTML tags
     - test_draft_pages_excluded: draft pages not in index
     - test_tags_included: page with tags has them in doc entry
     - test_index_is_valid_json: output parses as valid JSON

2. GREEN: Create src/bartleby/search.py:
   - ABOUTME: Search index generation for client-side search with lunr.js.
   - build_search_index(pages: list[Page], config: BartlebyConfig) -> dict[str, object]:
     - Extract searchable content from each page
     - Split into section-level entries by heading
     - Strip HTML from text content
     - Build index structure matching spec format
   - write_search_index(index: dict[str, object], output_dir: Path) -> None

3. Wire into build.py:
   - Generate search index after all pages rendered (spec step 19)

4. Verify: `just check` passes.
```

---

### Step 17: Feed Generation

**Context**: Steps 1-16 complete. Pages have all metadata, rendered content, and absolute URLs constructable from site.url + output_url.

**Goal**: Generate valid RSS 2.0 and Atom 1.0 feeds per content type as configured.

```text
Step 17: Feed Generation. Steps 1-16 complete (through search index).

Refer to spec.md "Feed Generation" section. RSS and Atom per content type.
Feeds include title, description, date, author, excerpt, full content.
URLs: /blog/feed.xml (RSS), /blog/atom.xml (Atom).

1. RED: Write feed generation tests:
   - Create tests/test_feeds.py:
     - ABOUTME: Tests for RSS and Atom feed generation.
     - test_rss_valid_xml: output parses as valid XML
     - test_rss_channel_metadata: channel has title, link, description
     - test_rss_item_fields: each item has title, link, description,
       pubDate, author
     - test_rss_item_count: correct number of items for content type
     - test_rss_absolute_urls: all links are absolute (start with site.url)
     - test_atom_valid_xml: output parses as valid XML
     - test_atom_entry_fields: entries have title, link, summary, updated, author
     - test_feed_only_for_configured_types: content type without feeds config
       produces no feed
     - test_rss_feed_path: written to {content_type}/feed.xml
     - test_atom_feed_path: written to {content_type}/atom.xml
     - test_feed_items_reverse_chronological: newest first

2. GREEN: Create src/bartleby/feeds.py:
   - ABOUTME: RSS 2.0 and Atom 1.0 feed generation per content type.
   - generate_rss(pages: list[Page], content_type_name: str,
       site: SiteConfig) -> str
   - generate_atom(pages: list[Page], content_type_name: str,
       site: SiteConfig) -> str
   - generate_feeds(pages: list[Page], config: BartlebyConfig,
       output_dir: Path) -> None:
     - Group pages by content type
     - For each content type with feeds configured, generate and write feeds

3. Wire into build.py:
   - Generate feeds after all pages rendered (spec step 20)

4. Verify: `just check` passes.
```

---

### Step 18: Sitemap and Robots.txt

**Context**: Steps 1-17 complete. All pages have absolute URLs. Config has AI crawler directives.

**Goal**: Generate sitemap.xml, sitemap.xml.gz, and robots.txt with AI crawler directives.

```text
Step 18: Sitemap and Robots.txt. Steps 1-17 complete (through feed generation).

Refer to spec.md "Sitemap and Robots" section.
sitemap.xml includes all non-draft pages with URL, lastmod, changefreq, priority.
robots.txt references sitemap and includes AI crawler directives from config.
Static robots.txt in static/ overrides generated one.

1. RED: Write sitemap and robots tests:
   - Create tests/test_sitemap.py:
     - ABOUTME: Tests for sitemap.xml and robots.txt generation.
     - test_sitemap_valid_xml: output parses as valid XML
     - test_sitemap_includes_all_pages: non-draft pages present
     - test_sitemap_excludes_drafts: draft pages not in sitemap
     - test_sitemap_has_absolute_urls: all URLs start with site.url
     - test_sitemap_lastmod: pages with dates have lastmod elements
     - test_sitemap_gz_generated: gzipped version created alongside XML
     - test_robots_txt_references_sitemap: contains Sitemap: line with URL
     - test_robots_txt_ai_allow: config ai.robots.allow includes
       User-agent directives for allowed bots
     - test_robots_txt_ai_disallow: config ai.robots.disallow includes
       Disallow directives for blocked bots
     - test_robots_txt_no_ai_config: no AI directives if neither allow nor
       disallow configured
     - test_static_robots_overrides: if static/robots.txt exists, it's used
       instead of generated

2. GREEN: Create src/bartleby/sitemap.py:
   - ABOUTME: Sitemap.xml and robots.txt generation.
   - generate_sitemap(pages: list[Page], site: SiteConfig) -> str
   - generate_sitemap_gz(sitemap_xml: str, output_dir: Path) -> None
   - generate_robots_txt(site: SiteConfig, ai_config: AIConfig) -> str

3. Wire into build.py:
   - Generate sitemap after all pages rendered (spec step 21)
   - Generate robots.txt (spec step 22)
   - Check for static/robots.txt override

4. Verify: `just check` passes.
```

---

### Step 19: SEO Meta Tags

**Context**: Steps 1-18 complete. Base template already has placeholder SEO tags from Step 8. Pages have all metadata.

**Goal**: Create dedicated SEO helper functions that generate proper Open Graph, Twitter Card, and canonical URL meta tags with fallback logic. Wire into template context.

```text
Step 19: SEO Meta Tags. Steps 1-18 complete (through sitemap/robots).

Refer to spec.md "SEO" section. OG tags, Twitter Cards, canonical URLs.
Fallback: page-level fields → site defaults. The base template from Step 8
already has placeholder tags — this step creates proper helper functions and
ensures the template uses them correctly.

1. RED: Write SEO tests:
   - Create tests/test_seo.py:
     - ABOUTME: Tests for SEO meta tag generation.
     - test_og_tags_from_page_data: page with title, description, image
       produces correct og:title, og:description, og:image
     - test_og_type_article_for_posts: content type posts get og:type="article"
     - test_og_type_website_for_pages: static pages get og:type="website"
     - test_twitter_card_tags: produces twitter:card, twitter:title,
       twitter:description, twitter:image
     - test_canonical_url: combines site.url + page output_url
     - test_fallback_to_site_defaults: page without description uses
       site.description; page without image uses site.default_image
     - test_article_tags: published_time, author, and per-tag article:tag generated
     - test_twitter_handle_included: when site.twitter configured,
       twitter:site tag included

2. GREEN: Create src/bartleby/seo.py:
   - ABOUTME: SEO meta tag generation — Open Graph, Twitter Cards, canonical URLs.
   - generate_og_tags(page: Page, site: SiteConfig) -> dict[str, str]
   - generate_twitter_tags(page: Page, site: SiteConfig) -> dict[str, str]
   - generate_canonical_url(page: Page, site: SiteConfig) -> str
   - generate_all_meta_tags(page: Page, site: SiteConfig) -> dict[str, str | dict]:
     - Combines OG, Twitter, canonical into one structure for template use

3. Wire into templates:
   - Update templates.build_page_context to include seo data
   - Update base.html to use the SEO helper output (or pass to a macro/partial)

4. Verify: `just check` passes.
```

---

### Step 20: LLM Output

**Context**: Steps 1-19 complete. Full site builds with SEO. Config has AI settings.

**Goal**: Generate llms.txt, llms-full.txt, markdown variant files alongside HTML, and JSON-LD structured data.

```text
Step 20: LLM Output. Steps 1-19 complete (through SEO).

Refer to spec.md "LLM Friendliness" section.
- llms.txt: structured site overview with links to .md variants
- llms-full.txt: full content of every page inlined
- Markdown variants: .md file alongside each .html (front matter stripped)
- JSON-LD: Article schema for posts, WebPage for pages (already in base.html
  from Step 8, but ensure the data is correct)

1. RED: Write LLM output tests:
   - Create tests/test_llm.py:
     - ABOUTME: Tests for LLM-friendly output generation.
     - test_llms_txt_format: starts with "# {site.title}", has description,
       sections by content type, entries with title and .md URL
     - test_llms_txt_links_to_md_variants: links end with .md
     - test_llms_txt_disabled: when ai.llms_txt is False, not generated
     - test_llms_full_txt_includes_content: full markdown content inlined
       for each page, separated by ---
     - test_llms_full_txt_disabled: when ai.llms_full_txt is False, not generated
     - test_markdown_variant_written: for page at site/blog/post/index.html,
       site/blog/post/index.md also written
     - test_markdown_variant_strips_front_matter: .md file has no YAML
       front matter, just content
     - test_markdown_variants_disabled: when ai.markdown_variants is False,
       no .md files written
     - test_jsonld_article_for_post: JSON-LD has @type Article, correct fields
     - test_jsonld_webpage_for_static: JSON-LD has @type WebPage
     - test_jsonld_fields_populated: headline, author, datePublished, etc.

2. GREEN: Create src/bartleby/llm.py:
   - ABOUTME: LLM-friendly output — llms.txt, llms-full.txt, markdown variants, JSON-LD.
   - generate_llms_txt(pages: list[Page], site: SiteConfig,
       config: BartlebyConfig) -> str
   - generate_llms_full_txt(pages: list[Page], site: SiteConfig,
       config: BartlebyConfig) -> str
   - write_markdown_variant(page: Page, output_dir: Path) -> None
   - generate_jsonld(page: Page, site: SiteConfig) -> str:
     - Article schema for content type posts
     - WebPage schema for static pages

3. Wire into build.py:
   - Write markdown variants after page rendering (spec step 17)
   - Generate llms.txt and llms-full.txt (spec steps 23-24)
   - Pass JSON-LD to template context (or generate in template via macro)

4. Verify: `just check` passes.
```

---

## Phase 7: Extensibility

### Step 21: Plugin System

**Context**: Steps 1-20 complete. Build pipeline has PluginCollection with run_event() call sites throughout (from Step 10), but no actual plugin support — events dict is always empty.

**Goal**: Implement BasePlugin with all 16 hooks, @event_priority decorator, plugin discovery (entry points + local plugins/ directory), and verify plugins can hook into the build pipeline.

```text
Step 21: Plugin System. Steps 1-20 complete. PluginCollection exists in plugins.py
with run_event() already called throughout build.py, but no BasePlugin or discovery.

Refer to spec.md "Plugin System" section. 16 hooks across lifecycle, config,
build, per-page, and post-build phases. Plugins from pip entry points or
local plugins/ directory. @event_priority for ordering.

1. RED: Write plugin system tests:
   - Create tests/test_plugins.py:
     - ABOUTME: Tests for plugin base class, hook dispatch, priority, and discovery.
     - test_base_plugin_hooks_are_noop: BasePlugin instance, all hook methods
       return None by default
     - test_plugin_collection_registers_hooks: adding a plugin with on_config
       method registers it in events["config"]
     - test_run_event_calls_handler: registered handler called with correct args
     - test_run_event_none_keeps_value: handler returning None preserves item
     - test_run_event_new_value_replaces: handler returning new value replaces item
     - test_event_priority_ordering: two plugins with different priorities
       called in priority order (higher first)
     - test_event_priority_default: unprioritized handlers get priority 0
     - test_multiple_plugins_chained: three plugins modifying same event,
       changes chain correctly
     - test_discover_entry_point_plugins: mock entry points discovery
     - test_discover_local_plugins: plugin .py file in plugins/ directory
       discovered and loaded
     - test_plugin_config_loaded: plugin with config class gets config validated
     - test_build_with_plugin: end-to-end test — plugin that modifies
       on_page_markdown (e.g., adds a banner) produces expected output

   All 16 hooks from spec (test they can be overridden):
     - test_lifecycle_hooks: on_startup, on_shutdown
     - test_config_hooks: on_config
     - test_build_hooks: on_pre_build, on_files, on_nav, on_env
     - test_page_hooks: on_pre_page, on_page_read_source, on_page_markdown,
       on_page_content, on_page_context, on_post_page
     - test_post_build_hooks: on_post_build, on_build_error
     - test_serve_hook: on_serve

2. GREEN: Extend src/bartleby/plugins.py:
   - Keep existing PluginCollection.run_event()
   - Add BasePlugin class with all 16 hook methods (default return None):
     - on_startup(command: str) -> None
     - on_shutdown() -> None
     - on_config(config: BartlebyConfig) -> BartlebyConfig | None
     - on_pre_build(config: BartlebyConfig) -> None
     - on_files(files: tuple[list[Page], list[ColocatedAsset]],
         config: BartlebyConfig) -> tuple | None
     - on_nav(nav: Navigation, config: BartlebyConfig) -> Navigation | None
     - on_env(env: jinja2.Environment, config: BartlebyConfig) -> jinja2.Environment | None
     - on_pre_page(page: Page, config: BartlebyConfig) -> Page | None
     - on_page_read_source(page: Page, config: BartlebyConfig) -> str | None
     - on_page_markdown(markdown: str, page: Page, config: BartlebyConfig) -> str | None
     - on_page_content(html: str, page: Page, config: BartlebyConfig) -> str | None
     - on_page_context(context: dict, page: Page, config: BartlebyConfig) -> dict | None
     - on_post_page(output: str, page: Page, config: BartlebyConfig) -> str | None
     - on_post_build(config: BartlebyConfig) -> None
     - on_build_error(error: Exception) -> None
     - on_serve(server: object, config: BartlebyConfig) -> None
   - Add @event_priority(n) decorator
   - Add discover_plugins(config: BartlebyConfig, project_dir: Path) -> PluginCollection:
     - Load from entry_points(group="bartleby.plugins")
     - Load from plugins/ directory .py files
     - Register all hooks from discovered plugins
   - Update PluginCollection to support priority ordering in run_event

3. Wire into build.py:
   - Call discover_plugins() at pipeline start
   - The run_event() calls already exist from Step 10 — ensure they pass
     the correct arguments matching the BasePlugin signatures

4. Verify: `just check` passes.
```

---

## Phase 8: CLI and Server

### Step 22: CLI Commands

**Context**: Steps 1-21 complete. Build pipeline and plugin system fully functional. No CLI entry point yet (just a placeholder __main__.py).

**Goal**: Implement the CLI with argparse: `bartleby new site`, `bartleby new post`, `bartleby build`, `bartleby validate`, `bartleby serve` (serve is placeholder until Step 23).

```text
Step 22: CLI Commands. Steps 1-21 complete (full build pipeline + plugins).

Refer to spec.md "CLI" section. Commands: new site, new post, build, validate, serve.
Use argparse (stdlib) — no Click or Typer.

1. RED: Write CLI tests:
   - Create tests/test_cli.py:
     - ABOUTME: Tests for CLI command parsing and execution.
     - test_new_site_creates_structure: "new site mysite" creates directory with
       bartleby.yml, .authors.yml, content/index.md, templates/, plugins/, static/
     - test_new_site_valid_config: generated bartleby.yml is loadable by config system
     - test_new_site_directory_exists_error: creating site in existing dir raises error
     - test_new_post_creates_file: "new post 'My Title' --type blog" creates file
       in correct content type directory with slugified filename
     - test_new_post_front_matter: created file has correct front matter
       (title, date, required metadata fields for content type)
     - test_new_post_author_placeholder: if .authors.yml exists, front matter
       includes authors field
     - test_build_command_calls_pipeline: "build" invokes build.build()
     - test_build_strict_flag: "--strict" passes strict=True
     - test_validate_command: "validate" runs config + metadata validation
       without building
     - test_validate_exit_code: returns 0 on success, 1 on errors
     - test_parse_args_help: "--help" doesn't raise

2. GREEN: Create src/bartleby/cli.py:
   - ABOUTME: CLI commands using argparse — new, build, validate, serve.
   - main() -> None: set up argparse, dispatch to command functions
   - _cmd_new_site(args) -> None: scaffold new project
   - _cmd_new_post(args) -> None: create content file with front matter
   - _cmd_build(args) -> None: call build.build()
   - _cmd_validate(args) -> None: validate config and metadata
   - _cmd_serve(args) -> None: placeholder (prints "not yet implemented")

   Update src/bartleby/__main__.py:
   - ABOUTME: Entry point for running bartleby as `python -m bartleby`.
   - Call cli.main()

3. REFACTOR: Ensure error messages from build/validate are printed cleanly
   to stderr with exit codes.

4. Verify: `just check` passes.
```

---

### Step 23: Dev Server

**Context**: Steps 1-22 complete. CLI has `serve` placeholder. Build pipeline is synchronous.

**Goal**: Implement the development server with async HTTP serving, file watching (watchdog), WebSocket live reload, draft content inclusion, and dirty build mode.

```text
Step 23: Dev Server. Steps 1-22 complete (CLI with serve placeholder).

Refer to spec.md "Development Server" section. HTTP server serves site/ dir.
File watcher monitors content/, templates/, static/, plugins/, .authors.yml,
bartleby.yml. WebSocket pushes reload on change. Draft content included.
--dirty flag for incremental rebuilds.

1. RED: Write dev server tests:
   - Create tests/test_server.py:
     - ABOUTME: Tests for the development server, file watcher, and live reload.
     - test_server_starts_and_stops: server can be started and cleanly stopped
     - test_server_serves_built_files: after build, GET /index.html returns content
     - test_file_change_triggers_rebuild: modifying a content file triggers rebuild
     - test_config_change_triggers_full_rebuild: modifying bartleby.yml triggers
       full rebuild even in dirty mode
     - test_template_change_triggers_full_rebuild: modifying template triggers full
     - test_drafts_included: draft content served in dev mode
     - test_dirty_mode_incremental: only changed files rebuilt in dirty mode
     - test_websocket_reload_signal: WebSocket sends reload message after rebuild

   Note: Server tests may need to be integration tests using asyncio test helpers.
   Use pytest-asyncio if needed (add to dev dependencies).

2. GREEN: Create src/bartleby/server.py:
   - ABOUTME: Development server with live reload, file watching, and dirty builds.
   - serve(config_path: Path, *, host: str, port: int, dirty: bool) -> None:
     - Build site initially (with drafts)
     - Start async HTTP server
     - Start file watcher (watchdog)
     - Start WebSocket server for live reload
     - On file change: rebuild (dirty or full), send WebSocket reload
   - Use asyncio for the event loop
   - Use watchdog for file system monitoring
   - Use websockets library for WebSocket server

3. Wire into cli.py:
   - Replace serve placeholder with actual server call
   - Pass --dirty flag, host/port from config or CLI args

4. Verify: `just check` passes.
```

---

## Phase 9: Theme

### Step 24: Base Material Theme

**Context**: Steps 1-23 complete. Minimal templates from Step 8 produce functional but unstyled HTML. All features work end-to-end.

**Goal**: Replace minimal templates with properly structured Material Design templates using Tailwind CSS and Alpine.js. This step creates the template structure and basic styling — not the full polished theme.

```text
Step 24: Base Material Theme. Steps 1-23 complete. Minimal templates exist
from Step 8 — this step replaces them with proper Material-style templates.

Refer to spec.md "Material Theme (Built-In)" section.
Tailwind CSS for styling, Alpine.js for interactivity.
Templates use Tailwind utility classes directly (not opaque BEM classes).
Vendor Alpine.js and lunr.js as static assets.

1. RED: Write theme tests:
   - Create tests/test_theme.py:
     - ABOUTME: Tests for the built-in Material theme templates.
     - test_base_template_valid_html5: output starts with <!DOCTYPE html>,
       has <html>, <head>, <body>
     - test_base_template_has_meta_viewport: responsive meta tag present
     - test_base_template_includes_css: links to theme CSS
     - test_base_template_includes_alpine: Alpine.js script loaded
     - test_header_has_site_title: header contains site.title
     - test_nav_tabs_rendered: when navigation.tabs feature enabled,
       top-level nav rendered as tabs
     - test_dark_mode_toggle: when color_mode.toggle is true,
       toggle button rendered with Alpine.js x-data
     - test_post_template_shows_metadata: post template shows title, date,
       authors, readtime, tags
     - test_list_template_shows_pagination: listing template renders
       pagination controls when multiple pages
     - test_404_template_exists: 404.html renders without error
     - test_footer_has_prev_next: footer shows previous/next links when available
     - test_all_templates_render: smoke test rendering all template types
       (base, page, post, list, taxonomy, taxonomy_index, 404)

2. GREEN: Create/replace theme templates:
   - src/bartleby/theme/templates/base.html: Full HTML5 skeleton with:
     - Tailwind CSS link, Alpine.js script, HTMX script
     - Header partial include, nav partial include
     - Main content area with {% block content %}
     - Footer partial include
     - SEO meta tags (from Step 19)
     - JSON-LD (from Step 20)
     - Color mode logic (Alpine.js x-data for dark/light toggle)
   - src/bartleby/theme/templates/page.html: extends base, simple content rendering
   - src/bartleby/theme/templates/defaults/post.html: extends base, full post layout
     (title, meta, authors, readtime, content, tags, prev/next)
   - src/bartleby/theme/templates/defaults/list.html: extends base, post listing
     with pagination
   - src/bartleby/theme/templates/taxonomy.html: extends base, taxonomy term page
   - src/bartleby/theme/templates/taxonomy_index.html: extends base, all terms listing
   - src/bartleby/theme/templates/404.html: extends base, not-found page
   - src/bartleby/theme/templates/partials/header.html: site title, nav tabs, search, toggle
   - src/bartleby/theme/templates/partials/footer.html: prev/next, site info
   - src/bartleby/theme/templates/partials/nav.html: sidebar navigation
   - src/bartleby/theme/templates/partials/toc.html: table of contents sidebar

   Vendor JS assets:
   - src/bartleby/theme/static/js/alpine.min.js (download Alpine.js)
   - src/bartleby/theme/static/js/htmx.min.js (download HTMX)
   - src/bartleby/theme/static/js/lunr.min.js (download lunr.js)

   Create base Tailwind CSS:
   - src/bartleby/theme/static/css/main.css: compiled Tailwind output
     with base styles for typography, layout, components
   - Use Tailwind standalone CLI to compile
   - Include @apply rules mapping mkdocs-material class conventions
     (md-button, grid, cards) to Tailwind utilities

3. REFACTOR: Extract repeated template patterns into macros
   (e.g., post card, pagination controls, tag list).

4. Update build.py:
   - Copy theme static assets to site/ (spec step 27)

5. Verify: `just check` passes.
```

---

### Step 25: Full Material Theme

**Context**: Steps 1-24 complete. Base theme templates exist with proper structure. Basic Tailwind styling in place.

**Goal**: Polish the theme to match Material Design aesthetic. Style all content elements (admonitions, code blocks, tables, tabs, etc.). Complete responsive design and all theme features from the spec.

```text
Step 25: Full Material Theme. Steps 1-24 complete (base theme working).

Refer to spec.md "Material Theme > Theme Components" and "Content Reference"
sections. This step styles every content element and implements all theme features.

1. RED: Write comprehensive theme tests:
   - Create tests/test_theme_full.py:
     - ABOUTME: Tests for full Material theme styling and interactive components.
     - test_admonition_styled: !!! note renders with Material-style admonition classes
     - test_code_block_has_copy_button: when content.code.copy enabled,
       code blocks include copy button markup
     - test_code_block_line_numbers: linenums renders line number elements
     - test_content_tabs_rendered: tabbed content has tab UI with Alpine.js
     - test_search_modal: when search feature enabled, search modal markup present
       with Alpine.js x-data
     - test_sidebar_navigation: sidebar has collapsible sections with Alpine.js
     - test_toc_sidebar: table of contents sidebar rendered from page headings
     - test_responsive_mobile_menu: hamburger menu markup present for mobile
     - test_color_palette_applied: primary/accent colors from config appear
       as CSS custom properties
     - test_back_to_top: when navigation.top enabled, back-to-top button present
     - test_grid_cards_styled: grid/cards class produces CSS grid layout
     - test_mermaid_diagram: mermaid code block has mermaid class (client-side rendered)

2. GREEN: Enhance theme templates and CSS:
   - Update Tailwind CSS to style all content elements:
     - Admonitions (all 12 types with icons and colors)
     - Code blocks (syntax highlighting, copy button, annotations)
     - Content tabs (Alpine.js tab switching)
     - Tables (sortable option)
     - Details/summary (collapsible)
     - Task lists, definition lists
     - Footnotes
     - Buttons (md-button styling via @apply)
     - Grids and cards
     - Math (MathJax/KaTeX container styling)
     - Images (alignment, captions, lazy loading)
   - Add Alpine.js components:
     - Search modal (x-data, keyboard navigation, lunr.js integration)
     - Sidebar toggle (collapsible sections, active tracking)
     - TOC scroll spy (x-intersect)
     - Content tab linking
     - Back-to-top button
     - Dark mode toggle with localStorage persistence
   - Create src/bartleby/theme/templates/partials/search.html: search modal
   - Responsive breakpoints using Tailwind prefixes (sm:, md:, lg:)

3. Compile final Tailwind CSS with PurgeCSS for minimal output.

4. Verify: `just check` passes.
```

---

### Step 26: Icon Packs and Tree-Shaking

**Context**: Steps 1-25 complete. Theme renders icons via `:material-*:`, `:fontawesome-*:`, etc. syntax (handled by pymdownx.emoji extension). Icons referenced but not yet bundled.

**Goal**: Bundle icon SVGs, resolve icon references, and tree-shake unused icons from build output.

```text
Step 26: Icon Packs and Tree-Shaking. Steps 1-25 complete (full theme).

Refer to spec.md "Icon Packs" section. Four packs: Material Design Icons,
FontAwesome, Octicons, Simple Icons. All bundled in package but only used
icons copied to build output (tree-shaking). Packs can be disabled in config.

1. RED: Write icon tests:
   - Create tests/test_icons.py:
     - ABOUTME: Tests for icon pack bundling, resolution, and tree-shaking.
     - test_resolve_material_icon: ":material-account:" resolves to SVG path
     - test_resolve_fontawesome_icon: ":fontawesome-brands-github:" resolves
     - test_resolve_octicons_icon: ":octicons-heart-fill-24:" resolves
     - test_resolve_simple_icon: ":simple-python:" resolves
     - test_disabled_pack_not_resolved: pack set to false in config,
       icon from that pack returns None
     - test_tree_shake_includes_used: page HTML containing material-account
       → SVG copied to output
     - test_tree_shake_excludes_unused: icons not referenced in any page
       not copied to output
     - test_all_packs_enabled_by_default: default config has all four true

2. GREEN: Create src/bartleby/icons.py:
   - ABOUTME: Icon pack management, resolution, and build-time tree-shaking.
   - get_icon_path(icon_name: str, icon_packs: dict[str, bool]) -> Path | None
   - tree_shake_icons(rendered_pages: list[str], icon_packs: dict[str, bool],
       output_dir: Path) -> None:
     - Scan all rendered HTML for icon references
     - Copy only referenced SVGs to output
   - Bundle icon SVGs under src/bartleby/theme/icons/
     (Note: actual SVG files will need to be downloaded/included separately —
      for now, create the infrastructure and test with a few sample icons)

3. Wire into build.py:
   - Tree-shake icons after all pages rendered (spec step 18)

4. Verify: `just check` passes.
```

---

## Phase 10: Performance

### Step 27: Async Build Pipeline

**Context**: Steps 1-26 complete. Build pipeline is synchronous. All features working.

**Goal**: Convert the build pipeline to use asyncio for I/O-bound parallelism and ProcessPoolExecutor for CPU-bound markdown rendering. Plugin hooks must stay in the main process.

```text
Step 27: Async Build Pipeline. Steps 1-26 complete (full feature set, synchronous build).

Refer to spec.md "Build Pipeline > Async Build Architecture" section.
asyncio orchestrator. ProcessPoolExecutor for markdown.convert() only.
aiofiles for file I/O. Plugin hooks run in main process. Critical constraint:
only pure rendering work dispatched to workers — no plugin hooks cross process boundary.

1. RED: Write async build tests:
   - Create tests/test_async_build.py:
     - ABOUTME: Tests for async build pipeline correctness and parallelism.
     - test_async_build_same_output: async build produces identical output
       to sync build for the same fixture site
     - test_async_build_performance: async build of multi-page site completes
       (no deadlocks or hangs — use timeout)
     - test_plugin_hooks_main_process: plugin that checks threading.current_thread()
       confirms hooks run in main thread
     - test_concurrent_page_rendering: multiple pages rendered (verify all
       pages present in output)
     - test_async_file_writes: output files written correctly with aiofiles
     - test_concurrent_output_generation: search index, feeds, sitemap
       generated concurrently

2. GREEN: Modify src/bartleby/build.py:
   - Add async_build(config_path: Path, ...) -> BuildResult:
     - Same pipeline as build() but:
     - Content discovery: async directory scanning
     - Markdown rendering: dispatch to ProcessPoolExecutor
     - File writes: use aiofiles
     - Post-render outputs (search, feeds, sitemap, llms): run concurrently
       with asyncio.gather()
     - Plugin hooks: always await in main process, never dispatched to pool
   - Keep synchronous build() as fallback
   - Update CLI to use async_build by default

3. REFACTOR: Ensure clean error handling — if any async task fails,
   the build reports the error clearly rather than hanging.

4. Verify: `just check` passes.
```

---

## Phase 5: Agent Integration

### Step 28: Structured Output Layer

**Context**: Steps 1-27 complete. CLI commands work but only produce human-readable text output.

**Goal**: Add `--output json` support to all CLI commands. Every command returns a typed result dataclass that can be serialized to JSON or rendered as human text.

```text
Step 28: Structured Output Layer. Steps 1-27 complete (full features, async build).

Refer to spec.md "CLI > Global Flags" and "AI & Agent Integration > Structured CLI for Agents".

1. RED: Write tests:
   - Create tests/test_output.py:
     - ABOUTME: Tests for structured JSON output formatting across all CLI commands.
     - test_build_json_output: `bartleby build --output json` returns valid JSON
       with status, pages, duration_ms, errors, warnings fields
     - test_validate_json_output: `bartleby validate --output json` returns valid JSON
       with valid bool, errors array (each with file, line, field, message, code)
     - test_new_post_json_output: `bartleby new post --output json` returns valid JSON
       with path, url, content_type, metadata fields
     - test_json_error_output: when a command fails, JSON output includes "error" key
       with structured error info, exit code is 1
     - test_text_output_default: without --output flag, human-readable text is produced
     - test_quiet_flag: --quiet suppresses non-essential output
     - test_non_interactive_with_json: --output json never prompts, fails with
       exit code 2 if required flags missing

2. GREEN: Create src/bartleby/output.py:
   - ABOUTME: Structured output formatting — serialize command results as text or JSON.
   - Define result dataclasses: BuildResult, ValidateResult, NewPostResult, etc.
   - OutputFormatter protocol with TextFormatter and JsonFormatter implementations
   - Each CLI command returns its result dataclass; cli.py selects formatter
   - Update cli.py: add --output, --quiet, --verbose global flags
   - Update each command to return result dataclass instead of printing directly

3. REFACTOR: Ensure all existing tests still pass with the refactored CLI.

4. Verify: `just check` passes.
```

### Step 29: Non-Interactive Content Creation

**Context**: Steps 1-28 complete. `bartleby new post` works but prompts for content type interactively.

**Goal**: Add full flag support to `bartleby new post` for fully non-interactive operation. All metadata fields settable via flags.

```text
Step 29: Non-Interactive Content Creation. Steps 1-28 complete (structured output works).

Refer to spec.md "CLI > bartleby new post".

1. RED: Write tests:
   - In tests/test_cli.py (or tests/test_new_post.py):
     - test_new_post_all_flags: create post with --type, --author, --tags, --date,
       --draft, --slug, --meta all specified — verify correct front matter and file path
     - test_new_post_type_required_json_mode: when --output json and multiple content
       types exist but --type omitted, exit code 2 with error JSON
     - test_new_post_meta_flag_repeatable: --meta key1=val1 --meta key2=val2 sets
       both fields in front matter
     - test_new_post_slug_override: --slug custom-slug uses that instead of title-derived slug
     - test_new_post_date_default: omitting --date uses today's date
     - test_new_post_validates_author: --author nonexistent fails with error
     - test_new_post_validates_type: --type nonexistent fails with error

2. GREEN: Update cli.py new post command:
   - Add flags: --type, --author, --tags, --categories, --date, --draft, --slug, --meta
   - When all required info available via flags, skip prompts entirely
   - When --output json is set, never prompt — fail with structured error if info missing
   - Validate --author against .authors.yml, --type against config content types
   - Return NewPostResult dataclass

3. REFACTOR: Ensure interactive mode still works when flags omitted and --output json not set.

4. Verify: `just check` passes.
```

### Step 30: Content Query Commands

**Context**: Steps 1-29 complete. Content discovery exists in the build pipeline but is not exposed as standalone CLI commands.

**Goal**: Add `bartleby content list` and `bartleby content get` commands for programmatic content access.

```text
Step 30: Content Query Commands. Steps 1-29 complete (non-interactive CLI works).

Refer to spec.md "CLI > bartleby content list" and "CLI > bartleby content get".

1. RED: Write tests:
   - Create tests/test_content_query.py:
     - ABOUTME: Tests for content list/get commands — filtering, sorting, field selection.
     - test_content_list_all: lists all content with path, title, date, type, url fields
     - test_content_list_filter_type: --type blog returns only blog posts
     - test_content_list_filter_tag: --tag python returns only posts with that tag
     - test_content_list_filter_author: --author mason returns only that author's posts
     - test_content_list_filter_draft: --draft returns only drafts, --no-draft excludes them
     - test_content_list_sort: --sort date sorts by date descending
     - test_content_list_limit: --limit 5 returns at most 5 results
     - test_content_list_fields: --fields path,title returns only those fields
     - test_content_get: returns full metadata, content, word_count, links for a path
     - test_content_get_nonexistent: exit code 1 with structured error

2. GREEN: Create src/bartleby/content_query.py:
   - ABOUTME: Content query engine — filtering, sorting, field selection over site content.
   - ContentQuery dataclass (filters, sort, limit, fields)
   - query_content(config, query) -> list[ContentResult]
   - get_content(config, path) -> ContentDetail
   - Wire into cli.py as `content list` and `content get` subcommands

3. REFACTOR: Extract shared content loading logic between build pipeline and query commands.

4. Verify: `just check` passes.
```

### Step 31: Schema Introspection

**Context**: Steps 1-30 complete. Content types, authors, and taxonomies are defined in config but not programmatically queryable.

**Goal**: Add `bartleby schema` commands that let agents discover valid metadata schemas, authors, and taxonomy terms.

```text
Step 31: Schema Introspection. Steps 1-30 complete (content query works).

Refer to spec.md "CLI > bartleby schema".

1. RED: Write tests:
   - Create tests/test_schema_introspection.py:
     - ABOUTME: Tests for schema introspection — content type schemas, authors, taxonomies.
     - test_schema_content_type: schema blog returns required_fields, optional_fields,
       features (pagination, feeds, readtime, excerpt_separator)
     - test_schema_content_type_custom_metadata: custom metadata fields (like difficulty
       with choices) appear correctly in schema output
     - test_schema_authors: lists all authors with id, name, url, image, bio
     - test_schema_taxonomies: lists taxonomies with terms and counts from existing content
     - test_schema_nonexistent_type: exit code 1 with structured error
     - test_schema_json_output: all schema commands produce valid JSON

2. GREEN: Create src/bartleby/schema_introspection.py:
   - ABOUTME: Schema export for agent self-discovery — expose content type schemas, authors, terms.
   - content_type_schema(config, type_name) -> ContentTypeSchema
   - authors_schema(config) -> list[AuthorSchema]
   - taxonomies_schema(config, content_dir) -> list[TaxonomySchema]
   - Wire into cli.py as `schema <type>`, `schema authors`, `schema taxonomies`

3. REFACTOR: Ensure schema output stays in sync when config format changes.

4. Verify: `just check` passes.
```

### Step 32: Content Linting

**Context**: Steps 1-31 complete. Metadata validation exists but no broader content quality checks.

**Goal**: Add `bartleby lint` command for content quality issues beyond schema validation.

```text
Step 32: Content Linting. Steps 1-31 complete (schema introspection works).

Refer to spec.md "CLI > bartleby lint".

1. RED: Write tests:
   - Create tests/test_linting.py:
     - ABOUTME: Tests for content linting rules — broken links, orphans, missing alt, etc.
     - test_lint_broken_crossref: detects cross-reference to nonexistent .md file
     - test_lint_orphaned_page: detects page not in nav and not linked from anywhere
     - test_lint_missing_alt_text: detects images without alt text
     - test_lint_duplicate_title: detects two pages in same content type with same title
     - test_lint_unused_taxonomy: detects taxonomy term defined but never used
     - test_lint_clean_site: no issues reported for well-formed site
     - test_lint_json_output: structured output with severity, rule, file, line, message
     - test_lint_external_links: --check-external verifies external URLs (mock HTTP)

2. GREEN: Create src/bartleby/linting.py:
   - ABOUTME: Content quality checks — broken links, orphaned pages, missing alt text, duplicates.
   - Define LintRule protocol and individual rule implementations
   - LintRunner that applies all rules and collects issues
   - Each issue: LintIssue(severity, rule, file, line, message, fixable)
   - Wire into cli.py as `lint` command with --check-external and --fix flags

3. REFACTOR: Share cross-reference resolution logic with crossrefs.py.

4. Verify: `just check` passes.
```

### Step 33: Single-Page Render

**Context**: Steps 1-32 complete. Full build works but no way to render a single page for fast feedback.

**Goal**: Add `bartleby render <path>` command for rendering a single content file without full build.

```text
Step 33: Single-Page Render. Steps 1-32 complete (linting works).

Refer to spec.md "CLI > bartleby render".

1. RED: Write tests:
   - In tests/test_cli.py or tests/test_render.py:
     - test_render_html: renders page through full pipeline including template
     - test_render_markdown: --format markdown returns processed markdown
       (shortcodes expanded, cross-refs resolved, no HTML conversion)
     - test_render_metadata: --format metadata returns just parsed front matter
     - test_render_json_output: --output json returns path, url, metadata, html,
       warnings, word_count, read_time_minutes
     - test_render_nonexistent: exit code 1 with structured error
     - test_render_validation_warnings: includes warnings for the rendered page

2. GREEN: Add render command to cli.py:
   - Load config, resolve single page through pipeline subset
   - Skip full content discovery — just load the target page (and enough context
     for cross-refs and template rendering)
   - Return RenderResult dataclass

3. REFACTOR: Extract single-page render logic that can be shared with build pipeline.

4. Verify: `just check` passes.
```

### Step 34: Export Command

**Context**: Steps 1-33 complete. Content is queryable but not bulk-exportable.

**Goal**: Add `bartleby export` for bulk content export in JSONL/JSON/CSV formats.

```text
Step 34: Export Command. Steps 1-33 complete (single-page render works).

Refer to spec.md "CLI > bartleby export".

1. RED: Write tests:
   - Create tests/test_export.py:
     - ABOUTME: Tests for content export — JSONL, JSON, CSV formats with field options.
     - test_export_jsonl: produces valid JSONL (one JSON object per line)
     - test_export_json: produces valid JSON array
     - test_export_csv: produces valid CSV with headers
     - test_export_include_content: --include-content includes full markdown body
     - test_export_include_html: --include-html includes rendered HTML
     - test_export_filter_type: --type blog exports only blog content
     - test_export_to_file: --file path writes to file instead of stdout
     - test_export_metadata_only: default export includes metadata but not content

2. GREEN: Create src/bartleby/export.py:
   - ABOUTME: Content export — serialize site content to JSONL/JSON/CSV formats.
   - ExportFormat enum (jsonl, json, csv)
   - export_content(config, format, filters, include_content, include_html) -> str | bytes
   - Wire into cli.py as `export` command

3. REFACTOR: Reuse content_query.py filtering logic.

4. Verify: `just check` passes.
```

### Step 35: Skill Generation

**Context**: Steps 1-34 complete. All CLI commands work with structured output. Content is queryable and exportable.

**Goal**: Implement `bartleby generate-skill` — the core agent-first feature. Analyzes site content and generates agent skill files.

```text
Step 35: Skill Generation. Steps 1-34 complete (all CLI + agent features working).

Refer to spec.md "AI & Agent Integration > Skill Generation".

1. RED: Write tests:
   - Create tests/test_skills.py:
     - ABOUTME: Tests for agent skill generation — content analysis and skill file output.
     - test_generate_write_skill: produces valid markdown skill file with frontmatter,
       includes content type schemas, example posts, voice description
     - test_generate_review_skill: produces review skill with quality criteria
     - test_generate_ops_skill: produces ops skill with CLI command examples
     - test_content_analysis_voice: extracts voice patterns (sentence length, person,
       formality) from content corpus
     - test_content_analysis_structure: extracts heading frequency, common section titles
     - test_content_analysis_code_density: calculates code-to-prose ratio
     - test_content_analysis_length: calculates word count distribution per content type
     - test_content_analysis_taxonomy: extracts taxonomy term frequency histogram
     - test_agent_context_override: explicit ai.agent_context overrides analyzed patterns
     - test_style_guide_inclusion: ai.skills.style_guide content included in skills
     - test_skill_output_dir: skills written to configured directory
     - test_skill_dry_run: --dry-run reports what would be generated without writing
     - test_skill_force_overwrite: --force overwrites existing files
     - test_skill_generation_header: generated files include timestamp and input hash

2. GREEN: Create src/bartleby/skills.py:
   - ABOUTME: Agent skill generation — analyze site content and produce skill files for AI agents.
   - ContentAnalyzer class:
     - analyze_voice(pages) -> VoiceProfile (avg_sentence_length, person, formality)
     - analyze_structure(pages) -> StructureProfile (heading_freq, common_sections)
     - analyze_code_density(pages) -> CodeProfile (blocks_per_n_words, languages)
     - analyze_length(pages, by_type) -> LengthProfile (min, max, avg, median per type)
     - analyze_taxonomy(pages) -> TaxonomyProfile (term frequencies)
     - analyze_frontmatter(pages) -> FrontmatterProfile (field usage percentages)
   - SkillGenerator class:
     - generate_write_skill(config, analysis, examples) -> str
     - generate_review_skill(config, analysis) -> str
     - generate_ops_skill(config) -> str
   - Skill templates are Jinja2 templates bundled with the package
   - Wire into cli.py as `generate-skill` command

3. REFACTOR: Ensure content analysis is deterministic (no randomness, same input → same output).

4. Verify: `just check` passes.
```

### Step 36: Build Dry-Run

**Context**: Steps 1-35 complete. Build works but no way to preview what would change.

**Goal**: Add `--dry-run` flag to `bartleby build` that reports what would be written/modified/deleted without actually writing.

```text
Step 36: Build Dry-Run. Steps 1-35 complete (skill generation works).

1. RED: Write tests:
   - test_build_dry_run: --dry-run returns added/modified/deleted/unchanged counts
     without writing any files
   - test_build_dry_run_new_site: all files show as "added" on first build
   - test_build_dry_run_no_changes: rebuilding identical site shows all "unchanged"
   - test_build_dry_run_json: --dry-run --output json returns structured diff

2. GREEN: Add --dry-run to build command:
   - Run full pipeline but collect output paths instead of writing
   - Compare against existing site/ directory (if any)
   - Return DryRunResult with added, modified, unchanged, deleted lists

3. REFACTOR: Ensure dry-run is truly read-only (no side effects).

4. Verify: `just check` passes.
```

---

## Success Metrics

### Minimum Viable Product (after Step 10)
- `bartleby build` takes a content directory and produces valid HTML in `site/`
- Multiple content types with their own URL patterns
- Markdown rendering with all extensions (do-markdown, pymdownx, standard)
- Template rendering with lookup cascade
- Read time and excerpt extraction
- Metadata validation catches errors before build

### Feature Complete (after Step 20)
- Taxonomies with global and per-content-type pages
- Paginated listings
- Cross-reference resolution with broken link detection
- Shortcodes
- Co-located assets following page URLs
- Search index, RSS/Atom feeds, sitemap, robots.txt
- SEO meta tags (OG, Twitter, canonical)
- LLM output (llms.txt, markdown variants, JSON-LD)

### Production Ready (after Step 27)
- Plugin system with 16 hooks
- CLI with all commands (new, build, validate, serve)
- Dev server with live reload
- Material Design theme with Tailwind CSS and Alpine.js
- Icon packs with tree-shaking
- Async build pipeline for performance
- All tests passing, mypy strict, ruff clean

### Agent Ready (after Step 36)
- All CLI commands support `--output json` for structured machine-readable output
- Fully non-interactive operation via flags (no prompts when `--output json`)
- Schema introspection (`bartleby schema`) for agent self-discovery
- Content query commands (`bartleby content list/get`) for programmatic content access
- Single-page render (`bartleby render`) for fast agent feedback loops
- Content linting (`bartleby lint`) with structured, actionable output
- Content export (`bartleby export`) in JSONL/JSON/CSV for RAG and analysis
- Skill generation (`bartleby generate-skill`) that teaches agents the site's voice and conventions
- Build dry-run for impact assessment before committing changes
- Equal drivability by humans and AI agents
