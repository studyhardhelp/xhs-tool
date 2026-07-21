#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
SENSITIVE_KEY_PARTS = (
    "authorization",
    "avatar",
    "cookie",
    "email",
    "headers",
    "phone",
    "session",
    "token",
)


def ensure_private_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        directory.chmod(PRIVATE_DIR_MODE)
    except OSError:
        pass
    return directory


def write_private_text(path: str | Path, text: str) -> Path:
    target = Path(path)
    ensure_private_dir(target.parent)
    target.write_text(text, encoding="utf-8")
    protect_private_file(target)
    return target


def protect_private_file(path: str | Path) -> Path:
    target = Path(path)
    try:
        target.chmod(PRIVATE_FILE_MODE)
    except OSError:
        pass
    return target


def write_private_json(path: str | Path, data: Any) -> Path:
    return write_private_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def sanitize_error(message: Any) -> str:
    text = str(message or "")
    text = re.sub(r"(?i)(cookie|authorization|web_session|a1|email|phone)\s*[=:]\s*[^\s;,]+", r"\1=[redacted]", text)
    text = re.sub(r"(?i)(xsec_token=)[^&\s]+", r"\1[redacted]", text)
    return text[:1000]


def sanitize_raw_data(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
                result[key] = "[redacted]"
            else:
                result[key] = sanitize_raw_data(item)
        return result
    if isinstance(value, list):
        return [sanitize_raw_data(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_raw_data(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"(?i)(xsec_token=)[^&\s]+", r"\1[redacted]", value)
    return value


def enforce_limit(name: str, value: int, minimum: int, maximum: int) -> int:
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value
