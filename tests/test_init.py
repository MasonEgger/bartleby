# ABOUTME: Smoke tests verifying the bartleby package is importable.
# Ensures the package structure is valid and version is exposed.

import bartleby


def test_version_is_string() -> None:
    assert isinstance(bartleby.__version__, str)


def test_version_not_empty() -> None:
    assert len(bartleby.__version__) > 0
