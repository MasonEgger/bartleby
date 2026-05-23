# ABOUTME: Tests for author loading, validation, and resolution.
# Covers .authors.yml parsing, missing-file handling, and key resolution.

from pathlib import Path

import pytest

from bartleby.authors import Author, AuthorError, load_authors, resolve_authors

FIXTURES = Path(__file__).parent / "fixtures" / "authors"


def test_load_valid_authors() -> None:
    """A complete authors file populates every Author field for each entry."""
    authors = load_authors(FIXTURES / "valid.yml")
    assert set(authors.keys()) == {"mason", "guest"}
    assert authors["mason"].name == "Mason Egger"
    assert authors["mason"].description == "Developer Advocate & Python enthusiast"
    assert authors["mason"].avatar == "https://example.com/avatar.jpg"
    assert authors["mason"].url == "https://masonegger.com"
    assert authors["guest"].name == "Guest Author"
    assert authors["guest"].url is None
    assert authors["guest"].avatar is None


def test_load_minimal_author() -> None:
    """An author entry with only ``name`` parses with other fields as ``None``."""
    authors = load_authors(FIXTURES / "minimal.yml")
    assert authors["solo"].name == "Solo Author"
    assert authors["solo"].description is None
    assert authors["solo"].avatar is None
    assert authors["solo"].url is None


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    """Pointing at a nonexistent authors file returns an empty mapping."""
    assert load_authors(tmp_path / "does-not-exist.yml") == {}


def test_author_missing_name_raises() -> None:
    """An author entry without a ``name`` field raises :class:`AuthorError`."""
    with pytest.raises(AuthorError) as exc:
        load_authors(FIXTURES / "invalid_missing_name.yml")
    message = str(exc.value)
    assert "name" in message
    assert "broken" in message


def test_resolve_valid_keys() -> None:
    """Resolving known keys returns the matching Author objects in input order."""
    authors = load_authors(FIXTURES / "valid.yml")
    resolved = resolve_authors(["mason", "guest"], authors)
    assert len(resolved) == 2
    assert resolved[0].key == "mason"
    assert resolved[1].key == "guest"


def test_resolve_missing_key_raises() -> None:
    """Resolving an unknown key raises :class:`AuthorError` naming the key."""
    authors = load_authors(FIXTURES / "valid.yml")
    with pytest.raises(AuthorError) as exc:
        resolve_authors(["unknown"], authors)
    assert "unknown" in str(exc.value)


def test_resolve_empty_keys() -> None:
    """Resolving an empty key list returns an empty list."""
    authors = load_authors(FIXTURES / "valid.yml")
    assert resolve_authors([], authors) == []


def test_author_dataclass_key_field() -> None:
    """Loaded Author objects retain their YAML key in the ``key`` attribute."""
    authors = load_authors(FIXTURES / "valid.yml")
    assert isinstance(authors["mason"], Author)
    assert authors["mason"].key == "mason"
