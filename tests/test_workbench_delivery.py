"""Office content integrity and upgrade regressions, in isolated temporary workspaces."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/engineering-workbench'
spec = importlib.util.spec_from_file_location('delivery_workbench', PLUGIN / '__init__.py', submodule_search_locations=[str(PLUGIN)])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
install_spec = importlib.util.spec_from_file_location('delivery_installer', ROOT / 'install_workbench.py')
installer = importlib.util.module_from_spec(install_spec)
install_spec.loader.exec_module(installer)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        env = patch.dict(os.environ, {'HERMES_WORKBENCH_ROOT': str(self.root)})
        env.start()
        self.addCleanup(env.stop)

    def data(self, kind):
        return {'format': kind, 'title': 'Synthetic', 'sections': [{'heading': '=Literal heading', 'body': 'Important assumptions, không được bỏ sót.'}], 'columns': ['Value'], 'rows': [[1]], 'sources': ['synthetic']}

    def test_csv_preserves_narrative_in_explicit_hashed_supplement(self):
        data = self.data('csv')
        result = module.artifacts.export(data)
        supplement = result['supplemental_files'][0]
        document = json.loads(Path(supplement['path']).read_text())
        self.assertEqual(document['sections'], data['sections'])
        import hashlib
        self.assertEqual(supplement['sha256'], hashlib.sha256(Path(supplement['path']).read_bytes()).hexdigest())
        manifest = json.loads(Path(result['manifest']).read_text())
        self.assertEqual(manifest['supplemental_files'], result['supplemental_files'])

    def test_xlsx_narrative_is_not_silently_dropped_or_a_formula(self):
        if importlib.util.find_spec('openpyxl') is None:
            self.skipTest('Office dependency installed in dedicated CI')
        import openpyxl
        data = self.data('xlsx')
        result = module.artifacts.export(data)
        book = openpyxl.load_workbook(result['path'])
        try:
            self.assertEqual(book['Narrative']['A1'].value, data['sections'][0]['heading'])
            self.assertEqual(book['Narrative']['A1'].data_type, 's')
            self.assertEqual(book['Narrative']['B1'].value, data['sections'][0]['body'])
        finally:
            book.close()

    def test_status_rejects_declared_but_invalid_workspace(self):
        with patch.dict(os.environ, {'HERMES_WORKBENCH_ROOT': str(self.root / 'missing')}):
            result = module.core.capabilities({})
            self.assertTrue(result['workspace_declared'])
            self.assertFalse(result['workspace_configured'])

    def test_lone_surrogate_is_validation_error(self):
        result = json.loads(module.HANDLERS['engineering_export'](self.data('csv') | {'title': '\ud800'}))
        self.assertFalse(result['ok'])
        self.assertEqual(result['type'], 'validation_error')

    def test_staging_is_outside_plugin_discovery_and_rollback_works(self):
        home = self.root / 'profile'
        installed = installer.install(home, apply=True)
        original = Path(installed['destination']) / 'user.txt'
        original.write_text('KEEP')
        real_rename = Path.rename
        def refuse_publish(path, target):
            if path.name == 'plugin' and path.parent.name.startswith('.workbench-stage-'):
                self.assertEqual(path.parent.parent, home)
                raise OSError('synthetic failure')
            return real_rename(path, target)
        with patch.object(Path, 'rename', refuse_publish):
            with self.assertRaises(OSError):
                installer.install(home, apply=True, upgrade=True)
        self.assertEqual(original.read_text(), 'KEEP')
        self.assertEqual(list(home.glob('.workbench-stage-*')), [])
