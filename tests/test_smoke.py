# ABOUTME: End-to-end smoke test driving the real CLI scaffold/post/build path.
# Greps the rendered output so a green suite cannot ship a broken listing again.

from __future__ import annotations

from typing import TYPE_CHECKING

from bartleby.cli import main

if TYPE_CHECKING:
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
