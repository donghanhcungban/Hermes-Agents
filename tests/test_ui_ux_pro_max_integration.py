"""Integration checks for the Hermes UI/UX Pro Max skill."""

from __future__ import annotations

import subprocess
import sys
import unittest
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "ui-ux-pro-max"


class UiUxProMaxIntegrationTests(unittest.TestCase):
    def test_skill_frontmatter_and_provenance(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("\nname: ui-ux-pro-max\n", text)
        provenance = (SKILL / "UPSTREAM.md").read_text(encoding="utf-8")
        self.assertIn("dcc40ff5133ef78276117db0cc34e7b83cc8aeba", provenance)

    def test_sync_manifest_is_present_and_pinned(self) -> None:
        sync = runpy.run_path(str(SKILL / "scripts" / "sync_upstream.py"))
        self.assertEqual(sync["UPSTREAM_COMMIT"], "dcc40ff5133ef78276117db0cc34e7b83cc8aeba")
        self.assertEqual(len(sync["MANIFEST"]), 41)
        for path, sha, size in sync["MANIFEST"]:
            with self.subTest(path=path):
                data = sync["destination"](path).read_bytes()
                self.assertEqual(len(data), size)
                self.assertEqual(sync["git_blob_sha"](data), sha)
        self.assertIn("Permission is hereby granted", (SKILL / "LICENSE").read_text(encoding="utf-8"))

    def test_search_engine_smoke(self) -> None:
        search = SKILL / "scripts" / "search.py"
        self.assertTrue(search.is_file())
        proc = subprocess.run(
            [sys.executable, str(search), "keyboard focus modal", "--domain", "ux", "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('"domain": "ux"', proc.stdout)


if __name__ == "__main__":
    unittest.main()
