# ABOUTME: End-to-end smoke test driving the real CLI scaffold/post/build path.
# Greps the rendered output so a green suite cannot ship a broken listing again.

from __future__ import annotations

import json
import threading
import urllib.request
from typing import TYPE_CHECKING

from bartleby.cli import main
from bartleby.server import RELOAD_SNIPPET, DevServer

if TYPE_CHECKING:
    import socketserver
    from pathlib import Path

    import pytest


def _write_published_post(project: Path, *, title: str, slug: str) -> None:
    """Overwrite a scaffolded post so it is published and carries an author byline.

    ``bartleby new post`` always writes ``draft: true`` with no author. The smoke
    test needs a published post with a resolvable author so the build emits it and
    the post template renders a byline.
    """
    post = project / "content" / "blog" / "posts" / f"{slug}.md"
    post.write_text(
        f'---\ntitle: "{title}"\n'
        "date: 2026-03-01\n"
        "draft: false\n"
        "authors: [default]\n"
        "tags: [python]\n"
        "---\n\n"
        "The quick brown fox jumps over the lazy dog.\n",
        encoding="utf-8",
    )


def test_scaffold_post_build_renders_title_byline_and_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh site -> published post -> build produces HTML with the post visible.

    Asserts against the real rendered output (not just file existence): the post
    title appears in its own page, a non-empty author byline is rendered, and the
    post is linked from the blog listing page.
    """
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])

    project = tmp_path / "mysite"
    monkeypatch.chdir(project)
    main(["new", "post", "Hello Smoke", "--type", "blog"])
    _write_published_post(project, title="Hello Smoke", slug="hello-smoke")

    main(["build"])

    post_html = (project / "site" / "blog" / "posts" / "hello-smoke" / "index.html").read_text(
        encoding="utf-8"
    )
    # The post title is rendered into its own page.
    assert "Hello Smoke" in post_html
    # A non-empty author byline appears (default author name from .authors.yml).
    assert "By" in post_html
    assert "Site Author" in post_html

    listing_html = (project / "site" / "blog" / "index.html").read_text(encoding="utf-8")
    # The post is linked from the listing, grepping the real anchor href.
    assert 'href="/blog/posts/hello-smoke/"' in listing_html
    assert "Hello Smoke" in listing_html


def test_scaffold_build_drops_draft_posts_from_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A scaffolded draft post (the default) is absent from the built listing."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])

    project = tmp_path / "mysite"
    monkeypatch.chdir(project)
    # Left as the default draft: true; no edit.
    main(["new", "post", "Secret Draft", "--type", "blog"])

    main(["build"])

    listing_html = (project / "site" / "blog" / "index.html").read_text(encoding="utf-8")
    assert "Secret Draft" not in listing_html
    assert not (project / "site" / "blog" / "posts" / "secret-draft").exists()


def _write_post(project: Path, *, slug: str, title_frontmatter: str, body: str) -> None:
    """Write a post directly, giving the caller full control over the raw ``title:`` value.

    Unlike ``_write_published_post``, ``title_frontmatter`` is the literal YAML
    text after ``title: ``, quoting included, so a caller can exercise a title
    containing an embedded double quote (R9) without the helper mangling it.
    """
    post = project / "content" / "blog" / "posts" / f"{slug}.md"
    post.write_text(
        f"---\ntitle: {title_frontmatter}\n"
        "date: 2026-03-01\n"
        "draft: false\n"
        "authors: [default]\n"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )


def _write_draft_bundle_with_asset(project: Path, *, slug: str) -> None:
    """Write a draft page bundle (``index.md`` plus a co-located asset) (R7).

    A production build must write neither the draft page nor ``photo.png``;
    the dev server (which always includes drafts) writes both.
    """
    bundle_dir = project / "content" / "blog" / "posts" / slug
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "index.md").write_text(
        '---\ntitle: "Secret Draft Bundle"\n'
        "date: 2026-03-01\n"
        "draft: true\n"
        "authors: [default]\n"
        "---\n\n"
        "This draft bundle's asset must never reach a production build.\n",
        encoding="utf-8",
    )
    (bundle_dir / "photo.png").write_bytes(b"stub-png-bytes")


def _extract_jsonld(html: str) -> dict[str, object]:
    """Pull the ``application/ld+json`` block out of rendered page HTML and parse it."""
    marker = '<script type="application/ld+json">'
    start = html.index(marker) + len(marker)
    end = html.index("</script>", start)
    payload: dict[str, object] = json.loads(html[start:end])
    return payload


def _start_running_server(
    server: DevServer,
) -> tuple[threading.Thread, int, socketserver.TCPServer]:
    """Start ``server.run`` on a daemon thread and block until it is listening.

    :returns: The worker thread, the bound ephemeral port, and the live server.
    """
    bound: dict[str, object] = {}
    listening = threading.Event()

    def on_ready(httpd: socketserver.TCPServer) -> None:
        bound["port"] = httpd.server_address[1]
        bound["httpd"] = httpd
        listening.set()

    worker = threading.Thread(target=lambda: server.run(ready=on_ready), daemon=True)
    worker.start()
    assert listening.wait(timeout=10), "server never started listening"
    return worker, bound["port"], bound["httpd"]  # type: ignore[return-value]


def test_scaffold_build_and_serve_compose_output_dir_draft_and_quoted_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The three cross-cutting remediation fixes hold together through build and serve.

    Exercises, on one scaffolded site, through the real CLI entry point and
    the real dev server:

    - R4: a custom ``output_dir`` is where the build writes and where
      ``DevServer.run`` serves from, not ``site/``.
    - R7: a draft page bundle and its co-located asset are both absent from a
      production build (the publication boundary holds end to end).
    - R9: a title containing a double quote round-trips through valid JSON-LD.

    A page-to-page ``.md`` crossref is also included and asserted to resolve
    to the target's output URL in the rendered HTML.
    """
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])

    project = tmp_path / "mysite"
    config_path = project / "bartleby.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\noutput_dir: published\n",
        encoding="utf-8",
    )

    _write_post(
        project,
        slug="second-post",
        title_frontmatter='"Second Post"',
        body="The second post that the quoted-title post links to.",
    )
    _write_post(
        project,
        slug="quoted-title-post",
        title_frontmatter='"Say \\"Hello\\" Smoke"',
        body="See the [second post](second-post.md) for more.",
    )
    _write_draft_bundle_with_asset(project, slug="secret-draft-bundle")

    monkeypatch.chdir(project)
    main(["build"])

    # R4: the build wrote the configured output_dir, not `site/`.
    output_dir = project / "published"
    assert output_dir.exists()
    assert not (project / "site").exists()

    # R7: the draft bundle and its co-located asset are both absent.
    draft_dir = output_dir / "blog" / "posts" / "secret-draft-bundle"
    assert not draft_dir.exists()
    assert not (draft_dir / "photo.png").exists()

    # R9: the quoted title's JSON-LD block is valid JSON and round-trips the title.
    post_html = (output_dir / "blog" / "posts" / "quoted-title-post" / "index.html").read_text(
        encoding="utf-8"
    )
    jsonld = _extract_jsonld(post_html)
    assert jsonld["headline"] == 'Say "Hello" Smoke'

    # The .md crossref resolved to the target page's real output URL.
    second_post_html = (output_dir / "blog" / "posts" / "second-post" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'href="/blog/posts/second-post/"' in post_html
    assert "Second Post" in second_post_html

    # R4 + R5 groundwork: DevServer.run() serves the configured output_dir
    # and carries the live-reload snippet (serve mode only).
    server = DevServer(config_path, host="127.0.0.1", port=0, dirty=False)
    worker, port, httpd = _start_running_server(server)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as response:
            served_index = response.read().decode("utf-8")
    finally:
        httpd.shutdown()
        worker.join(timeout=10)
    assert not worker.is_alive()

    assert (output_dir / "index.html").exists()
    assert RELOAD_SNIPPET in served_index
