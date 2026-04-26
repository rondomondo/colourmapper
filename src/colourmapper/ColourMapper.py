#!/usr/bin/env python

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ColourResult:
    """Represents the result of a colour mapping operation."""
    found: bool
    hex_value: str
    name: str


class ColourMapper:
    """Maps between colour names and hex values, with support for finding nearest colours."""

    HEX_COLOUR_RE = re.compile(r'^#?([a-fA-F0-9]{3}|[a-fA-F0-9]{6})$', re.IGNORECASE)

    MAPPING_FILE = Path(__file__).parent / "named_colours_map.json"

    NAME_TO_HEX: dict[str, str] = {}
    HEX_TO_NAME: dict[str, str] = {}

    class MissingMappingFile(IOError):
        """Exception raised when the colour mapping file cannot be found."""

        def __init__(self, mapping_file: Path | None = None) -> None:
            path = mapping_file or ColourMapper.MAPPING_FILE
            message = (
                f"Unable to find the mapping file: {path}\n"
                "Expected format: JSON array of objects with 'name' and 'hex' keys."
            )
            super().__init__(message)

    def __init__(self, mapping_file: str | Path | None = None) -> None:
        """Initialize the ColourMapper with colour mappings.

        Args:
            mapping_file: optional path to a custom colour mapping JSON file.
                          Defaults to the bundled named_colours_map.json.
        """
        resolved = Path(mapping_file) if mapping_file is not None else None
        ColourMapper._ensure_loaded(resolved)
        self.name_to_hex = ColourMapper.NAME_TO_HEX
        self.hex_to_name = ColourMapper.HEX_TO_NAME

    @classmethod
    def _ensure_loaded(cls, mapping_file: Path | None = None) -> None:
        """Lazy-load colour mappings from JSON on first access."""
        resolved = mapping_file or cls.MAPPING_FILE
        if cls.NAME_TO_HEX and mapping_file is None:
            return
        try:
            with open(resolved, encoding="utf-8") as infile:
                data = json.load(infile)
                data_no_spaces = {k.replace(" ", ""): v for k, v in data.items()}
                cls.NAME_TO_HEX.update(dict(data, **data_no_spaces))
                cls.HEX_TO_NAME.update({v.lower(): k for k, v in data.items()})
        except OSError as e:
            raise cls.MissingMappingFile(resolved) from e

    @staticmethod
    def hexify(value: str) -> str | None:
        """Convert a colour value to standardised hexadecimal form.

        Args:
            value: colour value to convert.

        Returns:
            Standardised hex colour code, or None if invalid.
        """
        match = ColourMapper.HEX_COLOUR_RE.match(value)
        if not match:
            return None

        hex_value = match.group(1)
        if len(hex_value) == 3:
            hex_value = ''.join(c * 2 for c in hex_value)
        return f"#{hex_value.lower()}"

    @staticmethod
    def _calculate_colour_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
        """Calculate the Euclidean distance between two RGB colours.

        Args:
            c1: first RGB colour tuple.
            c2: second RGB colour tuple.

        Returns:
            Euclidean distance between the colours.
        """
        return sum((x - y) ** 2 for x, y in zip(c1, c2, strict=True)) ** 0.5

    @staticmethod
    def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
        """Convert a hex colour string to RGB values.

        Args:
            hex_str: hex colour string (with or without leading #).

        Returns:
            RGB colour values as a three-tuple.
        """
        hex_str = hex_str.lstrip('#')
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (r, g, b)

    @classmethod
    def get_closest_colour(cls, hex_colour: str) -> tuple[str, str]:
        """Find the closest named colour to a given hex colour.

        Args:
            hex_colour: hex colour code to match.

        Returns:
            Closest matching hex code and colour name.
        """
        cls._ensure_loaded()
        hex_colour = hex_colour.lstrip('#').lower()
        target_rgb = cls._hex_to_rgb(hex_colour)

        min_distance = float('inf')
        closest_hex = None
        closest_name = None

        for hex_code, name in cls.HEX_TO_NAME.items():
            compare_hex = hex_code.lstrip('#').lower()
            compare_rgb = cls._hex_to_rgb(compare_hex)
            distance = cls._calculate_colour_distance(target_rgb, compare_rgb)

            if distance < min_distance:
                min_distance = distance
                closest_hex = compare_hex
                closest_name = name

        return f"#{closest_hex}", closest_name

    # American-spelling aliases for backward compatibility
    _calculate_color_distance = _calculate_colour_distance
    get_closest_color = get_closest_colour

    @classmethod
    def get_color_name(cls, value: str) -> ColourResult:
        """Alias for get_colour_name for American-spelling compatibility.

        Args:
            value: colour name or hex value.

        Returns:
            ColourResult with found status, hex value, and colour name.
        """
        return cls.get_colour_name(value)

    @classmethod
    def get_colour_name(cls, value: str) -> ColourResult:
        """Get the standardised colour name and hex value for a given input.

        Args:
            value: colour name or hex value.

        Returns:
            ColourResult with found status, hex value, and colour name.
        """
        cls._ensure_loaded()
        value = value.lower()

        if value in cls.NAME_TO_HEX:
            return ColourResult(
                found=True,
                hex_value=cls.NAME_TO_HEX[value],
                name=value
            )

        hex_value = cls.hexify(value)
        if not hex_value:
            return ColourResult(found=False, hex_value=value, name=value)

        if hex_value.lower() in cls.HEX_TO_NAME:
            return ColourResult(
                found=True,
                hex_value=hex_value,
                name=cls.HEX_TO_NAME[hex_value.lower()]
            )

        nearest_hex, nearest_name = cls.get_closest_colour(hex_value)
        if nearest_name:
            return ColourResult(
                found=True,
                hex_value=nearest_hex,
                name=nearest_name
            )

        return ColourResult(
            found=True,
            hex_value=hex_value,
            name=hex_value
        )


def main() -> None:
    """Command-line interface for colour mapping."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <colour>\n\nwhere colour can be a name or hex value")
        sys.exit(1)

    mapper = ColourMapper()
    result = mapper.get_colour_name(sys.argv[1])
    print(f"{result.hex_value},{result.found},{result.name}")


if __name__ == "__main__":
    main()
