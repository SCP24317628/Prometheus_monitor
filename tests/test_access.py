import json, pathlib, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
class AccessGeneratorTest(unittest.TestCase):
    def test_generates_final_dashboard_link(self):
        with tempfile.TemporaryDirectory() as temp:
            out = pathlib.Path(temp) / 'access.json'
            subprocess.run([sys.executable, 'tools/generate_access.py', 'config/monitoring.yml', '--output', str(out)], cwd=ROOT, check=True, capture_output=True, text=True)
            data = json.loads(out.read_text(encoding='utf-8'))
        self.assertEqual(data['grafana_dashboard'], 'http://192.0.2.10:3000/d/inference-system-overview/inference-system-overview')
        self.assertNotIn('sglang_dashboard', data)
        self.assertEqual(len(data['services']), 1)
