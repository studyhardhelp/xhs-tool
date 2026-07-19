#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from pathlib import Path


RAW_PATTERNS = ("raw.json", "raw.workflow.json", "raw.partial.json")


def expired_raw_files(root: Path, older_than_days: int, now: float | None = None) -> list[Path]:
    if older_than_days < 1:
        raise ValueError("older-than-days must be at least 1.")
    root = root.resolve()
    if not root.exists():
        return []
    cutoff = (time.time() if now is None else now) - older_than_days * 86400
    files = []
    for pattern in RAW_PATTERNS:
        for path in root.rglob(pattern):
            resolved = path.resolve()
            if root not in resolved.parents or not resolved.is_file():
                continue
            if resolved.stat().st_mtime < cutoff:
                files.append(resolved)
    return sorted(set(files))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or purge retained raw XHS run data.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1] / "runs"))
    parser.add_argument("--older-than-days", type=int, default=30)
    parser.add_argument("--execute", action="store_true", help="Delete matching raw files. Without this flag, only list them.")
    args = parser.parse_args()

    files = expired_raw_files(Path(args.root), args.older_than_days)
    for path in files:
        print(path)
        if args.execute:
            path.unlink()
    action = "removed" if args.execute else "matched"
    print(f"{action}: {len(files)} raw files")


if __name__ == "__main__":
    main()
