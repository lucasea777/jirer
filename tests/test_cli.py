"""Tests for `jirer`.cli module."""
from typing import List

import pytest
from click.testing import CliRunner

import jirer
from jirer import cli


@pytest.mark.parametrize(
    "options,expected",
    [
        # ([], "jirer.cli.main"),
        (["--help"], "Usage: cli [OPTIONS]"),
        (["--version"], f"cli, version { jirer.__version__ }\n"),
    ],
)
def test_command_line_interface(options: List[str], expected: str) -> None:
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.cli, options)
    assert result.exit_code == 0
    print(result.output)
    assert expected in result.output
