#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from collect_notes import resolve_tool, validate_cookie


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COOKIE_PATH = PROJECT_ROOT / ".secrets" / "xhs_cookie.txt"
STATE_PATH = PROJECT_ROOT / ".secrets" / "xhs_auth_state.json"
AUTH_META_PATH = PROJECT_ROOT / ".secrets" / "xhs_auth_meta.json"
REQUIRED_COOKIE_NAMES = ["a1", "web_session", "webId", "websectiga", "gid"]
COMMON_CHROME_EXECUTABLES = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ],
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Google\Chrome for Testing\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome for Testing\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ],
    "Linux": [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/microsoft-edge",
    ],
}
PATH_BROWSER_NAMES = [
    "google-chrome",
    "google-chrome-stable",
    "chrome",
    "chromium",
    "chromium-browser",
    "msedge",
    "microsoft-edge",
]


def skill_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def ensure_secret_dir() -> None:
    COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        COOKIE_PATH.parent.chmod(0o700)
    except OSError:
        pass


def cookie_header_from_browser_cookies(cookies: list[dict]) -> str:
    by_name = {}
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        domain = cookie.get("domain", "")
        if not name or value is None:
            continue
        if "xiaohongshu.com" not in domain:
            continue
        by_name[name] = value

    selected = []
    for name in REQUIRED_COOKIE_NAMES:
        value = by_name.get(name)
        if value:
            selected.append(f"{name}={value}")

    for name, value in sorted(by_name.items()):
        if name not in REQUIRED_COOKIE_NAMES and name.startswith(("web", "xsec", "ab", "sec")):
            selected.append(f"{name}={value}")
    return "; ".join(selected)


def save_cookie(cookie_header: str) -> None:
    ensure_secret_dir()
    COOKIE_PATH.write_text(cookie_header.strip() + "\n", encoding="utf-8")
    try:
        COOKIE_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_cookie() -> str:
    if COOKIE_PATH.exists():
        return COOKIE_PATH.read_text(encoding="utf-8").strip()
    return os.environ.get("XHS_COOKIE", "").strip()


def cookie_names_from_header(cookie_header: str) -> list[str]:
    names = []
    for item in cookie_header.split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        name, _ = item.split("=", 1)
        if name:
            names.append(name)
    return names


def auth_status_from_cookie(cookie_header: str, source: str = "") -> dict:
    names = cookie_names_from_header(cookie_header)
    found = [name for name in REQUIRED_COOKIE_NAMES if name in names]
    missing = [name for name in REQUIRED_COOKIE_NAMES if name not in names]
    has_session = "web_session" in names
    has_identity = "a1" in names and ("webId" in names or "gid" in names)
    usable = has_session and has_identity
    if usable:
        status = "present"
        message = "Local XHS auth has the required cookie names and needs a live API check."
    elif names:
        status = "partial"
        message = "Local XHS auth exists but may need refresh."
    else:
        status = "missing"
        message = "No local XHS auth found."
    return {
        "status": status,
        "usable": False,
        "structural_usable": usable,
        "verified": False,
        "message": message,
        "source": source,
        "found": found,
        "missing": missing,
        "cookie_count": len(names),
    }


