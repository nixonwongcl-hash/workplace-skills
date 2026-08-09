#!/usr/bin/env python3
"""Sync canonical workplace skills into one or more installed skill roots."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

IGNORED_PARTS = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def should_copy(path: Path) -> bool:
    return not any(part in IGNORED_PARTS for part in path.parts) and path.suffix not in IGNORED_SUFFIXES


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--target", type=Path, action="append", required=True)
    args = parser.parse_args()

    manifest = json.loads((args.repo_root / "skill_versions.json").read_text(encoding="utf-8"))
    copied = 0

    for folder, metadata in manifest["skills"].items():
        source_root = args.repo_root / folder
        for target_root in args.target:
            destination_root = target_root / folder
            destination_root.mkdir(parents=True, exist_ok=True)
            for source in source_root.rglob("*"):
                relative = source.relative_to(source_root)
                if not source.is_file() or not should_copy(relative):
                    continue
                destination = destination_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                copied += 1
            print(f"synced {folder} v{metadata['version']} -> {destination_root}")

    print(f"Copied {copied} canonical files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())