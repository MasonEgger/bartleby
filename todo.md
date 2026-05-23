# Bartleby Implementation Progress

## Phase 1: Foundation

- [x] **Step 1: Project Scaffolding**
  - [x] 1.1: Create pyproject.toml with all dependencies and tool config
  - [x] 1.2: Create package structure (src/bartleby/, tests/, fixtures/)
  - [x] 1.3: Create Justfile (check, lint, typecheck, test, format)
  - [x] 1.4: Update .gitignore
  - [x] 1.5: Write smoke tests (test_init.py)
  - [x] 1.6: Verify `uv sync --dev` and `just check` pass

- [x] **Step 2: Configuration System**
  - [x] 2.1: Create test fixture configs (minimal.yml, full.yml, invalid_*.yml)
  - [x] 2.2: Write config loading and validation tests (test_config.py)
  - [x] 2.3: Implement config dataclasses and load_config (config.py)
  - [x] 2.4: Refactor — validation error messages with key paths
  - [x] 2.5: Verify `just check` passes

- [x] **Step 3: Authors System**
  - [x] 3.1: Create test fixture author files (valid.yml, minimal.yml)
  - [x] 3.2: Write author loading and resolution tests (test_authors.py)
  - [x] 3.3: Implement Author dataclass, load_authors, resolve_authors (authors.py)
  - [x] 3.4: Verify `just check` passes

## Phase 2: Content Layer

- [x] **Step 4: Content Discovery and Front Matter**
  - [x] 4.1: Create sample site fixture (tests/fixtures/site/)
  - [x] 4.2: Write content discovery tests (test_content.py)
  - [x] 4.3: Add shared fixtures to conftest.py
  - [x] 4.4: Implement Page dataclass, parse_front_matter, discover_content (content.py)
  - [x] 4.5: Verify `just check` passes

- [x] **Step 5: Metadata Validation**
  - [x] 5.1: Write metadata validation tests (test_metadata.py)
  - [x] 5.2: Implement validate_page_metadata, validate_all_metadata (metadata.py)
  - [x] 5.3: Verify `just check` passes

- [x] **Step 6: URL Generation**
  - [x] 6.1: Write URL generation tests (test_urls.py)
  - [x] 6.2: Implement generate_url, generate_all_urls (urls.py)
  - [x] 6.3: Handle edge cases (missing dates, index files)
  - [x] 6.4: Verify `just check` passes

## Phase 3: Rendering Pipeline

- [x] **Step 7: Markdown Pipeline**
  - [x] 7.1: Write markdown pipeline tests (test_markdown_pipeline.py)
  - [x] 7.2: Implement create_markdown_renderer, render_markdown (markdown_pipeline.py)
  - [x] 7.3: Verify extension ordering (fence before superfences)
  - [x] 7.4: Verify `just check` passes

- [x] **Step 8: Template System (+ customization seams)**
  - [x] 8.1: Create test fixture templates, overrides/, partials/, data/ fixtures
  - [x] 8.2: Write template system tests (test_templates.py) including overrides, partials, data, extra_css/js
  - [x] 8.3: Implement create_jinja_env with 6-level cascade (overrides/ on top, project_dir for partials/shortcodes)
  - [x] 8.4: Implement load_data_files() — YAML + TOML auto-load from data/
  - [x] 8.5: Implement build_page_context including `data`, `extra_css`, `extra_js`
  - [x] 8.6: Create theme package and minimal built-in templates
  - [x] 8.7: Create SEO/JSON-LD partials in base template
  - [x] 8.8: Verify `just check` passes

## Phase 4: First Working Build

- [x] **Step 9: Navigation System**
  - [x] 9.1: Write navigation tests (test_navigation.py)
  - [x] 9.2: Implement build_navigation, auto_generate_nav, link_pages (navigation.py)
  - [x] 9.3: Verify `just check` passes

- [x] **Step 10: Build Pipeline v1** ⭐ MVP Milestone
  - [x] 10.1: Expand test fixture site for end-to-end testing
  - [x] 10.2: Write build pipeline integration tests (test_build.py)
  - [x] 10.3: Write excerpt and readtime unit tests
  - [x] 10.4: Implement build(), extract_excerpt, calculate_readtime (build.py)
  - [x] 10.5: Create minimal PluginCollection with run_event (plugins.py)
  - [x] 10.6: Add plugin hook call sites throughout build pipeline
  - [x] 10.7: Verify `just check` passes

## Phase 5: Content Features

- [x] **Step 11: Taxonomy System**
  - [x] 11.1: Update test fixtures with taxonomy data
  - [x] 11.2: Write taxonomy tests (test_taxonomies.py)
  - [x] 11.3: Implement build_taxonomies, generate_taxonomy_pages (taxonomies.py)
  - [x] 11.4: Wire into build.py
  - [x] 11.5: Verify `just check` passes

- [x] **Step 12: Listing Pages and Pagination**
  - [x] 12.1: Write pagination tests (test_pagination.py)
  - [x] 12.2: Write listing tests (test_listings.py)
  - [x] 12.3: Implement paginate (pagination.py)
  - [x] 12.4: Implement generate_listing_pages (listings.py)
  - [x] 12.5: Wire into build.py
  - [x] 12.6: Verify `just check` passes

- [x] **Step 13: Cross-Reference Resolution**
  - [x] 13.1: Write cross-reference tests (test_crossrefs.py)
  - [x] 13.2: Implement resolve_page_crossrefs, resolve_all_crossrefs (crossrefs.py)
  - [x] 13.3: Wire into build.py
  - [x] 13.4: Verify `just check` passes

