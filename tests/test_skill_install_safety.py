"""Safety regressions with synthetic skills, never a real Hermes home."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("safe_installer_under_test", ROOT / "install.py")
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class SkillInstallSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.package = self.root / "package"
        self.home = self.root / "home"
        self.source = self.package / "skills" / "example"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_text("---\nname: example\n---\nNEW\n")
        self.override = patch.object(INSTALLER, "PACKAGE_DIR", self.package)
        self.override.start()

    def tearDown(self):
        self.override.stop()
        self.temp.cleanup()

    def test_backs_up_same_name_user_edits(self):
        old = self.home / "skills" / "category" / "custom-example"
        old.mkdir(parents=True)
        (old / "SKILL.md").write_text("---\nname: example\n---\nPRIVATE EDITS\n")
        INSTALLER.install_bundled_skills(self.home)
        self.assertFalse(old.exists())
        backups = list((self.home / "skill-backups").rglob("SKILL.md"))
        self.assertTrue(any("PRIVATE EDITS" in p.read_text() for p in backups))
        self.assertIn("NEW", (self.home / "skills/example/SKILL.md").read_text())

    def test_refuses_external_destination_link_without_touching_target(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "KEEP").write_text("KEEP")
        (self.home / "skills").mkdir(parents=True)
        (self.home / "skills/example").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            INSTALLER.install_bundled_skills(self.home)
        self.assertEqual((outside / "KEEP").read_text(), "KEEP")

    def test_refuses_linked_skills_root(self):
        self.home.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (self.home / "skills").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            INSTALLER.install_bundled_skills(self.home)
        self.assertEqual(list(outside.iterdir()), [])

    def test_file_collision_is_backed_up(self):
        (self.home / "skills").mkdir(parents=True)
        (self.home / "skills/example").write_text("OLD FILE")
        INSTALLER.install_bundled_skills(self.home)
        self.assertTrue(any(p.is_file() and p.read_text() == "OLD FILE" for p in (self.home / "skill-backups").rglob("example")))

    def test_source_link_is_rejected(self):
        (self.source / "data").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            INSTALLER.install_bundled_skills(self.home)
        self.assertFalse(self.home.exists())

    def test_failed_publish_restores_original(self):
        old = self.home / "skills/example"
        old.mkdir(parents=True)
        (old / "SKILL.md").write_text("ORIGINAL")
        real_rename = Path.rename
        def fail_staged_publish(path, target):
            if path.name == "skill" and path.parent.name.startswith(".skill-stage-"):
                raise OSError("Synthetic publish failure")
            return real_rename(path, target)
        with patch.object(Path, "rename", fail_staged_publish):
            with self.assertRaises(OSError):
                INSTALLER.install_bundled_skills(self.home)
        self.assertEqual((old / "SKILL.md").read_text(), "ORIGINAL")

    def test_root_skill_file_is_never_moved(self):
        (self.home / "skills").mkdir(parents=True)
        root_file = self.home / "skills/SKILL.md"
        root_file.write_text("---\nname: example\n---\nROOT\n")
        INSTALLER.install_bundled_skills(self.home)
        self.assertTrue(root_file.exists())


if __name__ == "__main__":
    unittest.main()
