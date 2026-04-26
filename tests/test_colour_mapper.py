"""Tests for colourmapper.ColourMapper."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from colourmapper.ColourMapper import ColourMapper, ColourResult

_TEST_COLORS = {
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "black": "#000000",
    "white": "#FFFFFF",
    "dark red": "#8B0000",
}


@pytest.fixture()
def mapper(tmp_path: Path) -> ColourMapper:
    """Return a ColourMapper backed by a temporary colour file, restoring class maps after the test."""
    saved_name_to_hex = dict(ColourMapper.NAME_TO_HEX)
    saved_hex_to_name = dict(ColourMapper.HEX_TO_NAME)

    colour_file = tmp_path / "colours.json"
    colour_file.write_text(json.dumps(_TEST_COLORS))

    with patch.object(ColourMapper, "MAPPING_FILE", colour_file):
        ColourMapper.NAME_TO_HEX = {}
        ColourMapper.HEX_TO_NAME = {}
        instance = ColourMapper()

    yield instance

    ColourMapper.NAME_TO_HEX = saved_name_to_hex
    ColourMapper.HEX_TO_NAME = saved_hex_to_name


class TestColourResult:
    def test_dataclass_fields(self) -> None:
        result = ColourResult(found=True, hex_value="#ff0000", name="red")
        assert result.found is True
        assert result.hex_value == "#ff0000"
        assert result.name == "red"


class TestColourMapperInit:
    def test_loads_colours(self, mapper: ColourMapper) -> None:
        assert "red" in mapper.name_to_hex
        assert mapper.name_to_hex["red"] == "#FF0000"

    def test_no_space_variant(self, mapper: ColourMapper) -> None:
        assert "darkred" in mapper.name_to_hex

    def test_reverse_map(self, mapper: ColourMapper) -> None:
        assert mapper.hex_to_name.get("#ff0000") == "red"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.json"
        with patch.object(ColourMapper, "MAPPING_FILE", missing):
            ColourMapper.NAME_TO_HEX = {}
            ColourMapper.HEX_TO_NAME = {}
            with pytest.raises(ColourMapper.MissingMappingFile):
                ColourMapper()


class TestHexify:
    def test_full_hex_with_hash(self) -> None:
        assert ColourMapper.hexify("#FF0000") == "#ff0000"

    def test_full_hex_without_hash(self) -> None:
        assert ColourMapper.hexify("FF0000") == "#ff0000"

    def test_shorthand_hex(self) -> None:
        assert ColourMapper.hexify("#f00") == "#ff0000"

    def test_shorthand_hex_without_hash(self) -> None:
        assert ColourMapper.hexify("f00") == "#ff0000"

    def test_invalid_returns_none(self) -> None:
        assert ColourMapper.hexify("XYZ") is None
        assert ColourMapper.hexify("#ZZZZZZ") is None
        assert ColourMapper.hexify("12345") is None
        assert ColourMapper.hexify("") is None


class TestHexToRgb:
    def test_red(self) -> None:
        assert ColourMapper._hex_to_rgb("FF0000") == (255, 0, 0)

    def test_green_with_hash(self) -> None:
        assert ColourMapper._hex_to_rgb("#00FF00") == (0, 255, 0)

    def test_blue_lowercase(self) -> None:
        assert ColourMapper._hex_to_rgb("0000ff") == (0, 0, 255)


class TestColourDistance:
    def test_same_colour_is_zero(self) -> None:
        assert ColourMapper._calculate_colour_distance((255, 0, 0), (255, 0, 0)) == 0.0

    def test_red_vs_green(self) -> None:
        d = ColourMapper._calculate_colour_distance((255, 0, 0), (0, 255, 0))
        assert abs(d - 360.62) < 1.0

    def test_triangle_inequality(self) -> None:
        a = (255, 0, 0)
        b = (0, 255, 0)
        c = (0, 0, 255)
        d_ab = ColourMapper._calculate_colour_distance(a, b)
        d_bc = ColourMapper._calculate_colour_distance(b, c)
        d_ac = ColourMapper._calculate_colour_distance(a, c)
        assert d_ac <= d_ab + d_bc + 1e-9


class TestGetClosestColour:
    def test_exact_match_red(self, mapper: ColourMapper) -> None:
        hex_val, name = ColourMapper.get_closest_colour("#FF0000")
        assert name == "red"

    def test_near_red(self, mapper: ColourMapper) -> None:
        _, name = ColourMapper.get_closest_colour("#FF0001")
        assert name == "red"

    def test_returns_result(self, mapper: ColourMapper) -> None:
        hex_val, name = ColourMapper.get_closest_colour("#7F007F")
        assert name is not None
        assert hex_val.startswith("#")


class TestGetColourName:
    def test_name_lookup(self, mapper: ColourMapper) -> None:
        result = ColourMapper.get_colour_name("red")
        assert result.found is True
        assert result.hex_value == "#FF0000"
        assert result.name == "red"

    def test_case_insensitive_name(self, mapper: ColourMapper) -> None:
        result = ColourMapper.get_colour_name("rEd")
        assert result.found is True

    def test_no_space_name(self, mapper: ColourMapper) -> None:
        result = ColourMapper.get_colour_name("darkred")
        assert result.found is True
        assert result.hex_value == "#8B0000"

    def test_hex_lookup(self, mapper: ColourMapper) -> None:
        result = ColourMapper.get_colour_name("#FF0000")
        assert result.found is True
        assert result.name == "red"

    def test_hex_without_hash(self, mapper: ColourMapper) -> None:
        result = ColourMapper.get_colour_name("FF0000")
        assert result.found is True

    def test_shorthand_hex(self, mapper: ColourMapper) -> None:
        result = ColourMapper.get_colour_name("#F00")
        assert result.found is True
        assert result.name == "red"

    def test_unknown_name_not_found(self, mapper: ColourMapper) -> None:
        result = ColourMapper.get_colour_name("Magenta")
        assert result.found is False

    def test_near_match_found(self, mapper: ColourMapper) -> None:
        result = ColourMapper.get_colour_name("#FE0000")
        assert result.found is True
        assert result.name == "red"

    def test_get_color_name_alias(self, mapper: ColourMapper) -> None:
        result = ColourMapper.get_color_name("red")
        assert result.found is True