- [ ] **Step 14: Shortcode Preprocessing**
  - [ ] 14.1: Create shortcode fixture templates (project-root `shortcodes/` preferred)
  - [ ] 14.2: Write shortcode tests (test_shortcodes.py) — resolve via Jinja env from Step 8
  - [ ] 14.3: Implement process_shortcodes (shortcodes.py)
  - [ ] 14.4: Wire into build.py (before markdown rendering)
  - [ ] 14.5: Verify `just check` passes

- [ ] **Step 15: Static Files and Co-located Assets**
  - [ ] 15.1: Update test fixtures with static files
  - [ ] 15.2: Write asset copying tests (test_assets.py)
  - [ ] 15.3: Implement copy_static_files, copy_colocated_assets (assets.py)
  - [ ] 15.4: Wire into build.py
  - [ ] 15.5: Verify `just check` passes

## Phase 6: Generated Output

- [ ] **Step 16: Search Index Generation**
  - [ ] 16.1: Write search index tests (test_search.py)
  - [ ] 16.2: Implement build_search_index, write_search_index (search.py)
  - [ ] 16.3: Wire into build.py
  - [ ] 16.4: Verify `just check` passes

- [ ] **Step 17: Feed Generation**
  - [ ] 17.1: Write feed tests (test_feeds.py)
  - [ ] 17.2: Implement generate_rss, generate_atom, generate_feeds (feeds.py)
  - [ ] 17.3: Wire into build.py
  - [ ] 17.4: Verify `just check` passes

- [ ] **Step 18: Sitemap and Robots.txt**
  - [ ] 18.1: Write sitemap and robots tests (test_sitemap.py)
  - [ ] 18.2: Implement generate_sitemap, generate_robots_txt (sitemap.py)
  - [ ] 18.3: Wire into build.py
  - [ ] 18.4: Verify `just check` passes

- [ ] **Step 19: SEO Meta Tags**
  - [ ] 19.1: Write SEO tests (test_seo.py)
  - [ ] 19.2: Implement generate_og_tags, generate_twitter_tags, generate_canonical_url (seo.py)
  - [ ] 19.3: Wire into template context and update base.html
  - [ ] 19.4: Verify `just check` passes

- [ ] **Step 20: LLM Output**
  - [ ] 20.1: Write LLM output tests (test_llm.py)
  - [ ] 20.2: Implement generate_llms_txt, generate_llms_full_txt, write_markdown_variant, generate_jsonld (llm.py)
  - [ ] 20.3: Wire into build.py
  - [ ] 20.4: Verify `just check` passes

## Phase 7: Extensibility

- [ ] **Step 21: Internal Plugin Architecture + Hooks Directory**
  - [ ] 21.1: Write hook system tests (test_plugins.py) — file-convention discovery, no entry-points
  - [ ] 21.2: Create hooks/ fixture files (inject_banner.py, jinja_extras.py)
  - [ ] 21.3: Implement BasePlugin with all 16 hooks (internal use)
  - [ ] 21.4: Implement @event_priority decorator (works on methods AND module functions)
  - [ ] 21.5: Implement discover_hooks(project_dir) — globs hooks/*.py, registers module-level on_<event> functions
  - [ ] 21.6: Update PluginCollection with priority ordering
  - [ ] 21.7: Wire discover_hooks into build.py (merge with internal handlers from Step 10)
  - [ ] 21.8: Verify `just check` passes (including negative test that entry_points discovery is NOT used)

## Phase 8: CLI and Server

- [ ] **Step 22: CLI Commands**
  - [ ] 22.1: Write CLI tests (test_cli.py)
  - [ ] 22.2: Implement main, new site, new post, build, validate (cli.py)
  - [ ] 22.3: Update __main__.py entry point
  - [ ] 22.4: Verify `just check` passes

- [ ] **Step 23: Dev Server**
  - [ ] 23.1: Write dev server tests (test_server.py)
  - [ ] 23.2: Implement serve with HTTP, file watcher, WebSocket (server.py)
  - [ ] 23.3: Wire into cli.py serve command
  - [ ] 23.4: Verify `just check` passes

## Phase 9: Theme

- [ ] **Step 24: Base Material Theme**
  - [ ] 24.1: Write base theme tests (test_theme.py)
  - [ ] 24.2: Create all template files (base, page, post, list, taxonomy, 404, partials)
  - [ ] 24.3: Vendor JS assets (Alpine.js, HTMX, lunr.js)
  - [ ] 24.4: Compile base Tailwind CSS
  - [ ] 24.5: Update build.py to copy theme assets
  - [ ] 24.6: Verify `just check` passes

- [ ] **Step 25: Full Material Theme**
  - [ ] 25.1: Write comprehensive theme tests (test_theme_full.py)
  - [ ] 25.2: Style all content elements (admonitions, code, tables, tabs, etc.)
  - [ ] 25.3: Add Alpine.js components (search, sidebar, TOC, dark mode)
  - [ ] 25.4: Implement responsive design
  - [ ] 25.5: Compile final Tailwind CSS with PurgeCSS
  - [ ] 25.6: Verify `just check` passes

- [ ] **Step 26: Icon Packs and Tree-Shaking**
  - [ ] 26.1: Write icon tests (test_icons.py)
  - [ ] 26.2: Implement get_icon_path, tree_shake_icons (icons.py)
  - [ ] 26.3: Bundle sample icon SVGs
  - [ ] 26.4: Wire into build.py
  - [ ] 26.5: Verify `just check` passes

## Phase 10: Performance

- [ ] **Step 27: Async Build Pipeline**
  - [ ] 27.1: Write async build tests (test_async_build.py)
  - [ ] 27.2: Implement async_build with ProcessPoolExecutor + aiofiles
  - [ ] 27.3: Keep sync build() as fallback
  - [ ] 27.4: Update CLI to use async_build by default
  - [ ] 27.5: Verify `just check` passes
