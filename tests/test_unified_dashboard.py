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
        self.assertIn("Active Requests by Node / Role", timeseries_titles)
        self.assertIn("Queued Requests by Node / Role", timeseries_titles)
        self.assertIn("Token Throughput by Node / Role", timeseries_titles)
        self.assertIn("Generation Throughput & Realtime Tokens by Node / Role", timeseries_titles)
        self.assertIn("TTFT Trend by Node / Role (Mean / P90 / P99)", timeseries_titles)
        self.assertIn("E2E Trend by Node / Role (Mean / P90 / P99)", timeseries_titles)
        self.assertNotIn("Time to First Token", timeseries_titles)
        self.assertNotIn("Per-stage Request Latency p95", timeseries_titles)
        self.assertIn("Prefill Critical Stages p95 by Node", timeseries_titles)
        self.assertIn("Decode Critical Stages p95 by Node", timeseries_titles)
        drilldown = next(p for p in dashboard["panels"] if p.get("title") == "Prefill Drill-down: Bootstrap / Compute / KV Transfer")
        self.assertTrue(drilldown["collapsed"])
        self.assertEqual(len(drilldown["panels"]), 6)
        self.assertEqual(
            {p["title"] for p in drilldown["panels"]},
            {"Bootstrap & Allocation p95 by Node", "Forward & Chunked Prefill p95 by Node",
             "Prompt Length p50 / p95 / p99 by Node", "KV Transfer Latency p50 / p95 by Node",
             "KV Transfer Speed p50 / p95 by Node", "Prefill PD Failures & Retries per Second"},
        )
        by_title = {p.get("title"): p for p in dashboard["panels"]}
        self.assertEqual(by_title["Token Throughput by Node / Role"]["fieldConfig"]["defaults"]["unit"], "suffix: tok/s")
        self.assertEqual(by_title["Generation Throughput & Realtime Tokens by Node / Role"]["fieldConfig"]["defaults"]["unit"], "suffix: tok/s")
        active_exprs = [target["expr"] for target in by_title["Active Requests by Node / Role"]["targets"]]
        self.assertTrue(all("sum by (node,role)" in expr for expr in active_exprs))
        self.assertEqual(by_title["CPU Utilization"]["fieldConfig"]["defaults"]["unit"], "percent")
        self.assertEqual(by_title["CPU Utilization"]["fieldConfig"]["defaults"]["max"], 100)
        self.assertEqual(by_title["Memory Used"]["fieldConfig"]["defaults"]["unit"], "bytes")
        latency_y = by_title["Latency: TTFT & E2E"]["gridPos"]["y"]
        gpu_y = by_title["GPU, CPU & Memory"]["gridPos"]["y"]
        for title in ("Draft Tokens & Accepted Length by Node / Role", "Speculative Acceptance Rate by Node / Role"):
            self.assertGreater(by_title[title]["gridPos"]["y"], latency_y)
            self.assertLess(by_title[title]["gridPos"]["y"], gpu_y)
        self.assertEqual(by_title["Speculative Acceptance Rate by Node / Role"]["fieldConfig"]["defaults"]["unit"], "percentunit")
        self.assertEqual(len(by_title["Draft Tokens & Accepted Length by Node / Role"]["targets"]), 2)
        self.assertEqual(len(by_title["Speculative Acceptance Rate by Node / Role"]["targets"]), 1)
        self.assertIn("prefill_forward|prefill_bootstrap|prefill_transfer_kv_cache",
                      by_title["Prefill Critical Stages p95 by Node"]["targets"][0]["expr"])
        self.assertIn("decode_bootstrap|decode_transferred",
                      by_title["Decode Critical Stages p95 by Node"]["targets"][0]["expr"])
        self.assertFalse({p.get("title") for p in dashboard["panels"] if p.get("type") == "stat"} &
                         {"Running Requests", "Prefill Inflight Requests", "Queued Requests", "Generation Throughput",
                          "TTFT Mean", "TTFT P90", "TTFT P99", "E2E Mean", "E2E P90", "E2E P99"})


if __name__ == "__main__":
    unittest.main()
