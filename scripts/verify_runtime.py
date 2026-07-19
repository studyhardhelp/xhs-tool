#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path


RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
MANIFEST_PATH = RUNTIME_DIR / "MANIFEST.sha256"


def verify_runtime() -> list[str]:
    errors = []
    expected_paths = set()
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        expected_hash, relative_path = line.split(maxsplit=1)
        relative_path = relative_path.strip()
        expected_paths.add(relative_path)
        path = RUNTIME_DIR / relative_path
        if not path.is_file():
            errors.append(f"missing: {relative_path}")
            continue
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            errors.append(f"checksum mismatch: {relative_path}")
    actual_paths = {
        str(path.relative_to(RUNTIME_DIR))
        for path in RUNTIME_DIR.rglob("*")
        if path.is_file() and path != MANIFEST_PATH and "__pycache__" not in path.parts
    }
    for relative_path in sorted(actual_paths - expected_paths):
        errors.append(f"unlisted: {relative_path}")
    return errors


def main() -> None:
    errors = verify_runtime()
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print(f"runtime integrity: OK ({len(MANIFEST_PATH.read_text().splitlines())} files)")


if __name__ == "__main__":
    main()
