# ABOUTME: Shared helpers that read the entries out of RSS and Atom feed text.
# The feed tests and the first-run correctness tests parse feeds the same way.

from __future__ import annotations

import xml.etree.ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"


def rss_entries(xml: str) -> list[tuple[str | None, str | None]]:
    """The (title, link) pair of every RSS item, in document order."""
    return [
        (item.findtext("title"), item.findtext("link"))
        for item in ET.fromstring(xml).findall("channel/item")
    ]


def atom_entries(xml: str) -> list[tuple[str | None, str | None]]:
    """The (title, alternate href) pair of every Atom entry, in document order."""
    return [
        (entry.findtext(f"{ATOM}title"), entry.findall(f"{ATOM}link")[0].get("href"))
        for entry in ET.fromstring(xml).findall(f"{ATOM}entry")
    ]
