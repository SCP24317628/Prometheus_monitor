import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class UnifiedDashboardTest(unittest.TestCase):
    def test_only_unified_dashboard_is_provisioned(self):
        dashboards = list((ROOT / "monitoring" / "grafana" / "dashboards").glob("*.json"))
        self.assertEqual([p.name for p in dashboards], ["inference-overview.json"])
        dashboard = json.loads(dashboards[0].read_text(encoding="utf-8"))
        self.assertEqual(dashboard["uid"], "inference-system-overview")
        self.assertGreaterEqual(len(dashboard["panels"]), 40)
        titles = {panel.get("title", "") for panel in dashboard["panels"]}
        self.assertIn("SGLang Performance Summary", titles)
        self.assertIn("Latency Comparison: TTFT and TPOT", titles)
        self.assertIn("PD Disaggregation and KV Transfer", titles)
        self.assertIn("GPU Utilization (MTDCGM)", titles)


if __name__ == "__main__":
    unittest.main()
