# ABOUTME: Shared test fixtures for Bartleby test suite.
# Provides the sample-site path and pre-loaded config used by content tests.

from pathlib import Path

import pytest

from bartleby.config import BartlebyConfig, load_config


@pytest.fixture
def sample_site_path() -> Path:
    """Path to the on-disk sample site fixture used by content/build tests."""
    return Path(__file__).parent / "fixtures" / "site"


@pytest.fixture
def sample_config(sample_site_path: Path) -> BartlebyConfig:
    """Loaded :class:`BartlebyConfig` for the sample site fixture."""
    return load_config(sample_site_path / "bartleby.yml")
