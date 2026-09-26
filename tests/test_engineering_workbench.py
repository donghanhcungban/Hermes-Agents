"""Offline regression tests: native registration, numerical kernels, exports and installer."""
from __future__ import annotations
import importlib.util
import json
import math
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "engineering-workbench"
spec = importlib.util.spec_from_file_location("engineering_workbench", PLUGIN / "__init__.py", submodule_search_locations=[str(PLUGIN)])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
installer_spec = importlib.util.spec_from_file_location("workbench_installer", ROOT / "install_workbench.py")
installer = importlib.util.module_from_spec(installer_spec)
installer_spec.loader.exec_module(installer)


def call(name, args):
    return json.loads(module.HANDLERS["engineering_" + name](args, task_id="test"))


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {"HERMES_WORKBENCH_ROOT": str(self.root)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def calc(self, operation="three_phase_current", inputs=None):
        return call("mep_calculate", {"operation": operation, "inputs": inputs if inputs is not None else {"power_W": 10000, "line_voltage_V": 400, "power_factor": 0.8}, "design_basis": "Synthetic fixture, not a real project"})

    def data(self, kind="md"):
        return {"format": kind, "title": "Test report", "sections": [{"heading": "Evidence", "body": "Synthetic test content."}], "sources": ["unit-test fixture"]}

    def test_native_registration(self):
        class Context:
            def __init__(self):
                self.tools, self.skills = [], []
            def register_tool(self, **kwargs):
                self.tools.append(kwargs)
            def register_skill(self, name, path):
                self.skills.append((name, path))
        context = Context()
        module.register(context)
        self.assertEqual(len(context.tools), 6)
        self.assertEqual({n for n, _ in context.skills}, {"software", "office", "mep"})
        self.assertTrue(all(p.is_file() for _, p in context.skills))

    def test_status_does_not_claim_live_integration(self):
        result = call("status", {})["result"]
        self.assertIn("not probed", result["host_connections"])
        self.assertIn("Revit/AutoCAD live adapter", result["not_implemented"])

    def test_all_domain_plans_are_not_executed(self):
        for domain in ("software", "office", "mep"):
            result = call("plan", {"domain": domain, "objective": "Test"})
            self.assertTrue(result["ok"])
            self.assertEqual(result["result"]["status"], "planned_not_executed")

    def test_unknown_domain(self):
        self.assertFalse(call("plan", {"domain": "anything", "objective": "Test"})["ok"])

    def test_unknown_arguments(self):
        self.assertFalse(call("status", {"shell": "echo dangerous"})["ok"])

    def test_nonobject_arguments(self):
        self.assertFalse(call("status", [])["ok"])

    def test_three_phase_golden(self):
        result = self.calc()["result"]
        self.assertAlmostEqual(result["value"], 18.042195912175806)
        self.assertTrue(result["review_required"])
        self.assertFalse(result["standards_verified"])

    def test_airflow_golden(self):
        result = self.calc("sensible_airflow", {"heat_W": 12060, "density_kg_m3": 1.2, "specific_heat_J_kgK": 1005, "delta_T_K": 10})
        self.assertAlmostEqual(result["result"]["value"], 1)

    def test_water_flow_golden(self):
        result = self.calc("water_flow", {"heat_W": 41800, "density_kg_m3": 1000, "specific_heat_J_kgK": 4180, "delta_T_K": 10})
        self.assertAlmostEqual(result["result"]["value"], 0.001)

    def test_velocity_golden(self):
        result = self.calc("circular_velocity", {"flow_m3_s": math.pi / 4, "diameter_m": 1})
        self.assertAlmostEqual(result["result"]["value"], 1)

    def test_pressure_golden(self):
        result = self.calc("darcy_pressure_loss", {"darcy_factor": 0.02, "length_m": 10, "diameter_m": 0.1, "density_kg_m3": 1000, "velocity_m_s": 2})
        self.assertAlmostEqual(result["result"]["value"], 4000)

    def test_invalid_numbers(self):
        for value in [0, -1, True, "400", float("inf"), float("nan")]:
            with self.subTest(value=value):
                self.assertFalse(self.calc(inputs={"power_W": 10000, "line_voltage_V": value, "power_factor": 0.8})["ok"])

    def test_power_factor_limit(self):
        self.assertFalse(self.calc(inputs={"power_W": 10, "line_voltage_V": 400, "power_factor": 1.1})["ok"])

    def test_missing_and_extra_units(self):
        for inputs in [{"power_kW": 10}, {"power_W": 10, "line_voltage_V": 400, "power_factor": 1, "efficiency": 0.8}]:
            self.assertFalse(self.calc(inputs=inputs)["ok"])

    def test_requires_design_basis(self):
        self.assertFalse(call("mep_calculate", {"operation": "circular_velocity", "inputs": {"flow_m3_s": 1, "diameter_m": 1}})["ok"])

    def test_overflow_is_error_not_json_infinity(self):
        self.assertFalse(self.calc("circular_velocity", {"flow_m3_s": 1e308, "diameter_m": 1e-200})["ok"])

    def test_boq_exact_decimal(self):
        row = {"id": "a", "description": "Cable", "unit": "m", "quantity": "0.1", "unit_price": "0.2", "source": "fixture"}
        result = call("boq", {"currency": "VND", "items": [row]})["result"]
        self.assertEqual(result["subtotal"], "0.02")
        self.assertEqual(result["status"], "arithmetic_checked_only")

    def test_boq_duplicate_and_nonfinite(self):
        row = {"id": "a", "description": "Cable", "unit": "m", "quantity": "1", "unit_price": "2", "source": "fixture"}
        self.assertFalse(call("boq", {"currency": "VND", "items": [row, row]})["ok"])
        for value in ["NaN", "Infinity", "-1", True, "0.0000000001", "0E+999999"]:
            self.assertFalse(call("boq", {"currency": "VND", "items": [{**row, "quantity": value}]})["ok"])

    def test_workspace_required(self):
        with patch.dict(os.environ, {"HERMES_WORKBENCH_ROOT": ""}):
            self.assertFalse(call("repo_inspect", {})["ok"])
            self.assertFalse(call("export", self.data())["ok"])

    def test_traversal_and_absolute_rejected(self):
        for path in ["../", "/tmp", "a/../../"]:
            self.assertFalse(call("repo_inspect", {"path": path})["ok"])

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            (self.root / "escape").symlink_to(other, target_is_directory=True)
            self.assertFalse(call("repo_inspect", {"path": "escape"})["ok"])
            (self.root / "artifacts").symlink_to(other, target_is_directory=True)
            self.assertFalse(call("export", self.data())["ok"])
            self.assertEqual(list(Path(other).iterdir()), [])

    def test_static_inventory_does_not_execute(self):
        (self.root / "package.json").write_text('{"scripts":{"test":"do-not-execute"}}')
        result = call("repo_inspect", {})["result"]
        self.assertIn("package.json", result["manifests"])
        self.assertFalse(result["tests_executed"])

    def test_inventory_skips_linked_parent_directories(self):
        with tempfile.TemporaryDirectory() as other:
            (Path(other) / "workflows").mkdir()
            (self.root / ".github").symlink_to(other, target_is_directory=True)
            self.assertNotIn(".github/workflows", call("repo_inspect", {})["result"]["signals"])

    def test_manifest_and_non_overwriting_exports(self):
        a, b = call("export", self.data())["result"], call("export", self.data())["result"]
        self.assertNotEqual(a["path"], b["path"])
        self.assertTrue(Path(a["manifest"]).is_file())
        self.assertEqual(a["visual_review"], "not_performed")
        self.assertFalse(a["sources_verified"])
        self.assertEqual(len(a["sha256"]), 64)

    def test_csv_injection_neutralized(self):
        data = self.data("csv") | {"columns": ["=heading", "Value"], "rows": [["  =HYPERLINK(\"bad\")", 2]]}
        result = call("export", data)["result"]
        content = Path(result["path"]).read_text(encoding="utf-8-sig")
        self.assertIn("'=heading", content)
        self.assertIn("'  =HYPERLINK", content)

    def test_invalid_export_payloads(self):
        for extra in [{"rows": [[1]], "columns": []}, {"sources": []}, {"sections": [{"body": "missing heading"}]}, {"title": "bad\x00title"}]:
            self.assertFalse(call("export", self.data() | extra)["ok"])

    def test_failed_export_cleans_temporary_artifacts(self):
        with patch.object(module.artifacts, "write_file", side_effect=ValueError("synthetic failure")):
            self.assertFalse(call("export", self.data())["ok"])
        self.assertEqual(list((self.root / "artifacts").iterdir()), [])

    def test_installer_dry_run_and_config_preservation(self):
        home = self.root / "profile"
        self.assertEqual(installer.install(home)["action"], "dry_run")
        self.assertFalse(home.exists())
        home.mkdir()
        (home / "config.yaml").write_text("model: private-config\n")
        result = installer.install(home, apply=True)
        self.assertFalse(result["enabled"])
        self.assertEqual((home / "config.yaml").read_text(), "model: private-config\n")
        self.assertTrue((Path(result["destination"]) / "plugin.yaml").is_file())

    def test_installer_upgrade_backup_and_conflict(self):
        home = self.root / "profile"
        first = installer.install(home, apply=True)
        (Path(first["destination"]) / "user.txt").write_text("KEEP")
        with self.assertRaises(ValueError):
            installer.install(home, apply=True)
        result = installer.install(home, apply=True, upgrade=True)
        self.assertEqual((Path(result["backup"]) / "user.txt").read_text(), "KEEP")

    def test_installer_rejects_symlink(self):
        home = self.root / "profile"
        home.mkdir()
        (home / "plugins").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            installer.install(home, apply=True)

    def test_office_optional_formats(self):
        for kind, dependency in [("docx", "docx"), ("xlsx", "openpyxl"), ("pptx", "pptx"), ("pdf", "reportlab")]:
            with self.subTest(kind=kind):
                if importlib.util.find_spec(dependency) is None:
                    self.skipTest(f"Optional {dependency} not installed; dedicated office CI installs all four")
                data = self.data(kind)
                if kind == "xlsx":
                    data |= {"columns": ["Value"], "rows": [["=1+1"], [12345678901234567]]}
                with patch.dict(os.environ, {"HERMES_WORKBENCH_PDF_FONT": ""}):
                    result = call("export", data)
                self.assertTrue(result["ok"], result)
                path = Path(result["result"]["path"])
                self.assertGreater(path.stat().st_size, 100)
                if kind != "pdf":
                    with zipfile.ZipFile(path) as archive:
                        self.assertIsNone(archive.testzip())
                        if kind == "xlsx":
                            xml = archive.read("xl/worksheets/sheet1.xml").decode()
                            self.assertNotIn("<f>", xml)
                            self.assertIn("12345678901234567", xml)

    def test_unicode_pdf_requires_font(self):
        if importlib.util.find_spec("reportlab") is None:
            self.skipTest("Optional reportlab not installed")
        with patch.dict(os.environ, {"HERMES_WORKBENCH_PDF_FONT": ""}):
            self.assertFalse(call("export", self.data("pdf") | {"title": "Kỹ thuật"})["ok"])

    def test_no_silent_pdf_or_pptx_table_loss(self):
        for kind in ("pptx", "pdf"):
            result = call("export", self.data(kind) | {"columns": ["a"], "rows": [[1]]})
            self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
