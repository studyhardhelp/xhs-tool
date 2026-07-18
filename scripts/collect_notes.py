#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from xhs_report_lib import (
    flatten_note_comments,
    normalize_comments_raw,
    normalize_raw,
    unwrap_xhs_tool_response,
    write_comments_table,
    write_json,
    write_markdown_report,
    write_table,
)

SECRET_COOKIE_PATH = Path(__file__).resolve().parents[1] / ".secrets" / "xhs_cookie.txt"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_cookie(cli_cookie: str = "") -> str:
    if cli_cookie:
        return cli_cookie.strip()
    env_cookie = os.environ.get("XHS_COOKIE", "").strip()
    if env_cookie:
        return env_cookie
    if SECRET_COOKIE_PATH.exists():
        return SECRET_COOKIE_PATH.read_text(encoding="utf-8").strip()
    return ""


def resolve_tool(skill_path: str | None) -> Path:
    candidates = []
    candidates.append(Path(__file__).resolve().parent / "xhs_api_tool.py")
    if skill_path:
        candidates.append(Path(skill_path) / "scripts" / "xhs_api_tool.py")
    env_path = os.environ.get("XHS_APIS_SKILL_PATH")
    if env_path:
        candidates.append(Path(env_path) / "scripts" / "xhs_api_tool.py")
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        "xhs_api_tool.py not found. Use the vendored scripts/xhs_api_tool.py, "
        "pass --xhs-apis-skill /path/to/xhs-apis, or set XHS_APIS_SKILL_PATH."
    )


def default_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def resolve_out_dir(out_dir: str, run_id: str) -> Path:
    if out_dir:
        return Path(out_dir.replace("{run_id}", run_id))
    return PROJECT_ROOT / "runs" / run_id


