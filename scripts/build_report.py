#!/usr/bin/env python3
import argparse
from pathlib import Path

from xhs_report_lib import flatten_note_comments, load_normalized, write_comments_table, write_json, write_markdown_report, write_table, summarize_notes
from xhs_security import ensure_private_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Markdown and spreadsheet reports from normalized XHS notes.")
    parser.add_argument("--input", required=True, help="Normalized notes JSON file.")
    parser.add_argument("--out-dir", required=True, help="Directory for report outputs.")
    parser.add_argument("--source", default="", help="Optional source label for the report.")
    args = parser.parse_args()

    notes = load_normalized(args.input)
    out_dir = Path(args.out_dir)
    ensure_private_dir(out_dir)

    normalized_path = out_dir / "notes.normalized.json"
    summary_path = out_dir / "summary.json"
    markdown_path = out_dir / "report.md"
    table_path = write_table(out_dir / "notes", notes)
    comments = flatten_note_comments(notes)
    comments_path = out_dir / "comments.normalized.json"
    comments_table_path = write_comments_table(out_dir / "comments", comments)

    write_json(normalized_path, notes)
    write_json(comments_path, comments)
    write_json(summary_path, summarize_notes(notes))
    write_markdown_report(markdown_path, notes, args.source)

    print(f"notes: {len(notes)}")
    print(f"normalized: {normalized_path.resolve()}")
    print(f"summary: {summary_path.resolve()}")
    print(f"report: {markdown_path.resolve()}")
    print(f"table: {table_path.resolve()}")
    print(f"comments: {comments_path.resolve()}")
    print(f"comments_table: {comments_table_path.resolve()}")


if __name__ == "__main__":
    main()
