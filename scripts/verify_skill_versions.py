#!/usr/bin/env python3
"""Verify workplace skill versions against the repository manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VERSION_RE = re.compile(r"^Current version:\s*\*\*v(\d+\.\d+\.\d+)\*\*", re.MULTILINE)


def read_version(skill_file: Path) -> str | None:
    if not skill_file.is_file():
        return None
    match = VERSION_RE.search(skill_file.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--installed-root", type=Path, action="append", default=[])
    args = parser.parse_args()

    manifest = json.loads((args.repo_root / "skill_versions.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    for folder, metadata in manifest["skills"].items():
        expected = metadata["version"]
        canonical = read_version(args.repo_root / metadata["path"])
        if canonical != expected:
            failures.append(f"canonical {folder}: expected {expected}, found {canonical or 'missing'}")

        for installed_root in args.installed_root:
            installed = read_version(installed_root / folder / "SKILL.md")
            if installed != expected:
                failures.append(
                    f"installed {installed_root / folder}: expected {expected}, "
                    f"found {installed or 'missing'}"
                )

    if failures:
        print("Skill version check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"All {len(manifest['skills'])} canonical skill versions match the manifest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