def save_auth_meta(status: dict, extra: dict | None = None) -> None:
    ensure_secret_dir()
    payload = {
        "version": "1.0",
        "saved_at": now_iso(),
        "cookie_file": skill_relative(COOKIE_PATH),
        "auth": status,
    }
    if extra:
        payload.update(extra)
    AUTH_META_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        AUTH_META_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def load_auth_meta() -> dict:
    if not AUTH_META_PATH.exists():
        return {}
    try:
        return json.loads(AUTH_META_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def redacted_cookie(cookie_header: str) -> str:
    parts = []
    for item in cookie_header.split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        name, value = item.split("=", 1)
        visible = value[:4] + "..." + value[-4:] if len(value) > 10 else "***"
        parts.append(f"{name}={visible}")
    return "; ".join(parts)


def common_browser_paths() -> list[str]:
    paths = list(COMMON_CHROME_EXECUTABLES.get(platform.system(), []))
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            paths.extend(
                [
                    str(Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe"),
                    str(Path(local_app_data) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
                ]
            )
    for name in PATH_BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            paths.append(found)
    deduped = []
    seen = set()
    for path in paths:
        if path not in seen and Path(path).exists():
            deduped.append(path)
            seen.add(path)
    return deduped


def build_launch_candidates(args: argparse.Namespace) -> list[dict]:
    base = {
        "headless": False,
        "slow_mo": args.slow_mo,
    }
    candidates = []
    if args.executable_path:
        candidates.append((f"executable: {args.executable_path}", {**base, "executable_path": args.executable_path}))
    if args.channel:
        candidates.append((f"channel: {args.channel}", {**base, "channel": args.channel}))
        return candidates
    for channel in ["chrome", "msedge", "chrome-beta", "chrome-dev", "chrome-canary"]:
        candidates.append((f"channel: {channel}", {**base, "channel": channel}))
    for path in common_browser_paths():
        candidates.append((f"executable: {path}", {**base, "executable_path": path}))
    candidates.append(("Playwright bundled chromium", dict(base)))
    return candidates


def install_playwright_chromium() -> tuple[bool, str]:
    command = [sys.executable, "-m", "playwright", "install", "chromium"]
    completed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=600)
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return completed.returncode == 0, output


def try_launch_chromium(playwright, args: argparse.Namespace):
    errors = []
    for label, launch_kwargs in build_launch_candidates(args):
        try:
            if args.verbose:
                print(f"Trying browser launch via {label}...")
            browser = playwright.chromium.launch(**launch_kwargs)
            print(f"Browser launched via {label}.")
            return browser, errors
        except Exception as exc:
            errors.append(f"- {label}: {exc}")
            if args.verbose:
                print(f"Launch failed via {label}: {exc}", file=sys.stderr)
    return None, errors


def launch_chromium(playwright, args: argparse.Namespace):
    browser, errors = try_launch_chromium(playwright, args)
    if browser:
        return browser
    if args.auto_install_browser and not args.channel and not args.executable_path:
        print("No controllable Chrome/Edge browser found. Installing Playwright Chromium...")
        success, output = install_playwright_chromium()
        if success:
            browser, retry_errors = try_launch_chromium(playwright, args)
            if browser:
                return browser
            errors.extend(retry_errors)
        else:
            errors.append("- Playwright chromium install: " + (output or "install command failed"))
    raise SystemExit(
        "Could not open a visible browser for Xiaohongshu login.\n"
        "Tried:\n"
        + "\n".join(errors)
        + "\n\nIf Chrome is installed, try:\n"
        "  .venv/bin/python scripts/xhs_auth.py login --channel chrome --verbose\n"
        "If Chrome is not installed, retry with automatic Playwright Chromium install:\n"
        "  .venv/bin/python scripts/xhs_auth.py login --verbose --wait-auto\n"
        "If you only want to open the system default browser, use it for manual login/cookie copy; automatic cookie export requires a Playwright-controlled Chromium browser."
    )


def wait_for_login_completion(page, context, timeout_seconds: int, poll_seconds: int = 3) -> str:
    deadline = time.time() + timeout_seconds
    last_url = ""
    while time.time() < deadline:
        current_url = page.url
        if current_url != last_url:
            print(f"Waiting for login. Current page: {current_url}")
            last_url = current_url
        cookie_header = cookie_header_from_browser_cookies(context.cookies())
        status = auth_status_from_cookie(cookie_header, "browser")
        if status["structural_usable"]:
            return cookie_header
        time.sleep(poll_seconds)
    raise SystemExit(f"Login wait timed out after {timeout_seconds} seconds. Please retry login.")


def login(args: argparse.Namespace) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required for browser login. Install it with:\n"
            "  .venv/bin/pip install playwright\n"
            "  .venv/bin/python -m playwright install chromium\n"
            "Or use an installed Chrome channel with --channel chrome."
        ) from exc

    ensure_secret_dir()
    with sync_playwright() as p:
        browser = launch_chromium(p, args)
        context = browser.new_context(storage_state=str(STATE_PATH) if STATE_PATH.exists() else None)
        page = context.new_page()
        page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
        print("Browser opened. Log in to Xiaohongshu in the browser window.")
        if args.wait_auto:
            print(f"Waiting up to {args.timeout} seconds for login to complete.")
            cookie_header = wait_for_login_completion(page, context, args.timeout)
        else:
            print("After the home page shows your logged-in account, return here and press Enter.")
            input()
            cookie_header = cookie_header_from_browser_cookies(context.cookies())
        context.storage_state(path=str(STATE_PATH))
        try:
            STATE_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        browser.close()

    status_payload = auth_status_from_cookie(cookie_header, f"<skill-dir>/{skill_relative(COOKIE_PATH)}")
    if not status_payload["structural_usable"]:
        raise SystemExit("No usable Xiaohongshu cookies found. Make sure login completed in the opened browser.")
    save_cookie(cookie_header)
    save_auth_meta(status_payload, {"last_login_at": now_iso(), "browser_storage_state": skill_relative(STATE_PATH)})
    print(f"Saved local XHS auth to <skill-dir>/{skill_relative(COOKIE_PATH)}")
    if args.show_redacted:
        print(redacted_cookie(cookie_header))


def status(args: argparse.Namespace) -> None:
    cookie = load_cookie()
    if not cookie:
        payload = auth_status_from_cookie("", "")
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(payload["message"])
        return
    source = f"<skill-dir>/{skill_relative(COOKIE_PATH)}" if COOKIE_PATH.exists() else "XHS_COOKIE"
    payload = auth_status_from_cookie(cookie, source)
    if payload["structural_usable"] and not args.offline:
        valid, message = validate_cookie(resolve_tool(None), cookie)
        payload["usable"] = valid
        technical_failure = any(marker in message.lower() for marker in ("timed out", "runtime", "dependency", "not found"))
        payload["verified"] = not technical_failure
        payload["status"] = "valid" if valid else "unverified" if technical_failure else "invalid"
        if valid:
            payload["message"] = "Local XHS auth passed the live API check."
        elif technical_failure:
            payload["message"] = f"Local XHS auth could not be verified because the API runtime failed: {message}"
        else:
            payload["message"] = f"Local XHS auth failed the live API check: {message}"
        save_auth_meta(payload, {"last_check": {"success": valid, "msg": message, "checked_at": now_iso()}})
    elif payload["structural_usable"]:
        payload["status"] = "present"
        payload["message"] = "Local XHS auth has the required cookie names but was not verified online."
    meta = load_auth_meta()
    if meta:
        payload["saved_at"] = meta.get("saved_at")
        payload["last_check"] = meta.get("last_check")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{payload['message']} Source: {source}")
        if payload["missing"]:
            print("Missing key names: " + ", ".join(payload["missing"]))
    if args.show_redacted:
        print(redacted_cookie(cookie))


def logout(_: argparse.Namespace) -> None:
    removed = []
    for path in [COOKIE_PATH, STATE_PATH, AUTH_META_PATH]:
        if path.exists():
            path.unlink()
            removed.append(str(path))
    print("Removed: " + ", ".join(removed) if removed else "No local auth files found.")


def check(_: argparse.Namespace) -> None:
    cookie = load_cookie()
    if not cookie:
        raise SystemExit("No cookie found. Run xhs_auth.py login first.")
    success, message = validate_cookie(resolve_tool(None), cookie)
    cookie_status = auth_status_from_cookie(cookie, f"<skill-dir>/{skill_relative(COOKIE_PATH)}" if COOKIE_PATH.exists() else "XHS_COOKIE")
    cookie_status["verified"] = True
    cookie_status["usable"] = success
    cookie_status["status"] = "valid" if success else "invalid"
    check_payload = {"success": success, "msg": message, "auth": cookie_status, "checked_at": now_iso()}
    save_auth_meta(cookie_status, {"last_check": check_payload})
    print(json.dumps({"success": success, "msg": message, "checked_at": check_payload["checked_at"]}, ensure_ascii=False, indent=2))
    if not success:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Xiaohongshu browser-login helper for xhs-report.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("login", help="Open a browser and save local XHS cookies after user login.")
    login_parser.add_argument("--channel", default="", help="Optional Playwright browser channel, e.g. chrome or msedge. If omitted, auto-detect.")
    login_parser.add_argument("--executable-path", default="", help="Optional browser executable path.")
    login_parser.add_argument("--slow-mo", type=int, default=0)
    login_parser.add_argument("--verbose", action="store_true", help="Print browser launch attempts.")
    login_parser.add_argument("--show-redacted", action="store_true", help="Print redacted cookie values for debugging.")
    login_parser.add_argument("--wait-auto", action="store_true", help="Automatically wait until usable local auth is detected.")
    login_parser.add_argument("--timeout", type=int, default=180, help="Maximum seconds to wait with --wait-auto.")
    login_parser.add_argument("--auto-install-browser", action=argparse.BooleanOptionalAction, default=True, help="Install Playwright Chromium automatically if no controllable browser is found.")
    login_parser.set_defaults(func=login)

    status_parser = subparsers.add_parser("status", help="Show whether local XHS auth exists.")
    status_parser.add_argument("--show-redacted", action="store_true", help="Print redacted cookie values for debugging.")
    status_parser.add_argument("--json", action="store_true", help="Print machine-readable auth status without cookie values.")
    status_parser.add_argument("--offline", action="store_true", help="Only inspect cookie names without calling the live API.")
    status_parser.set_defaults(func=status)

    check_parser = subparsers.add_parser("check", help="Check whether the stored cookie can call self-info API.")
    check_parser.set_defaults(func=check)

    logout_parser = subparsers.add_parser("logout", help="Remove local stored cookies and browser state.")
    logout_parser.set_defaults(func=logout)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
