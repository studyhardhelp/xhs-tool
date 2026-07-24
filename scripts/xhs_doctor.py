#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from verify_runtime import verify_runtime
from xhs_auth import BROWSERS_PATH, COOKIE_PATH, auth_status_from_cookie, common_browser_paths, load_cookie


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MODULES = ["openpyxl", "execjs", "requests", "loguru", "playwright", "jieba"]


@dataclass
class CheckResult:
    name: str
    status: str
    message: str
    remediation: str = ""


def run_command(command: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=timeout)
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    output = (completed.stdout or completed.stderr or "").strip().splitlines()
    return completed.returncode, output[0] if output else ""


def check_python() -> CheckResult:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 9):
        return CheckResult("python", "ok", f"Python {version}: {sys.executable}")
    return CheckResult("python", "fail", f"Python {version} is too old.", "Use Python 3.9+ and rerun bootstrap_env.sh.")


def check_node() -> CheckResult:
    path = shutil.which("node")
    if not path:
        return CheckResult("node", "fail", "Node.js was not found.", "Install Node.js 18+ and npm.")
    code, output = run_command(["node", "--version"])
    version = output.lstrip("v")
    major = int(version.split(".", 1)[0]) if version.split(".", 1)[0].isdigit() else 0
    if code == 0 and major >= 18:
        return CheckResult("node", "ok", f"Node.js {output}: {path}")
    return CheckResult("node", "fail", f"Node.js {output or 'unknown'} is too old.", "Install Node.js 18+.")


def check_npm() -> CheckResult:
    path = shutil.which("npm")
    if not path:
        return CheckResult("npm", "fail", "npm was not found.", "Install npm with Node.js 18+.")
    code, output = run_command(["npm", "--version"])
    if code == 0:
        return CheckResult("npm", "ok", f"npm {output}: {path}")
    return CheckResult("npm", "fail", "npm exists but could not run.", "Reinstall Node.js/npm.")


def check_python_modules() -> CheckResult:
    missing = [module for module in REQUIRED_MODULES if importlib.util.find_spec(module) is None]
    if not missing:
        return CheckResult("python-deps", "ok", "Required Python modules are importable.")
    return CheckResult(
        "python-deps",
        "fail",
        "Missing Python modules: " + ", ".join(missing),
        "Run: bash scripts/bootstrap_env.sh",
    )


def check_node_modules() -> CheckResult:
    modules_dir = PROJECT_ROOT / "scripts" / "node_modules"
    if modules_dir.is_dir():
        return CheckResult("node-deps", "ok", "scripts/node_modules exists.")
    return CheckResult("node-deps", "fail", "scripts/node_modules is missing.", "Run: npm ci --prefix scripts --ignore-scripts --no-audit --no-fund")


def check_runtime_manifest() -> CheckResult:
    errors = verify_runtime()
    if not errors:
        return CheckResult("runtime", "ok", "Vendored runtime manifest matches checked-in files.")
    return CheckResult("runtime", "fail", "; ".join(errors[:5]), "Review runtime changes and regenerate scripts/runtime/MANIFEST.sha256 if intentional.")


def check_browser() -> CheckResult:
    browsers = common_browser_paths()
    if browsers:
        return CheckResult("browser", "ok", f"Found controllable Chromium-family browser: {browsers[0]}")
    if BROWSERS_PATH.exists():
        return CheckResult("browser", "warn", f"No installed Chrome/Edge/Chromium found, but skill-local browser cache exists: {BROWSERS_PATH}")
    return CheckResult(
        "browser",
        "warn",
        "No installed Chrome/Edge/Chromium browser was found.",
        "Install Chrome/Edge/Chromium, or explicitly allow skill-local Chromium with XHS_INSTALL_BROWSER=1.",
    )


def check_auth(online_auth_check: bool = False) -> CheckResult:
    cookie = load_cookie()
    source = "XHS_COOKIE" if os.environ.get("XHS_COOKIE") else str(COOKIE_PATH)
    status = auth_status_from_cookie(cookie, source)
    if not cookie:
        return CheckResult("auth", "warn", "No local XHS login state found.", "Run: .venv/bin/python scripts/xhs_auth.py login --wait-auto")
    if not status["structural_usable"]:
        return CheckResult("auth", "warn", "Local XHS cookies exist but required cookie names are incomplete.", "Run browser login again with scripts/xhs_auth.py login --wait-auto")
    if not online_auth_check:
        return CheckResult("auth", "ok", "Local XHS cookies have the required names. Live API check was skipped.")

    from collect_notes import resolve_tool, validate_cookie

    valid, message = validate_cookie(resolve_tool(None), cookie)
    if valid:
        return CheckResult("auth", "ok", "Local XHS auth passed the live API check.")
    return CheckResult("auth", "warn", "Local XHS auth did not pass the live API check: " + message, "Run browser login again.")


def check_token_platform() -> CheckResult:
    names = ["TOKEN_PLATFORM_BASE_URL", "TOKEN_PLATFORM_API_KEY", "TOKEN_PLATFORM_MODEL"]
    missing = [name for name in names if not os.environ.get(name)]
    if not missing:
        return CheckResult("token-platform", "ok", "Token Platform chat environment variables are configured.")
    return CheckResult("token-platform", "warn", "Token Platform is not fully configured: " + ", ".join(missing), "Only deterministic local summaries/drafts will be available.")


def check_runs_dir() -> CheckResult:
    runs_dir = PROJECT_ROOT / "runs"
    try:
        runs_dir.mkdir(exist_ok=True)
        probe = runs_dir / ".doctor_write_test"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return CheckResult("runs-dir", "fail", f"Cannot write to runs directory: {exc}", "Fix local filesystem permissions for the skill directory.")
    return CheckResult("runs-dir", "ok", "runs directory is writable.")


def build_diagnostics(online_auth_check: bool = False) -> dict:
    checks = [
        check_python(),
        check_node(),
        check_npm(),
        check_python_modules(),
        check_node_modules(),
        check_runtime_manifest(),
        check_browser(),
        check_auth(online_auth_check=online_auth_check),
        check_token_platform(),
        check_runs_dir(),
    ]
    counts = {status: sum(1 for check in checks if check.status == status) for status in ["ok", "warn", "fail"]}
    overall = "fail" if counts["fail"] else "warn" if counts["warn"] else "ok"
    return {
        "overall": overall,
        "platform": platform.platform(),
        "skill_dir": str(PROJECT_ROOT),
        "online_auth_check": online_auth_check,
        "counts": counts,
        "checks": [asdict(check) for check in checks],
    }


def print_text_report(payload: dict) -> None:
    print(f"xhs-tool doctor: {payload['overall'].upper()}")
    print(f"Skill dir: {payload['skill_dir']}")
    print(f"Platform: {payload['platform']}")
    print("")
    for check in payload["checks"]:
        marker = {"ok": "OK", "warn": "WARN", "fail": "FAIL"}.get(check["status"], check["status"].upper())
        print(f"[{marker}] {check['name']}: {check['message']}")
        if check.get("remediation"):
            print(f"      -> {check['remediation']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose local xhs-tool installation and readiness.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable diagnostics.")
    parser.add_argument("--online-auth-check", action="store_true", help="Call the live XHS self-info API to verify stored auth.")
    args = parser.parse_args()
    payload = build_diagnostics(online_auth_check=args.online_auth_check)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text_report(payload)
    if payload["overall"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
