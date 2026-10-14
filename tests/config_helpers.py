# ABOUTME: Shared helpers for tests that edit or read a bartleby.yml fixture.
# Replaces top-level keys without duplicating them, and uncomments the full config's examples.

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from bartleby.config_edit import set_key

if TYPE_CHECKING:
    from pathlib import Path


def replace_top_level_keys(config_path: Path, extra: str) -> None:
    """Write each top-level key of the YAML text ``extra`` into ``config_path``.

    A key the file already holds is replaced whole, which is what appending the text
    used to do through PyYAML's last-key-wins reading before duplicate keys were rejected.
    """
    text = config_path.read_text(encoding="utf-8")
    for key, value in yaml.safe_load(extra).items():
        text = set_key(text, key, value)
    config_path.write_text(text, encoding="utf-8")


def uncomment_examples(text: str) -> str:
    """Return ``text`` with the commented-out example blocks turned back into live YAML.

    The full config writes ``content_types`` and ``taxonomies`` as a commented-out
    example (``# content_types:``, ``#   example:``). A comment line whose text starts
    with one of those keys, or with indentation, belongs to such a block; a description
    comment starts with a word and stays a comment.
    """
    lines: list[str] = []
    for line in text.splitlines():
        body = line.removeprefix("# ")
        if line.startswith("# ") and (
            body.startswith(("content_types:", "taxonomies:")) or body[:1].isspace()
        ):
            lines.append(body)
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"