def call_xhs(tool: Path, namespace: str, method: str, payload: dict) -> dict:
    command = [
        sys.executable,
        str(tool),
        "call",
        namespace,
        method,
        "--params",
        json.dumps(payload, ensure_ascii=False),
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return json.loads(completed.stdout)


def result_payload(response: dict):
    return unwrap_xhs_tool_response(response)


def fetch_comments(tool: Path, url: str, cookies_str: str) -> tuple[dict, list[dict]]:
    raw = call_xhs(tool, "pc", "get_note_all_comment", {"url": url, "cookies_str": cookies_str})
    return raw, normalize_comments_raw(raw, note_url=url)


def fetch_note_details(
    tool: Path,
    note_refs: list[dict],
    cookies_str: str,
    source: str,
    limit: int,
    include_comments: bool = False,
) -> tuple[list[dict], list[dict], list[dict]]:
    raw_details = []
    raw_comments = []
    normalized = []
    for ref in note_refs[:limit]:
        note_id = ref.get("id") or ref.get("note_id")
        if not note_id:
            continue
        xsec_token = ref.get("xsec_token", "")
        xsec_source = ref.get("xsec_source") or source
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        params = []
        if xsec_token:
            params.append(f"xsec_token={xsec_token}")
        if xsec_source:
            params.append(f"xsec_source={xsec_source}")
        if params:
            url = f"{url}?{'&'.join(params)}"
        detail_raw = call_xhs(tool, "pc", "get_note_info", {"url": url, "cookies_str": cookies_str})
        raw_details.append(detail_raw)
        note_details = normalize_raw(detail_raw)
        for note in note_details:
            if note.get("url") and "xsec_token=" not in note["url"]:
                note["url"] = url
        if include_comments:
            comment_raw, comments = fetch_comments(tool, url, cookies_str)
            raw_comments.append({"url": url, "raw": comment_raw})
            comments_by_note_id = {}
            for comment in comments:
                comments_by_note_id.setdefault(comment.get("note_id", ""), []).append(comment)
            for note in note_details:
                note_comments = comments_by_note_id.get(note.get("note_id"), comments)
                note["comments"] = note_comments
        normalized.extend(note_details)
    return raw_details, raw_comments, normalized


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect authorized XHS note data through xhs-apis and build first-pass outputs.")
    parser.add_argument("--mode", choices=["note", "keyword", "user"], required=True)
    parser.add_argument("--url", help="Note URL for mode=note or user profile URL for mode=user.")
    parser.add_argument("--query", help="Keyword for mode=keyword.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum keyword notes to collect.")
    parser.add_argument("--cookies-str", default="", help="XHS cookie string. Defaults to XHS_COOKIE or <skill-dir>/.secrets/xhs_cookie.txt.")
    parser.add_argument("--xhs-apis-skill", help="Path to an installed xhs-apis skill.")
    parser.add_argument("--include-comments", action="store_true", help="Also collect and flatten note comments.")
    parser.add_argument("--run-id", default="", help="Stable run id for output tracking. Defaults to YYYYMMDD_HHMMSS.")
    parser.add_argument("--out-dir", default="", help="Output directory. Defaults to <skill-dir>/runs/<run-id>. Supports {run_id}.")
    args = parser.parse_args()

    cookies_str = load_cookie(args.cookies_str)
    if not cookies_str:
        raise ValueError("cookies_str is required. Run scripts/xhs_auth.py login, pass --cookies-str, or set XHS_COOKIE.")
    if args.limit > 50:
        raise ValueError("limit must be <= 50 for the first version.")

    tool = resolve_tool(args.xhs_apis_skill)
    run_id = args.run_id or default_run_id()
    out_dir = resolve_out_dir(args.out_dir, run_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "note":
        if not args.url:
            raise ValueError("--url is required for mode=note.")
        raw = call_xhs(tool, "pc", "get_note_info", {"url": args.url, "cookies_str": cookies_str})
        notes = normalize_raw(raw)
        if args.include_comments:
            comment_raw, comments = fetch_comments(tool, args.url, cookies_str)
            raw = {"mode": "note", "note_raw": raw, "comment_raw": comment_raw}
            for note in notes:
                note["comments"] = comments
        source = args.url
    elif args.mode == "keyword":
        if not args.query:
            raise ValueError("--query is required for mode=keyword.")
        search_raw = call_xhs(
            tool,
            "pc",
            "search_some_note",
            {"query": args.query, "require_num": args.limit, "cookies_str": cookies_str},
        )
        search_items = result_payload(search_raw)
        if not isinstance(search_items, list):
            search_items = []
        detail_raw, comment_raw, notes = fetch_note_details(tool, search_items, cookies_str, "pc_search", args.limit, args.include_comments)
        raw = {"mode": "keyword", "query": args.query, "search_raw": search_raw, "detail_raw": detail_raw, "comment_raw": comment_raw}
        if not notes:
            notes = normalize_raw(search_raw)
        source = args.query
    else:
        if not args.url:
            raise ValueError("--url is required for mode=user.")
        user_raw = call_xhs(tool, "pc", "get_user_all_notes", {"user_url": args.url, "cookies_str": cookies_str})
        user_items = result_payload(user_raw)
        if not isinstance(user_items, list):
            user_items = []
        detail_raw, comment_raw, notes = fetch_note_details(tool, user_items, cookies_str, "pc_user", args.limit, args.include_comments)
        raw = {"mode": "user", "user_url": args.url, "user_raw": user_raw, "detail_raw": detail_raw, "comment_raw": comment_raw}
        if not notes:
            notes = normalize_raw(user_raw)
        source = args.url

    raw_path = out_dir / "raw.json"
    normalized_path = out_dir / "notes.normalized.json"
    report_path = out_dir / "report.md"
    table_path = write_table(out_dir / "notes", notes)
    comments = flatten_note_comments(notes)
    comments_path = out_dir / "comments.normalized.json"
    comments_table_path = write_comments_table(out_dir / "comments", comments)
    summary_path = out_dir / "summary.json"
    summary = {
        "run_id": run_id,
        "mode": args.mode,
        "source": source,
        "limit": args.limit,
        "include_comments": args.include_comments,
        "notes_count": len(notes),
        "comments_count": len(comments),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "outputs": {
            "raw": str(raw_path.resolve()),
            "normalized": str(normalized_path.resolve()),
            "report": str(report_path.resolve()),
            "table": str(table_path.resolve()),
            "comments": str(comments_path.resolve()),
            "comments_table": str(comments_table_path.resolve()),
        },
    }
    write_json(raw_path, raw)
    write_json(normalized_path, notes)
    write_json(comments_path, comments)
    write_json(summary_path, summary)
    write_markdown_report(report_path, notes, source)

    print(f"run_id: {run_id}")
    print(f"out_dir: {out_dir.resolve()}")
    print(f"raw: {raw_path.resolve()}")
    print(f"normalized: {normalized_path.resolve()}")
    print(f"summary: {summary_path.resolve()}")
    print(f"report: {report_path.resolve()}")
    print(f"table: {table_path.resolve()}")
    print(f"comments: {comments_path.resolve()}")
    print(f"comments_table: {comments_table_path.resolve()}")


if __name__ == "__main__":
    main()
