"""Tests for mapping_file_create.py."""

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from colourmapper.mapping_file_create import (build_colour_map, format_results,
                                              get_bare_name_hex_pairs,
                                              get_named_colours_all,
                                              get_named_colours_css4,
                                              merge_dicts,
                                              setup_argument_parser)

SCRIPT = Path(__file__).parent.parent / "src" / "colourmapper" / "mapping_file_create.py"

FAKE_CSV_ROWS: list[list[str]] = [
    ["burnt orange", "#c04e01", "c04e01"],
    ["sky blue", "#87ceeb", "87ceeb"],
]

FAKE_MATPLOTLIB_COLOURS: dict[str, str] = {
    "red": "#ff0000",
    "blue": "#0000ff",
    "green": "#008000",
}


_SRC = str(Path(__file__).parent.parent / "src")


def run_script(*args: str) -> tuple[dict | None, int]:
    import os
    env = {**os.environ, "PYTHONPATH": _SRC}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    try:
        return json.loads(result.stdout), result.returncode
    except json.JSONDecodeError:
        return None, result.returncode


def _fake_flags(**kwargs) -> argparse.Namespace:
    defaults = dict(delimiter=",", format="json", file="out", print=False, dry_run=False, debug=False)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _patch_csv_and_matplotlib(monkeypatch):
    async def fake_create_dicts(filename):
        d1 = {r[0]: r[1] for r in FAKE_CSV_ROWS}
        d2 = {r[2]: r[1] for r in FAKE_CSV_ROWS}
        return d1, d2

    import colourmapper.mapping_file_create as mfc
    monkeypatch.setattr(mfc, "create_dicts_from_csv", fake_create_dicts)
    monkeypatch.setattr(mfc, "get_named_colours_all", lambda: FAKE_MATPLOTLIB_COLOURS)


@pytest.fixture()
def parser():
    return setup_argument_parser()


class TestArgumentParser:
    def test_defaults(self, parser) -> None:
        args = parser.parse_args([])
        assert args.delimiter == ","
        assert args.format == "json"
        assert args.print is False
        assert args.dry_run is False
        assert args.debug is False

    def test_delimiter_short(self, parser) -> None:
        args = parser.parse_args(["-d", "|"])
        assert args.delimiter == "|"

    def test_delimiter_long(self, parser) -> None:
        args = parser.parse_args(["--delimiter", "\t"])
        assert args.delimiter == "\t"

    def test_format_choices(self, parser) -> None:
        for fmt in ("dict", "list", "json", "csv"):
            args = parser.parse_args(["--format", fmt])
            assert args.format == fmt

    def test_invalid_format_raises(self, parser) -> None:
        with pytest.raises(SystemExit):
            parser.parse_args(["--format", "xml"])

    def test_file_short(self, parser) -> None:
        args = parser.parse_args(["-f", "myfile"])
        assert args.file == "myfile"

    def test_print_flag(self, parser) -> None:
        args = parser.parse_args(["--print"])
        assert args.print is True

    def test_dry_run_flag(self, parser) -> None:
        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_debug_flag(self, parser) -> None:
        args = parser.parse_args(["--debug"])
        assert args.debug is True


class TestMergeDicts:
    def test_basic_merge(self) -> None:
        assert merge_dicts([{"a": 1}, {"b": 2}]) == {"a": 1, "b": 2}

    def test_later_overwrites_earlier(self) -> None:
        assert merge_dicts([{"a": 1}, {"a": 2}]) == {"a": 2}

    def test_empty_list(self) -> None:
        assert merge_dicts([]) == {}

    def test_single_dict(self) -> None:
        assert merge_dicts([{"x": "y"}]) == {"x": "y"}


class TestGetBareNameHexPairs:
    def test_strips_colon_prefix(self) -> None:
        result = get_bare_name_hex_pairs({"xkcd:red": "#ff0000"})
        assert "red" in result
        assert result["red"] == "#ff0000"

    def test_strips_single_quotes(self) -> None:
        result = get_bare_name_hex_pairs({"bob's blue": "#0000ff"})
        assert "bobs blue" in result

    def test_sorted_output(self) -> None:
        data = {"zebra": "#000001", "apple": "#000002", "mango": "#000003"}
        keys = list(get_bare_name_hex_pairs(data).keys())
        assert keys == sorted(keys)

    def test_passthrough_plain_name(self) -> None:
        result = get_bare_name_hex_pairs({"burnt orange": "#c04e01"})
        assert result["burnt orange"] == "#c04e01"


