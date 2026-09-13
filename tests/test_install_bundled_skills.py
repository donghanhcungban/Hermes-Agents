"""Regression tests for bundled skill installation."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("plugin_installer", ROOT / "install.py")
assert SPEC is not None and SPEC.loader is not None
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class BundledSkillInstallTests(unittest.TestCase):
    def test_installs_bundle_and_preserves_user_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_home = Path(tmp)
            user_skill = hermes_home / "skills" / "my-private-skill" / "SKILL.md"
            user_skill.parent.mkdir(parents=True)
            user_skill.write_text("private\n", encoding="utf-8")

            installed = INSTALLER.install_bundled_skills(hermes_home)

            expected = sorted([d.name for d in (ROOT / "skills").iterdir() if d.is_dir() and (d / "SKILL.md").is_file()])
            self.assertEqual(installed, expected)
            self.assertEqual(user_skill.read_text(encoding="utf-8"), "private\n")
            for name in installed:
                self.assertTrue((hermes_home / "skills" / name / "SKILL.md").is_file())

    def test_replaces_file_occupying_skill_slot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_home = Path(tmp)
            slot = hermes_home / "skills" / "antigravity-oauth-bridge"
            slot.parent.mkdir(parents=True)
            slot.write_text("stale", encoding="utf-8")

            INSTALLER.install_bundled_skills(hermes_home)

            self.assertTrue((slot / "SKILL.md").is_file())

    def test_removes_duplicate_category_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_home = Path(tmp)
            duplicate = hermes_home / "skills" / "autonomous-ai-agents" / "hermes-provider-management" / "SKILL.md"
            duplicate.parent.mkdir(parents=True)
            duplicate.write_text("---\nname: hermes-provider-management\ndescription: test\n---\n", encoding="utf-8")

            INSTALLER.install_bundled_skills(hermes_home)

            self.assertFalse(duplicate.exists())
            self.assertTrue((hermes_home / "skills" / "hermes-provider-management" / "SKILL.md").is_file())

    def test_bundle_frontmatter_names_match_directories(self) -> None:
        for skill_dir in sorted((ROOT / "skills").iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            text = skill_file.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"))
            self.assertIn(f"\nname: {skill_dir.name}\n", text)


if __name__ == "__main__":
    unittest.main()
