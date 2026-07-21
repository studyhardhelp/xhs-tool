#!/usr/bin/env python3
import argparse
from pathlib import Path

from xhs_report_lib import normalize_raw, read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize raw XHS/Spider_XHS JSON into stable note fields.")
    parser.add_argument("--input", required=True, help="Raw JSON file from Spider_XHS, XhsSkills, or collect_notes.py.")
    parser.add_argument("--out", required=True, help="Output normalized JSON file.")
    args = parser.parse_args()

    notes = normalize_raw(read_json(args.input))
    write_json(args.out, notes)
    print(f"normalized {len(notes)} notes -> {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
