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
        self.assertNotIn("SGLang Performance Summary", titles)
        self.assertIn("SGLang Concurrency & Queue", titles)
        self.assertIn("Latency: TTFT & E2E", titles)
        self.assertIn("KV Cache & PD Transfer", titles)
        self.assertIn("GPU, CPU & Memory", titles)
        self.assertIn("Network: RDMA First", titles)
        self.assertIn("GPU Utilization (MTDCGM)", titles)

        stat_titles = {p.get("title") for p in dashboard["panels"] if p.get("type") == "stat"}
        self.assertEqual(
            stat_titles,
            {"Running Requests", "Prefill Inflight Requests", "Queued Requests", "Generation Throughput",
             "TTFT Mean", "TTFT P90", "TTFT P99", "E2E Mean", "E2E P90", "E2E P99"},
        )


if __name__ == "__main__":
    unittest.main()
