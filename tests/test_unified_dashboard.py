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
        self.assertGreaterEqual(len(dashboard["panels"]), 30)
        titles = {panel.get("title", "") for panel in dashboard["panels"]}
        self.assertNotIn("SGLang Performance Summary", titles)
        self.assertIn("SGLang Concurrency & Queue", titles)
        self.assertIn("Latency: TTFT & E2E", titles)
        self.assertIn("KV Cache & PD Transfer", titles)
        self.assertIn("GPU, CPU & Memory", titles)
        self.assertIn("Network: RDMA First", titles)
        self.assertIn("GPU Utilization (Unified)", titles)

        timeseries_titles = {p.get("title") for p in dashboard["panels"] if p.get("type") == "timeseries"}
        self.assertIn("Request Concurrency & Queue", timeseries_titles)
        self.assertIn("Generation Throughput", timeseries_titles)
        self.assertIn("TTFT Trend (Mean / P90 / P99)", timeseries_titles)
        self.assertIn("E2E Trend (Mean / P90 / P99)", timeseries_titles)
        self.assertFalse({p.get("title") for p in dashboard["panels"] if p.get("type") == "stat"} &
                         {"Running Requests", "Prefill Inflight Requests", "Queued Requests", "Generation Throughput",
                          "TTFT Mean", "TTFT P90", "TTFT P99", "E2E Mean", "E2E P90", "E2E P99"})


if __name__ == "__main__":
    unittest.main()
