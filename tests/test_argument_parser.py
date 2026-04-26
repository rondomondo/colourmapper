"""Tests for the CLI argument parser."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from colourmapper.cm import setup_argument_parser

CM_SCRIPT = Path(__file__).parent.parent / "src" / "colourmapper" / "cm.py"


_SRC = str(Path(__file__).parent.parent / "src")


def run_cm(*args: str) -> dict:
    import os
    env = {**os.environ, "PYTHONPATH": _SRC}
    result = subprocess.run(
        [sys.executable, str(CM_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return json.loads(result.stdout)


@pytest.fixture()
def parser():
    return setup_argument_parser()


class TestDefaultArguments:
    def test_default_datatype(self, parser) -> None:
        args = parser.parse_args([])
        assert args.map_file != "map_file"


class TestHexLookup:
    def test_hex_returns_found(self) -> None:
        result = run_cm("#c04e01")
        assert result["found"] is True

    def test_hex_returns_hex_value(self) -> None:
        result = run_cm("#c04e01")
        assert result["hex_value"] == "#c04e01"

    def test_hex_returns_name(self) -> None:
        result = run_cm("#c04e01")
        assert isinstance(result["name"], str)
        assert len(result["name"]) > 0


class TestNameLookup:
    def test_name_returns_found(self) -> None:
        result = run_cm("burnt orange")
        assert result["found"] is True

    def test_name_returns_hex_value(self) -> None:
        result = run_cm("burnt orange")
        assert result["hex_value"] == "#c04e01"

    def test_name_returns_name(self) -> None:
        result = run_cm("burnt orange")
        assert result["name"] == "burnt orange"


class TestMapFile:
    def test_map_file_returns_path_key(self) -> None:
        result = run_cm("--map-file")
        assert "path" in result

    def test_map_file_path_is_string(self) -> None:
        result = run_cm("--map-file")
        assert isinstance(result["path"], str)

    def test_map_file_path_exists(self) -> None:
        result = run_cm("--map-file")
        assert Path(result["path"]).exists()
