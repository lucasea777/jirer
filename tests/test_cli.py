"""Tests for `jirer`.main module."""
from typing import List

import pytest
from click.testing import CliRunner

import jirer
from jirer import cli


@pytest.mark.parametrize(
    "options,expected",
    [
        # ([], "jirer.main.main"),
        (["--help"], "Usage: main [OPTIONS]"),
        (["--version"], f"main, version { jirer.__version__ }\n"),
    ],
)
def test_command_line_interface(options: List[str], expected: str) -> None:
    """Test the main."""
    runner = CliRunner()
    result = runner.invoke(cli.main, options)
    assert result.exit_code == 0
    print(result.output)
    assert expected in result.output
