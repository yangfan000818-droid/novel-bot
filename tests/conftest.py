"""Shared test fixtures."""

import pytest
from click.testing import CliRunner


@pytest.fixture()
def cli_runner() -> CliRunner:
    """Provide a Click CliRunner instance."""
    return CliRunner()
