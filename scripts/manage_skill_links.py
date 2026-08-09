#!/usr/bin/env python3
"""Manage recoverable per-skill junctions to the canonical workplace skill store."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def load_config(repo_root: Path, config_path: Path | None = None) -> tuple[dict[str, Any], list[str]]:
    config_file = config_path or repo_root / "agent_targets.json"
    config = json.loads(config_file.read_text(encoding="utf-8"))
    manifest = json.loads((repo_root / "skill_versions.json").read_text(encoding="utf-8"))
    return config, list(manifest["skills"].keys())


def is_junction(path: Path) -> bool:
    checker = getattr(os.path, "isjunction", None)
    return bool(checker and checker(path))


def is_link(path: Path) -> bool:
    return path.is_symlink() or is_junction(path)


def path_exists(path: Path) -> bool:
    return os.path.lexists(path)


def resolves_to(path: Path, expected: Path) -> bool:
    if not path_exists(path) or not is_link(path):
        return False
    try:
        return path.resolve(strict=True) == expected.resolve(strict=True)
    except OSError:
        return False


def remove_link(path: Path) -> None:
    if is_junction(path):
        os.rmdir(path)
    elif path.is_symlink():
        path.unlink()
    else:
        raise RuntimeError(f"Refusing to remove non-link path: {path}")


def create_junction(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(destination), str(source)],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create junction {destination} -> {source}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def validate_source(repo_root: Path, skill: str) -> Path:
    source = (repo_root / skill).resolve(strict=True)
    if source.parent != repo_root.resolve(strict=True):
        raise RuntimeError(f"Skill source escaped canonical root: {skill}")
    if not (source / "SKILL.md").is_file():
        raise RuntimeError(f"Canonical skill is incomplete: {source}")
    return source


def configured_targets(config: dict[str, Any], selected: set[str] | None) -> list[dict[str, str]]:
    targets = config["targets"]
    if selected:
        targets = [target for target in targets if target["id"] in selected]
        missing = selected - {target["id"] for target in targets}
        if missing:
            raise RuntimeError(f"Unknown target IDs: {', '.join(sorted(missing))}")
    return targets


def audit(
    repo_root: Path,
    config: dict[str, Any],
    skills: list[str],
    selected: set[str] | None = None,
) -> int:
    mismatches = 0
    for target in configured_targets(config, selected):
        root = expand_path(target["skills_root"])
        for skill in skills:
            source = validate_source(repo_root, skill)
            destination = root / skill
            if resolves_to(destination, source):
                print(f"OK       {target['id']}/{skill} -> {source}")
            else:
                state = "missing"
                if path_exists(destination):
                    state = "wrong-link" if is_link(destination) else "local-copy"
                print(f"MISMATCH {target['id']}/{skill}: {state}")
                mismatches += 1
    print(f"Audit complete: {mismatches} mismatch(es).")
    return 1 if mismatches else 0


def install(
    repo_root: Path,
    config: dict[str, Any],
    skills: list[str],
    selected: set[str] | None,
    dry_run: bool,
) -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = expand_path(config["backup_root"]) / timestamp
    records: list[dict[str, str]] = []

    for target in configured_targets(config, selected):
        root = expand_path(target["skills_root"])
        if not dry_run:
            root.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            source = validate_source(repo_root, skill)
            destination = root / skill
            if resolves_to(destination, source):
                print(f"UNCHANGED {target['id']}/{skill}")
                continue

            backup = backup_root / target["id"] / skill
            backup_for_record = ""
            if path_exists(destination):
                if is_link(destination):
                    print(f"{'WOULD REMOVE' if dry_run else 'REMOVING'} incorrect link {destination}")
                    if not dry_run:
                        remove_link(destination)
                else:
                    print(f"{'WOULD BACK UP' if dry_run else 'BACKING UP'} {destination} -> {backup}")
                    if not dry_run:
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(destination), str(backup))
                        backup_for_record = str(backup)


            print(f"{'WOULD LINK' if dry_run else 'LINKING'} {destination} -> {source}")
            if not dry_run:
                create_junction(source, destination)
                records.append(
                    {
                        "target_id": target["id"],
                        "destination": str(destination),
                        "backup": backup_for_record,
                    }
                )

    if not dry_run:
        backup_root.mkdir(parents=True, exist_ok=True)
        metadata = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "canonical_root": str(repo_root.resolve()),
            "records": records,
        }
        (backup_root / "migration.json").write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Backup metadata: {backup_root / 'migration.json'}")
    return 0


def restore(backup_path: Path) -> int:
    metadata_file = backup_path / "migration.json" if backup_path.is_dir() else backup_path
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    for record in reversed(metadata["records"]):
        destination = Path(record["destination"])
        backup = Path(record["backup"])
        if path_exists(destination):
            if not is_link(destination):
                raise RuntimeError(f"Restore blocked by non-link destination: {destination}")
            print(f"REMOVING {destination}")
            remove_link(destination)
        if record["backup"]:
            if not backup.exists():
                raise RuntimeError(f"Backup is missing: {backup}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            print(f"RESTORING {backup} -> {destination}")
            shutil.move(str(backup), str(destination))
    print("Restore complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--config", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--target", action="append", default=[])

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("--target", action="append", default=[])
    install_parser.add_argument("--dry-run", action="store_true")

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--backup", type=Path, required=True)

    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "restore":
            return restore(args.backup.resolve())
        config, skills = load_config(repo_root, args.config)
        selected = set(args.target) if args.target else None
        if args.command == "audit":
            return audit(repo_root, config, skills, selected)
        return install(repo_root, config, skills, selected, args.dry_run)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())