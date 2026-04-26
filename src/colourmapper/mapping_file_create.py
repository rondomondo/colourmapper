#!/usr/bin/env python3

import argparse
import asyncio
import csv
import itertools
import json
import os
import re
import sys
import traceback
from pathlib import Path

import matplotlib.colors as mcolors

PROGRAM_NAME = os.path.basename(re.sub(r"\.py$", "", sys.argv[0]))
NAMED_COLOURS_MAP_FILENAME = "named_colours_map.json"


def emit(data: object) -> None:
    print(json.dumps(data, indent=2))


def emit_error(message: str, detail: str | None = None) -> None:
    payload: dict = {"error": message}
    if detail:
        payload["detail"] = detail
    emit(payload)


def setup_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description=(
            "Generate a named-colour map from multiple sources and write it to a file.\n\n"
            "Combines xkcd, Crayola, and CSS colour-name CSVs with matplotlib's full\n"
            "colour map, then serialises the merged result in the requested format.\n\n"
            "A named-colour map is a flat JSON object mapping human-readable colour names\n"
            "to their hex codes, for example:\n\n"
            '  {\n'
            '    "acid green":   "#8ffe09",\n'
            '    "adobe":        "#bd6c48",\n'
            '    "algae":        "#54ac68",\n'
            '    "almond":       "#efdecd",\n'
            '    "almost black": "#070d0d"\n'
            '  }\n\n'
            "Each CSV source has exactly three comma-separated fields per row:\n"
            "  display name, hex value, normalised name\n\n"
            "Example rows from the bundled CSV files:\n"
            '  xkcd:    "acid green","#8ffe09","acid green"\n'
            '  Crayola: "Absolute Zero","#0048ba","absolute zero"\n'
            '  CSS:     "Abbey","4c4f56","abbey"\n'
            '  Custom:  "1989 Miami Hotline","#dd3366","1989 miami hotline"\n\n'
            "After merging the CSVs, matplotlib's full colour set is added, giving\n"
            "a final map of 3 000+ entries.\n\n"
            "All output is valid JSON and can be piped to jq."
        ),
        epilog=(
            "Examples:\n"
            f"  {PROGRAM_NAME}\n"
            f"  {PROGRAM_NAME} --format json --file my_colours\n"
            f"  {PROGRAM_NAME} --print\n"
            f"  {PROGRAM_NAME} --dry-run\n"
            f"  {PROGRAM_NAME} --dry-run | jq '.map | to_entries | .[0:5]'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    options = parser.add_argument_group("Options")
    options.add_argument(
        "-d",
        "--delimiter",
        default=",",
        help="Delimiter for list/csv output formats. Defaults to comma.",
    )
    options.add_argument(
        "-f",
        "--file",
        default=NAMED_COLOURS_MAP_FILENAME,
        help=f"Output filename stem. Defaults to {NAMED_COLOURS_MAP_FILENAME}.",
    )
    options.add_argument(
        "--format",
        choices=["dict", "list", "json", "csv"],
        default="json",
        help="Output format: dict, list, json, or csv. Defaults to json.",
    )
    options.add_argument(
        "--print",
        action="store_true",
        help="Emit the colour map to stdout as JSON.",
    )
    options.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the map but do not write any file. Implies --print.",
    )
    options.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug logging.",
    )

    return parser


def merge_dicts(dict_list: list[dict]) -> dict:
    kviter = itertools.chain.from_iterable(d.items() for d in dict_list)
    return dict(kviter)


async def read_csv_file(path: Path) -> list[list[str]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _read_csv_sync, path)


def _read_csv_sync(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    with path.open(newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for row in reader:
            rows.append(row)
    return rows


async def create_dicts_from_csv(filename: str) -> tuple[dict[str, str], dict[str, str]]:
    path = Path(filename)
    rows = await read_csv_file(path)
    dict1: dict[str, str] = {}
    dict2: dict[str, str] = {}
    for row in rows:
        if len(row) != 3:
            raise ValueError(f"Invalid CSV format {filename}: row {row} must have exactly 3 fields.")
        field1, field2, field3 = row
        dict1[field1] = field2
        dict2[field3] = field2
    return dict1, dict2


def get_named_colours_css4() -> list[tuple[str, str]]:
    colors = mcolors.CSS4_COLORS
    return [(name, mcolors.to_hex(color)) for name, color in colors.items()]


def get_named_colours_all() -> dict[str, str]:
    colors = mcolors._colors_full_map
    for k in mcolors.BASE_COLORS:
        colors.pop(k, None)
    return dict((name.replace("xkcd:", ""), mcolors.to_hex(color)) for name, color in colors.items())


def get_bare_name_hex_pairs(data: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in sorted(data.keys()):
        hexval = data[name]
        bare = name.split(":")[-1].replace("'", "")
        result[bare] = hexval
    return result


def format_results(bare_results: dict[str, str], output_format: str, delimiter: str) -> str:
    if output_format == "dict":
        return str(bare_results)
    if output_format == "list":
        items = [f'"{k}{delimiter}{v}"' for k, v in bare_results.items()]
        return str(items).replace("'", "")
    if output_format == "json":
        return json.dumps(bare_results, indent=4)
    rows = [f"{k}{delimiter}{v}" for k, v in bare_results.items()]
    return "\n".join(rows).replace("'", "")


async def write_file(path: Path, content: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, path.write_text, content, "utf-8")


async def build_colour_map(flags: argparse.Namespace) -> object:
    delimiter: str = flags.delimiter
    output_format: str = flags.format
    file_arg = Path(flags.file)
    output_path = (file_arg.parent /
                   f"{file_arg.stem}.{output_format}") if file_arg.parent != Path(".") else (Path(__file__).parent /
                                                                                             f"{file_arg.stem}.{output_format}")

    csv_files = [
        Path(__file__).parent / "xkcd.rgb.mapping.csv",
        Path(__file__).parent / "crayola2.mapping.csv",
        Path(__file__).parent / "colorNames.mapping.csv",
        Path(__file__).parent / "ColourMapperValues.csv",
    ]

    combined: dict[str, str] = {}
    for filename in csv_files:
        d1, d2 = await create_dicts_from_csv(filename)
        combined.update(d1)
        combined.update(d2)

    combined.update(get_named_colours_all())
    bare_results = get_bare_name_hex_pairs(combined)
    formatted = format_results(bare_results, output_format, delimiter)

    result: dict = {"count": len(bare_results), "format": output_format}

    if flags.dry_run:
        result["dry_run"] = True
        result["map"] = bare_results
        return result

    await write_file(output_path, formatted)
    result["path"] = str(output_path)

    if flags.print:
        result["map"] = bare_results

    return result


async def main() -> None:
    flags = None
    try:
        parser = setup_argument_parser()
        flags = parser.parse_args()

        result = await build_colour_map(flags)
        emit(result)

    except Exception as ex:
        detail = traceback.format_exc() if flags and flags.debug else None
        emit_error(str(ex), detail)
        sys.exit(1)


def _entry() -> None:
    """Sync entry point for the mapping-file-create console script (pip install)."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        emit_error("interrupted")
        sys.exit(0)
    except Exception as ex:
        emit_error(f"Unexpected error: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        emit_error("interrupted")
        sys.exit(0)
    except Exception as ex:
        emit_error(f"Unexpected error: {ex}")
        sys.exit(1)


