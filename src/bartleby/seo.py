# ABOUTME: SEO meta tag generation — Open Graph, Twitter Cards, canonical URLs.
# Produces structured tag dicts the base template iterates over.

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bartleby.config import SiteConfig
    from bartleby.content import Page


def generate_og_tags(page: Page, site: SiteConfig) -> dict[str, str]:
    """Generate the Open Graph meta tag dictionary for ``page``."""
    description = page.description or site.description or ""
    image = _resolve_image(page, site)
    og_type = "article" if page.content_type_name is not None else "website"
    tags: dict[str, str] = {
        "og:title": page.title,
        "og:description": description,
        "og:type": og_type,
        "og:url": _absolute(site.url, page.output_url),
    }
    if image:
        tags["og:image"] = image
    if og_type == "article" and page.date is not None:
        tags["article:published_time"] = page.date.isoformat()
    return tags


def generate_twitter_tags(page: Page, site: SiteConfig) -> dict[str, str]:
    """Generate the Twitter Card meta tag dictionary for ``page``."""
    description = page.description or site.description or ""
    image = _resolve_image(page, site)
    tags: dict[str, str] = {
        "twitter:card": "summary_large_image",
        "twitter:title": page.title,
        "twitter:description": description,
    }
    if image:
        tags["twitter:image"] = image
    if site.twitter:
        tags["twitter:site"] = site.twitter
    return tags


def generate_canonical_url(page: Page, site: SiteConfig) -> str:
    """Build the canonical URL by joining ``site.url`` with ``page.output_url``."""
    return _absolute(site.url, page.output_url)


def generate_all_meta_tags(page: Page, site: SiteConfig) -> dict[str, object]:
    """Bundle OG, Twitter, and canonical URL into one payload for templates."""
    return {
        "og": generate_og_tags(page, site),
        "twitter": generate_twitter_tags(page, site),
        "canonical": generate_canonical_url(page, site),
    }


def _resolve_image(page: Page, site: SiteConfig) -> str | None:
    """Resolve the OG/Twitter image — page front matter first, then site default."""
    image_raw = page.custom_metadata.get("image")
    image = image_raw if isinstance(image_raw, str) else None
    if image is None:
        image = site.default_image
    if image is None:
        return None
    if image.startswith("http://") or image.startswith("https://"):
        return image
    return _absolute(site.url, image)


def _absolute(site_url: str, path: str) -> str:
    """Join site URL and path with exactly one ``/`` between them."""
    return site_url.rstrip("/") + "/" + path.lstrip("/")