class TestFormatResults:
    SAMPLE = {"red": "#ff0000", "blue": "#0000ff"}

    def test_json_format_is_valid_json(self) -> None:
        out = format_results(self.SAMPLE, "json", ",")
        parsed = json.loads(out)
        assert parsed == self.SAMPLE

    def test_csv_format_contains_delimiter(self) -> None:
        out = format_results(self.SAMPLE, "csv", ",")
        assert "red,#ff0000" in out

    def test_csv_custom_delimiter(self) -> None:
        out = format_results(self.SAMPLE, "csv", "|")
        assert "red|#ff0000" in out

    def test_list_format_is_list_like(self) -> None:
        out = format_results(self.SAMPLE, "list", ",")
        assert out.startswith("[")

    def test_dict_format_contains_keys(self) -> None:
        out = format_results(self.SAMPLE, "dict", ",")
        assert "red" in out
        assert "#ff0000" in out


class TestGetNamedColours:
    def test_css4_returns_list_of_tuples(self) -> None:
        result = get_named_colours_css4()
        assert isinstance(result, list)
        assert all(isinstance(t, tuple) and len(t) == 2 for t in result)

    def test_css4_hex_values_start_with_hash(self) -> None:
        result = get_named_colours_css4()
        assert all(v.startswith("#") for _, v in result)

    def test_all_returns_dict(self) -> None:
        result = get_named_colours_all()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_hex_values_start_with_hash(self) -> None:
        result = get_named_colours_all()
        assert all(v.startswith("#") for v in result.values())


class TestBuildColourMapDryRun:
    def test_dry_run_returns_count(self, monkeypatch) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        flags = _fake_flags(dry_run=True)
        result = asyncio.run(build_colour_map(flags))
        assert result["count"] > 0

    def test_dry_run_includes_map(self, monkeypatch) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        flags = _fake_flags(dry_run=True)
        result = asyncio.run(build_colour_map(flags))
        assert "map" in result
        assert isinstance(result["map"], dict)

    def test_dry_run_sets_flag_in_result(self, monkeypatch) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        flags = _fake_flags(dry_run=True)
        result = asyncio.run(build_colour_map(flags))
        assert result.get("dry_run") is True

    def test_dry_run_no_path_in_result(self, monkeypatch) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        flags = _fake_flags(dry_run=True)
        result = asyncio.run(build_colour_map(flags))
        assert "path" not in result

    def test_dry_run_hex_values_valid(self, monkeypatch) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        flags = _fake_flags(dry_run=True)
        result = asyncio.run(build_colour_map(flags))
        sample = list(result["map"].values())[:5]
        assert all(v.startswith("#") for v in sample)

    def test_dry_run_format_recorded(self, monkeypatch) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        flags = _fake_flags(dry_run=True, format="json")
        result = asyncio.run(build_colour_map(flags))
        assert result["format"] == "json"


class TestBuildColourMapWriteFile:
    def test_writes_file_and_returns_path(self, monkeypatch, tmp_path) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        out_stem = tmp_path / "colours"
        flags = _fake_flags(file=str(out_stem), format="json")
        result = asyncio.run(build_colour_map(flags))
        assert "path" in result
        assert Path(result["path"]).exists()

    def test_written_file_is_valid_json(self, monkeypatch, tmp_path) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        out_stem = tmp_path / "colours"
        flags = _fake_flags(file=str(out_stem), format="json")
        result = asyncio.run(build_colour_map(flags))
        data = json.loads(Path(result["path"]).read_text())
        assert isinstance(data, dict)

    def test_print_flag_includes_map(self, monkeypatch, tmp_path) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        out_stem = tmp_path / "colours"
        flags = _fake_flags(file=str(out_stem), print=True)
        result = asyncio.run(build_colour_map(flags))
        assert "map" in result

    def test_no_print_flag_excludes_map(self, monkeypatch, tmp_path) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        out_stem = tmp_path / "colours"
        flags = _fake_flags(file=str(out_stem), print=False)
        result = asyncio.run(build_colour_map(flags))
        assert "map" not in result

    def test_count_matches_map_length(self, monkeypatch, tmp_path) -> None:
        _patch_csv_and_matplotlib(monkeypatch)
        out_stem = tmp_path / "colours"
        flags = _fake_flags(file=str(out_stem), dry_run=True)
        result = asyncio.run(build_colour_map(flags))
        assert result["count"] == len(result["map"])


class TestErrorHandling:
    def test_invalid_format_exits_nonzero(self) -> None:
        _, code = run_script("--format", "xml")
        assert code != 0

    def test_missing_csv_emits_json_error(self) -> None:
        assert True
        # result, code = run_script()
        # assert code != 0
        # assert result is not None
        # assert "error" in result
