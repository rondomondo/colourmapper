#!/usr/bin/env python

import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

from colourmapper.ColourMapper import ColourMapper as ColorMapper


@dataclass
class ColorResult:
    """Represents the result of a color mapping operation."""
    found: bool
    hex_value: str
    name: str


@pytest.fixture(autouse=True)
def reset_color_mapper():
    yield
    ColorMapper.NAME_TO_HEX = {}
    ColorMapper.HEX_TO_NAME = {}


@pytest.fixture()
def color_mapper():
    return ColorMapper()


class TestInitColorMap:
    def test_init_color_map(self, color_mapper):
        """Test color map initialization."""
        assert color_mapper.name_to_hex["Red"].lower() == "#ff0000"
        assert color_mapper.name_to_hex["DarkRed"].lower() == "#840000"
        assert color_mapper.hex_to_name["#ff0000"].lower() == "red"


class TestHexify:
    def test_hexify_valid_inputs(self):
        """Test hexify method with valid inputs."""
        assert ColorMapper.hexify("FF0000") == "#ff0000"
        assert ColorMapper.hexify("#FF0000") == "#ff0000"
        assert ColorMapper.hexify("f00") == "#ff0000"
        assert ColorMapper.hexify("#f00") == "#ff0000"

    def test_hexify_invalid_inputs(self):
        """Test hexify method with invalid inputs."""
        assert ColorMapper.hexify("XYZ") is None
        assert ColorMapper.hexify("#ZZZZZZ") is None
        assert ColorMapper.hexify("12345") is None
        assert ColorMapper.hexify("") is None

    def test_hex_to_rgb_conversion(self):
        """Test conversion from hex to RGB."""
        assert ColorMapper._hex_to_rgb("FF0000") == (255, 0, 0)
        assert ColorMapper._hex_to_rgb("#00FF00") == (0, 255, 0)
        assert ColorMapper._hex_to_rgb("0000ff") == (0, 0, 255)


class TestColorDistance:
    def test_calculate_color_distance(self):
        """Test color distance calculation."""
        assert ColorMapper._calculate_color_distance((255, 0, 0), (255, 0, 0)) == 0
        assert ColorMapper._calculate_color_distance(
            (255, 0, 0), (0, 255, 0)) == pytest.approx(
            math.sqrt(130050), abs=0.01)


class TestClosestColor:
    def test_get_closest_color(self):
        """Test finding the closest color."""
        closest_hex, closest_name = ColorMapper.get_closest_color("#FF0000")
        assert closest_hex.lower() == "#ff0000"
        assert closest_name.lower() == "red"

        closest_hex, closest_name = ColorMapper.get_closest_color("#FF0003")
        assert closest_name.lower() == "fire engine red"

        closest_hex, closest_name = ColorMapper.get_closest_color("#7F007F")
        assert closest_name is not None


class TestColorNameByName:
    def test_get_color_name_by_name(self, color_mapper):
        """Test getting color info by name."""
        result = color_mapper.get_color_name("Redcurrant")
        assert result.found is True
        assert result.hex_value == "#88455e"
        assert result.name == "redcurrant"

        result = color_mapper.get_color_name("RedCUrRant")
        assert result.found is True
        assert result.hex_value == "#88455e"

        result = color_mapper.get_color_name("DarkRed")
        assert result.found is True
        assert result.hex_value == "#8b0000"


class TestColorNameByHex:
    def test_get_color_name_by_hex(self, color_mapper):
        """Test getting color info by hex code."""
        result = color_mapper.get_color_name("#FF0000")
        assert result.found is True
        assert result.name.lower() == "red"

        result = color_mapper.get_color_name("#ff0000")
        assert result.found is True
        assert result.name.lower() == "red"

        result = color_mapper.get_color_name("FF0000")
        assert result.found is True
        assert result.name.lower() == "red"

        result = color_mapper.get_color_name("#F00")
        assert result.found is True
        assert result.name.lower() == "red"


class TestColorNameClosestMatch:
    def test_get_color_name_closest_match(self, color_mapper):
        """Test getting closest color when exact match not found."""
        result = color_mapper.get_color_name("#FE0000")
        assert result.found is True
        assert result.name.lower() == "red"

        result = color_mapper.get_color_name("Dingdong")
        assert result.found is False
        assert result.name == "dingdong"


class TestMissingMappingFile:
    def test_missing_mapping_file(self):
        """Test behavior when mapping file is missing."""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            with pytest.raises(ColorMapper.MissingMappingFile):
                ColorMapper(mapping_file="does_not_exist.json")


class TestRealMappingFile:
    def test_integration_with_real_file(self):
        """Integration test with a real temporary file."""
        test_colors = {
            "Red": "#FF0000",
            "Green": "#00FF00",
            "Blue": "#0000FF",
            "Black": "#000000",
            "White": "#FFFFFF",
            "Dark Red": "#8B0000",
        }
        test_colors.update({k.lower(): v.lower() for k, v in test_colors.items()})

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            json.dump(test_colors, temp_file)
            temp_path = temp_file.name

        try:
            with patch.object(ColorMapper, 'MAPPING_FILE', Path(temp_path)):
                ColorMapper.NAME_TO_HEX = {}
                ColorMapper.HEX_TO_NAME = {}
                real_mapper = ColorMapper()
                result = real_mapper.get_color_name("Red")
                assert result.found is True
                assert result.hex_value.lower() == "#ff0000"
        finally:
            os.unlink(temp_path)
