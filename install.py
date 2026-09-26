#!/usr/bin/env python3
"""1-Click Standalone Installer for Hermes Antigravity OAuth Plugin.

Works on:
- Local machines (Windows, macOS, Linux)
- Cloud / VPS (Oracle Cloud, Ubuntu, Debian, CentOS, Docker)

Usage:
  python install.py
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

def get_hermes_home() -> Path:
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        return Path(hermes_home).expanduser().resolve()
    return Path.home() / ".hermes"


def _get_skill_name(skill_file: Path) -> str | None:
    try:
        content = skill_file.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) >= 3:
            match = re.search(r"^name:\s*['\"]?([A-Za-z0-9_\-]+)['\"]?", parts[1], re.MULTILINE)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def install_bundled_skills(hermes_dir: Path) -> list[str]:
    """Install flat skills; back up replaced copies and never follow symlinks.

    Backups live outside Hermes' skill scan. The transaction is per skill, not
    the entire installer. Run only in a trusted, single-user installation root.
    """
    import tempfile
    import uuid

    source_root = PACKAGE_DIR / "skills"
    if not source_root.is_dir():
        return []
    home = Path(hermes_dir).expanduser().absolute()
    destination_root = home / "skills"
    backup_root = home / "skill-backups"
    for item in (home, *home.parents, destination_root, backup_root, source_root):
        if item.is_symlink():
            raise ValueError(f"Refusing symlink skill installation path: {item}")
    sources = [p for p in sorted(source_root.iterdir()) if p.is_dir() and (p / "SKILL.md").is_file()]
    for source in sources:
        if source.is_symlink() or any(p.is_symlink() for p in source.rglob("*")):
            raise ValueError(f"Refusing symlink in bundled skill: {source.name}")
        if (destination_root / source.name).is_symlink():
            raise ValueError(f"Refusing symlink skill destination: {source.name}")
    home.mkdir(parents=True, exist_ok=True)
    destination_root.mkdir(exist_ok=True)
    installed = []
    for source in sources:
        destination = destination_root / source.name  # Deliberately NOT resolve().
        name = _get_skill_name(source / "SKILL.md") or source.name
        replacements = [destination] if destination.exists() else []
        # os.walk explicitly does not traverse links to external skill trees.
        for directory, subdirs, filenames in os.walk(destination_root, followlinks=False):
            parent = Path(directory)
            subdirs[:] = [d for d in subdirs if not (parent / d).is_symlink()]
            existing = parent / "SKILL.md"
            if (parent != destination_root and parent != destination
                    and "SKILL.md" in filenames and not existing.is_symlink()
                    and _get_skill_name(existing) == name):
                replacements.append(parent)
        # If a parent will be backed up, do not separately move its children.
        selected = []
        for item in sorted(set(replacements), key=lambda p: len(p.parts)):
            if not any(item.is_relative_to(parent) for parent in selected):
                selected.append(item)
        moved = []
        with tempfile.TemporaryDirectory(prefix=".skill-stage-", dir=home) as temp:
            staged = Path(temp) / "skill"
            shutil.copytree(source, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            try:
                if selected:
                    backup = backup_root / uuid.uuid4().hex
                    backup.mkdir(parents=True, mode=0o700)
                    for old in selected:
                        target = backup / old.relative_to(destination_root)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        old.rename(target)
                        moved.append((old, target))
                staged.rename(destination)
            except Exception:
                for old, target in reversed(moved):
                    old.parent.mkdir(parents=True, exist_ok=True)
                    target.rename(old)
                raise
        installed.append(source.name)
    return installed


def main():
    print("=" * 65)
    print("   HERMES AGENT - GOOGLE ANTIGRAVITY OAUTH PLUGIN INSTALLER   ")
    print("=" * 65)

    hermes_dir = get_hermes_home()
    hermes_dir.mkdir(parents=True, exist_ok=True)

    # 1. Install Plugin
    plugin_dest = hermes_dir / "plugins" / "model-providers" / "antigravity"
    plugin_src = PACKAGE_DIR / "plugin"
    print(f"\n[1/6] Installing Provider Plugin to {plugin_dest}...")
    plugin_dest.mkdir(parents=True, exist_ok=True)
    for f in plugin_src.glob("*"):
        if f.is_file():
            shutil.copy2(f, plugin_dest / f.name)
            print(f"      + Copied {f.name}")

    # 2. Install Bridge Engine
    bridge_dest = hermes_dir / "bridge" / "antigravity" / "tools" / "antigravity_bridge"
    bridge_src = PACKAGE_DIR / "bridge"
    print(f"\n[2/6] Installing Bridge Runtime Engine to {bridge_dest}...")
    bridge_dest.parent.mkdir(parents=True, exist_ok=True)
    if bridge_dest.exists():
        shutil.rmtree(bridge_dest, ignore_errors=True)
    shutil.copytree(bridge_src, bridge_dest)
    print(f"      + Copied Bridge Engine files.")

    # 3. Copy Manager
    shutil.copy2(PACKAGE_DIR / "manage.py", hermes_dir / "bridge" / "antigravity" / "manage.py")
    print(f"\n[3/6] Installed Management CLI at {hermes_dir / 'bridge' / 'antigravity' / 'manage.py'}")

    # 4. Install bundled Hermes skills
    installed_skills = install_bundled_skills(hermes_dir)
    print(f"\n[4/6] Installed bundled skills: {', '.join(installed_skills) or 'none'}")

    # 4b. Install grill-tab plugin (vendor bundled from thanhan-a17/grill-tab, MIT)
    grill_src = PACKAGE_DIR / "plugins" / "grill-tab"
    if grill_src.is_dir():
        grill_dest = hermes_dir / "plugins" / "grill-tab"
        grill_desktop_dest = hermes_dir / "desktop-plugins" / "grill-tab"
        print(f"\n[4b] Installing grill-tab plugin to {grill_dest}...")
        if grill_dest.exists():
            shutil.rmtree(grill_dest)
        shutil.copytree(grill_src, grill_dest, ignore=shutil.ignore_patterns("tests", "docs", "scripts", "desktop"))
        grill_desktop_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(grill_src / "desktop" / "plugin.js", grill_desktop_dest / "plugin.js")
        # Write .hermes-package.json for desktop plugin discovery
        import json
        (grill_desktop_dest / ".hermes-package.json").write_text(
            json.dumps({"name": "grill-tab", "version": "0.2.0", "main": "plugin.js"}, indent=2) + "\n",
            encoding="utf-8",
        )
        print("      + grill-tab plugin + desktop plugin installed")
        print("      + Set auxiliary.grill_tab in config.yaml to choose its model")
        print("        (a fast cheap model is recommended: gemini-3-flash / gpt-4o-mini)")
    else:
        print("\n[4b] grill-tab plugin source not found — skipping")

    # 5. In-Repo synchronization (if executed from inside a hermes-agent git repo)
    repo_candidate = PACKAGE_DIR.parent
    if (repo_candidate / "run_agent.py").is_file() and (repo_candidate / "hermes_cli").is_dir():
        print(f"\n[5/6] Synchronizing with local workspace repository ({repo_candidate})...")
        repo_plugin = repo_candidate / "plugins" / "model-providers" / "antigravity"
        repo_tools = repo_candidate / "tools" / "antigravity_bridge"
        repo_plugin.mkdir(parents=True, exist_ok=True)
        for f in plugin_src.glob("*"):
            if f.is_file():
                shutil.copy2(f, repo_plugin / f.name)
        if repo_tools.exists():
            shutil.rmtree(repo_tools, ignore_errors=True)
        shutil.copytree(bridge_src, repo_tools)
        print("      + Workspace repository fully synchronized.")
    else:
        print(f"\n[5/6] Standalone environment installation complete.")

    # 6. Zero-touch failover: make Hermes use Antigravity as primary (on a
    #    fresh install only — an existing configured primary is left alone)
    #    and automatically rotate to openai-codex then anthropic on rate
    #    limit / quota / auth failure. No manual `hermes fallback add` needed,
    #    and re-running this installer on an upgrade never resets a primary
    #    provider the user already configured.
    print(f"\n[6/6] Configuring automatic cross-provider failover...")
    try:
        sys.path.insert(0, str(PACKAGE_DIR))
        import manage as _manage  # local module, see manage.py

        _manage.configure_priority_fallback_preserving_existing_primary(hermes_dir)
        print("      + fallback_providers: antigravity -> openai-codex -> anthropic (auto-tried on failure)")
        print("      + Existing primary provider preserved if you already had one configured.")
        print("      + No further action needed to enable automatic rotation.")
    except Exception as exc:
        print(f"      ! Could not auto-configure failover: {exc}")
        print("      Run 'python manage.py setup' manually to finish configuration.")

    print("\n" + "=" * 65)
    print(" INSTALLATION COMPLETED SUCCESSFULLY!")
    print("=" * 65)
    print("\nNext Steps:")
    print("  1. Log in with your Google account(s):")
    print("     python manage.py login       (repeat for additional accounts)")
    print("  2. Start bridge server daemon:")
    print("     python manage.py start")
    print("  3. Chat — Hermes already uses Antigravity as primary, with")
    print("     automatic openai-codex -> anthropic failover on rate limit.")
    print("     (Run 'python manage.py setup --no-fallback' to opt out of the")
    print("      automatic cross-provider chain, or --as-fallback-only to keep")
    print("      your existing primary provider and only add antigravity as a")
    print("      fallback option instead of the new primary.)")
    print("=" * 65)

if __name__ == "__main__":
    main()
