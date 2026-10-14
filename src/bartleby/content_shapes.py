# ABOUTME: The content-type shapes `bartleby enable` can add to bartleby.yml; blog is the only one.
# One definition of the blog block, shared by `enable` and the scaffold's blog option.

"""Named content-type shapes: a ready-made block plus the taxonomies it refers to.

A shape is a template, not an instance. ``enable blog tutorials`` instantiates the
``blog`` shape under the name ``tutorials``; a site may do that any number of times.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContentShape:
    """A content-type block template.

    :ivar path_suffix: Appended to the instance name to form its ``path``
        (``posts`` makes ``tutorials/posts``).
    :ivar settings: Every other key of the block, written as given.
    :ivar taxonomies: Taxonomy name to its ``bartleby.yml`` block, for each taxonomy the
        block's ``taxonomies`` list refers to; a site that lacks one needs it added.
    """

    path_suffix: str
    settings: dict[str, object]
    taxonomies: dict[str, dict[str, str]]

    def content_type(self, name: str) -> dict[str, object]:
        """Build the ``content_types.<name>`` block for the instance called ``name``.

        :param name: The instance name, such as ``tutorials``.
        :returns: A fresh block; the caller may mutate it.
        """
        return {"path": f"{name}/{self.path_suffix}", **deepcopy(self.settings)}


BLOG_SHAPE = ContentShape(
    path_suffix="posts",
    settings={
        "readtime": True,
        "excerpt_separator": "<!-- more -->",
        "taxonomies": ["tags"],
        "feeds": ["rss", "atom"],
    },
    taxonomies={"tags": {"slug_format": "{slug}"}},
)

CONTENT_SHAPES: dict[str, ContentShape] = {"blog": BLOG_SHAPE}
