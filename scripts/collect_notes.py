#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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
from xhs_security import enforce_limit, ensure_private_dir, sanitize_error, sanitize_raw_data

SECRET_COOKIE_PATH = Path(__file__).resolve().parents[1] / ".secrets" / "xhs_cookie.txt"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAX_NOTES = 50
MAX_COMMENTS_PER_NOTE = 100
DEFAULT_COMMENT_LIMIT = 50
DEFAULT_CALL_TIMEOUT = 60
DEFAULT_RETRIES = 2
MAX_COMMENT_PAGES = 12


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


def call_xhs(
    tool: Path,
    namespace: str,
    method: str,
    payload: dict,
    timeout: int = DEFAULT_CALL_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> dict:
    command = [
        sys.executable,
        str(tool),
        "call",
        namespace,
        method,
        "--params-stdin",
    ]
    serialized = json.dumps(payload, ensure_ascii=False)
    last_error = "unknown error"
    for attempt in range(retries + 1):
        try:
            completed = subprocess.run(
                command,
                input=serialized,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout,
            )
            if completed.returncode == 0:
                return json.loads(completed.stdout)
            last_error = completed.stderr.strip() or completed.stdout.strip()
        except subprocess.TimeoutExpired:
            last_error = f"request timed out after {timeout} seconds"
        except json.JSONDecodeError as exc:
            last_error = f"invalid API response: {exc}"
        if attempt < retries:
            time.sleep(0.5 * (2**attempt))
    raise RuntimeError(f"{namespace}.{method} failed after {retries + 1} attempts: {sanitize_error(last_error)}")


def result_payload(response: dict):
    return unwrap_xhs_tool_response(response)


def _trim_comment_tree(comments: list[dict], limit: int) -> list[dict]:
    result = []
    remaining = limit
    for comment in comments:
        if remaining <= 0 or not isinstance(comment, dict):
            break
        item = dict(comment)
        remaining -= 1
        sub_comments = []
        for sub_comment in item.get("sub_comments") or []:
            if remaining <= 0:
                break
            if isinstance(sub_comment, dict):
                sub_comments.append(sub_comment)
                remaining -= 1
        item["sub_comments"] = sub_comments
        result.append(item)
    return result


def fetch_comments(tool: Path, url: str, cookies_str: str, limit: int = DEFAULT_COMMENT_LIMIT) -> tuple[dict, list[dict]]:
    enforce_limit("comment limit", limit, 1, MAX_COMMENTS_PER_NOTE)
    parsed = urlparse(url)
    note_id = parsed.path.rstrip("/").split("/")[-1]
    xsec_token = parse_qs(parsed.query).get("xsec_token", [""])[0]
    cursor = ""
    collected = []
    pages = []
    while len(pages) < MAX_COMMENT_PAGES and len(normalize_comments_raw({"data": {"comments": collected}}, note_url=url)) < limit:
        response = call_xhs(
            tool,
            "pc",
            "get_note_out_comment",
            {"note_id": note_id, "cursor": cursor, "xsec_token": xsec_token, "cookies_str": cookies_str},
        )
        payload = result_payload(response)
        pages.append(response)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            break
        page_comments = data.get("comments") or []
        collected.extend(item for item in page_comments if isinstance(item, dict))
        next_cursor = str(data.get("cursor") or "")
        if not page_comments or not data.get("has_more") or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    limited = _trim_comment_tree(collected, limit)
    raw = {"pages": pages, "comments": limited, "limit": limit}
    return raw, normalize_comments_raw({"comments": limited}, note_url=url)[:limit]


def fetch_note_details(
    tool: Path,
    note_refs: list[dict],
    cookies_str: str,
    source: str,
    limit: int,
    include_comments: bool = False,
    comment_limit: int = DEFAULT_COMMENT_LIMIT,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    raw_details = []
    raw_comments = []
    normalized = []
    errors = []
    for ref in note_refs[:limit]:
        note_id = ref.get("id") or ref.get("note_id")
        if not note_id:
            continue
        xsec_token = ref.get("xsec_token", "")
        xsec_source = ref.get("xsec_source") or source
        canonical_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        url = canonical_url
        params = []
        if xsec_token:
            params.append(f"xsec_token={xsec_token}")
        if xsec_source:
            params.append(f"xsec_source={xsec_source}")
        if params:
            url = f"{url}?{'&'.join(params)}"
        try:
            detail_raw = call_xhs(tool, "pc", "get_note_info", {"url": url, "cookies_str": cookies_str})
        except RuntimeError as exc:
            errors.append({"stage": "note_detail", "note_id": note_id, "error": sanitize_error(exc)})
            continue
        raw_details.append(detail_raw)
        note_details = normalize_raw(detail_raw)
        for note in note_details:
            note["url"] = canonical_url
        if include_comments:
            try:
                comment_raw, comments = fetch_comments(tool, url, cookies_str, limit=comment_limit)
                raw_comments.append({"url": url, "raw": comment_raw})
                comments_by_note_id = {}
                for comment in comments:
                    comment["note_url"] = canonical_url
                    comments_by_note_id.setdefault(comment.get("note_id", ""), []).append(comment)
                for note in note_details:
                    note_comments = comments_by_note_id.get(note.get("note_id"), comments)
                    note["comments"] = note_comments
            except RuntimeError as exc:
                errors.append({"stage": "comments", "note_id": note_id, "error": sanitize_error(exc)})
        normalized.extend(note_details)
    return raw_details, raw_comments, normalized, errors


def fetch_user_note_refs(tool: Path, user_url: str, cookies_str: str, limit: int) -> tuple[list[dict], list[dict]]:
    parsed = urlparse(user_url)
    user_id = parsed.path.rstrip("/").split("/")[-1]
    query = parse_qs(parsed.query)
    xsec_token = query.get("xsec_token", [""])[0]
    xsec_source = query.get("xsec_source", ["pc_search"])[0]
    cursor = ""
    pages = []
    refs = []
    while len(refs) < limit:
        response = call_xhs(
            tool,
            "pc",
            "get_user_note_info",
            {
                "user_id": user_id,
                "cursor": cursor,
                "xsec_token": xsec_token,
                "xsec_source": xsec_source,
                "cookies_str": cookies_str,
            },
        )
        pages.append(response)
        payload = result_payload(response)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            break
        page_refs = data.get("notes") or []
        refs.extend(item for item in page_refs if isinstance(item, dict))
        next_cursor = str(data.get("cursor") or "")
        if not page_refs or not data.get("has_more") or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return pages, refs[:limit]


def validate_cookie(tool: Path, cookies_str: str) -> tuple[bool, str]:
    try:
        response = call_xhs(tool, "pc", "get_user_self_info2", {"cookies_str": cookies_str}, retries=0)
    except RuntimeError as exc:
        return False, sanitize_error(exc)
    result = response.get("result") if isinstance(response, dict) else None
    if isinstance(result, (list, tuple)) and len(result) >= 2:
        return bool(result[0]), str(result[1])
    return False, "Unexpected auth-check response."


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect authorized XHS note data through xhs-apis and build first-pass outputs.")
    parser.add_argument("--mode", choices=["note", "keyword", "user"], required=True)
    parser.add_argument("--url", help="Note URL for mode=note or user profile URL for mode=user.")
    parser.add_argument("--query", help="Keyword for mode=keyword.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum keyword notes to collect.")
    parser.add_argument("--xhs-apis-skill", help="Path to an installed xhs-apis skill.")
    parser.add_argument("--include-comments", action="store_true", help="Also collect and flatten note comments.")
    parser.add_argument("--comment-limit", type=int, default=DEFAULT_COMMENT_LIMIT, help="Maximum normalized comments per note (1-100).")
    parser.add_argument("--run-id", default="", help="Stable run id for output tracking. Defaults to YYYYMMDD_HHMMSS.")
    parser.add_argument("--out-dir", default="", help="Output directory. Defaults to <skill-dir>/runs/<run-id>. Supports {run_id}.")
    args = parser.parse_args()

    cookies_str = load_cookie()
    if not cookies_str:
        raise ValueError("XHS auth is required. Run scripts/xhs_auth.py login or set XHS_COOKIE.")
    enforce_limit("limit", args.limit, 1, MAX_NOTES)
    enforce_limit("comment limit", args.comment_limit, 1, MAX_COMMENTS_PER_NOTE)

    tool = resolve_tool(args.xhs_apis_skill)
    auth_valid, auth_message = validate_cookie(tool, cookies_str)
    if not auth_valid:
        raise ValueError(f"XHS auth check failed: {auth_message}. Run scripts/xhs_auth.py login --wait-auto.")
    run_id = args.run_id or default_run_id()
    out_dir = resolve_out_dir(args.out_dir, run_id)
    ensure_private_dir(out_dir)
    errors = []

    if args.mode == "note":
        if not args.url:
            raise ValueError("--url is required for mode=note.")
        raw = call_xhs(tool, "pc", "get_note_info", {"url": args.url, "cookies_str": cookies_str})
        notes = normalize_raw(raw)
        canonical_url = args.url.split("?", 1)[0].split("#", 1)[0]
        for note in notes:
            note["url"] = canonical_url
        if args.include_comments:
            comment_raw, comments = fetch_comments(tool, args.url, cookies_str, limit=args.comment_limit)
            raw = {"mode": "note", "note_raw": raw, "comment_raw": comment_raw}
            for comment in comments:
                comment["note_url"] = canonical_url
            for note in notes:
                note["comments"] = comments
        source = canonical_url
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
        detail_raw, comment_raw, notes, errors = fetch_note_details(
            tool, search_items, cookies_str, "pc_search", args.limit, args.include_comments, args.comment_limit
        )
        raw = {"mode": "keyword", "query": args.query, "search_raw": search_raw, "detail_raw": detail_raw, "comment_raw": comment_raw}
        if not notes:
            notes = normalize_raw(search_raw)
        source = args.query
    else:
        if not args.url:
            raise ValueError("--url is required for mode=user.")
        user_raw, user_items = fetch_user_note_refs(tool, args.url, cookies_str, args.limit)
        detail_raw, comment_raw, notes, errors = fetch_note_details(
            tool, user_items, cookies_str, "pc_user", args.limit, args.include_comments, args.comment_limit
        )
        raw = {"mode": "user", "user_url": args.url, "user_raw": user_raw, "detail_raw": detail_raw, "comment_raw": comment_raw}
        if not notes:
            notes = normalize_raw({"notes": user_items})
        source = args.url.split("?", 1)[0].split("#", 1)[0]

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
        "comment_limit": args.comment_limit,
        "notes_count": len(notes),
        "comments_count": len(comments),
        "errors": errors,
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
    write_json(raw_path, sanitize_raw_data(raw))
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
