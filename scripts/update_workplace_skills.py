#!/usr/bin/env python3
"""Safely refresh the canonical workplace skills checkout and audit all links."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run(command: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def append_log(message: str) -> None:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WorkplaceSkills" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    with (base / "update.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    try:
        status = run(["git", "status", "--porcelain"], repo_root).stdout.strip()
        if status:
            raise RuntimeError("Canonical checkout has local changes; automatic pull was skipped.")

        if not args.check_only:
            run(["git", "fetch", "origin", "--prune"], repo_root)
            run(["git", "pull", "--ff-only"], repo_root)

        verify = run([sys.executable, str(repo_root / "scripts" / "verify_skill_versions.py")], repo_root)
        audit = run(
            [sys.executable, str(repo_root / "scripts" / "manage_skill_links.py"), "audit"],
            repo_root,
            check=False,
        )
        if audit.returncode != 0:
            raise RuntimeError(audit.stdout.strip() or audit.stderr.strip())

        summary = verify.stdout.strip().splitlines()[-1]
        append_log(f"OK {summary}")
        print(summary)
        print("All configured agent links are current.")
        return 0
    except (OSError, RuntimeError) as exc:
        append_log(f"ERROR {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())