#!/usr/bin/env python3
"""Black-box checks for grill-tab's distributable installer."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PYTHON = Path(os.environ.get("PYTHON_BIN", sys.executable))


def make_hermes(directory: Path, version: str) -> Path:
    executable = directory / "hermes"
    executable.write_text(f"#!/usr/bin/env bash\necho 'Hermes Agent v{version}'\n", encoding="utf-8")
    executable.chmod(0o755)
    return executable


def copy_repo(directory: Path) -> Path:
    destination = directory / "grill-tab"
    shutil.copytree(REPO, destination, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "assets"))
    return destination


class InstallerTests(unittest.TestCase):
    def run_install(self, source: Path, home: Path, hermes: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update({"PYTHON_BIN": str(PYTHON), "HERMES_BIN": str(hermes), "HERMES_HOME": str(home)})
        return subprocess.run(
            ["bash", "install.sh", "--home", str(home)], cwd=source, env=environment,
            text=True, capture_output=True, check=False,
        )

    def test_unsupported_hermes_fails_before_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "untouched-home"
            result = self.run_install(copy_repo(root), home, make_hermes(root, "0.19.9"))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("[ERROR] Incompatible Hermes version: requires >=0.20.0, running 0.19.9", result.stderr)
            self.assertFalse(home.exists(), "pre-flight must not create target home")

    def test_malformed_manifest_fails_before_registration(self) -> None:
        with tempfile.Tempor