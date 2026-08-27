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
        self.assertIn("TTFT Trend by Node / Role (Mean / P90 / P99)", timeseries_titles)
        self.assertIn("E2E Trend by Node / Role (Mean / P90 / P99)", timeseries_titles)
        self.assertNotIn("Time to First Token", timeseries_titles)
        by_title = {p.get("title"): p for p in dashboard["panels"]}
        self.assertEqual(by_title["CPU Utilization"]["fieldConfig"]["defaults"]["unit"], "percent")
        self.assertEqual(by_title["CPU Utilization"]["fieldConfig"]["defaults"]["max"], 100)
        self.assertEqual(by_title["Memory Used"]["fieldConfig"]["defaults"]["unit"], "bytes")
        latency_y = by_title["Latency: TTFT & E2E"]["gridPos"]["y"]
        gpu_y = by_title["GPU, CPU & Memory"]["gridPos"]["y"]
        self.assertGreater(by_title["Speculative Decode Acceptance"]["gridPos"]["y"], latency_y)
        self.assertLess(by_title["Speculative Decode Acceptance"]["gridPos"]["y"], gpu_y)
        self.assertFalse({p.get("title") for p in dashboard["panels"] if p.get("type") == "stat"} &
                         {"Running Requests", "Prefill Inflight Requests", "Queued Requests", "Generation Throughput",
                          "TTFT Mean", "TTFT P90", "TTFT P99", "E2E Mean", "E2E P90", "E2E P99"})


if __name__ == "__main__":
    unittest.main()
