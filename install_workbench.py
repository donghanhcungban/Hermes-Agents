#!/usr/bin/env python3
"""Opt-in installer. Dry run by default; never edits provider config or credentials."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "plugins" / "engineering-workbench"


def install(home: Path, apply=False, upgrade=False):
    home = home.expanduser().absolute()
    destination = home / "plugins" / "engineering-workbench"
    # Reject all symlink ancestors instead of resolving a link and overwriting its target.
    for item in (home, *home.parents, home / "plugins", destination):
        if item.is_symlink():
            raise ValueError("Symlink install paths are not supported")
    if SOURCE.is_symlink() or not SOURCE.is_dir() or any(p.is_symlink() for p in SOURCE.rglob("*")):
        raise ValueError("Plugin source is missing or contains symlinks")
    if destination.exists() and not upgrade:
        raise ValueError("Plugin already exists; review it and use --upgrade to back up and replace")
    result = {"action": "install" if apply else "dry_run", "destination": str(destination),
              "provider_config_changed": False, "enabled": False}
    if not apply:
        return result
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".workbench-stage-", dir=home))
    backup = None
    try:
        shutil.copytree(SOURCE, stage / "plugin", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if destination.exists():
            # Sibling backup is outside the scanned plugins directory.
            backup_root = home / "workbench-backups"
            if backup_root.is_symlink():
                raise ValueError("Backup directory cannot be a symlink")
            backup_root.mkdir(mode=0o700, exist_ok=True)
            backup = backup_root / uuid.uuid4().hex
            destination.rename(backup)
        (stage / "plugin").rename(destination)
    except Exception:
        if backup is not None and backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    finally:
        shutil.rmtree(stage)
    if backup is not None:
        result["backup"] = str(backup)
    result["next"] = "hermes plugins enable engineering-workbench; restart the Hermes session"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-home", type=Path, default=Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--upgrade", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.hermes_home, args.apply, args.upgrade), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Installation failed: {exc}\n")


if __name__ == "__main__":
    main()
