import copy
import pathlib
import sys
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from render_config import ConfigError, render  # noqa: E402


class RenderConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load((ROOT / "config" / "monitoring.yml").read_text(encoding="utf-8"))

    def test_example_renders_expected_targets(self):
        config = render(copy.deepcopy(self.document))
        jobs = {job["job_name"]: job for job in config["scrape_configs"]}
        self.assertEqual(config["global"]["scrape_interval"], "15s")
        self.assertEqual(len(jobs["node"]["static_configs"]), 2)
        self.assertEqual(len(jobs["musa"]["static_configs"]), 2)
        self.assertEqual(len(jobs["sglang"]["static_configs"]), 1)

    def test_disabled_plugin_is_not_rendered(self):
        document = copy.deepcopy(self.document)
        for node in document["nodes"]:
            node["plugins"]["musa"]["enabled"] = False
        jobs = {job["job_name"] for job in render(document)["scrape_configs"]}
        self.assertNotIn("musa", jobs)

    def test_duplicate_service_target_is_rejected(self):
        document = copy.deepcopy(self.document)
        duplicate = copy.deepcopy(document["services"][0])
        duplicate["name"] = "duplicate"
        document["services"].append(duplicate)
        with self.assertRaisesRegex(ConfigError, "duplicate scrape target"):
            render(document)

    def test_unbounded_label_is_rejected(self):
        document = copy.deepcopy(self.document)
        document["services"][0]["labels"]["request_id"] = "dynamic"
        with self.assertRaisesRegex(ConfigError, "forbidden"):
            render(document)

    def test_dcgm_plugins_are_disabled_by_default(self):
        config = render(copy.deepcopy(self.document))
        jobs = {job["job_name"] for job in config["scrape_configs"]}
        self.assertNotIn("musa_dcgm", jobs)
        self.assertNotIn("nvidia_dcgm", jobs)

    def test_enabled_musa_dcgm_generates_target(self):
        document = copy.deepcopy(self.document)
        document["nodes"][0]["plugins"]["musa_dcgm"]["enabled"] = True
        config = render(document)
        jobs = {job["job_name"]: job for job in config["scrape_configs"]}
        self.assertEqual(jobs["musa_dcgm"]["static_configs"][0]["targets"], ["192.0.2.10:9600"])

    def test_node_envs_follow_dcgm_switches(self):
        import tempfile
        from render_config import render_node_envs
        with tempfile.TemporaryDirectory() as temp:
            output = pathlib.Path(temp)
            render_node_envs(copy.deepcopy(self.document), output)
            content = (output / "node-01.env").read_text(encoding="utf-8")
        self.assertIn("MTDCGM_ENABLED=false", content)
        self.assertIn("NVIDIA_DCGM_ENABLED=false", content)

    def test_rejects_wrong_vendor_dcgm(self):
        document = copy.deepcopy(self.document)
        document["nodes"][0]["plugins"]["nvidia_dcgm"] = {"enabled": True, "port": 9400}
        with self.assertRaisesRegex(ConfigError, "nvidia_dcgm requires"):
            render(document)

    def test_enabled_nvidia_dcgm_generates_target(self):
        document = copy.deepcopy(self.document)
        node = document["nodes"][0]
        node["accelerator_vendor"] = "nvidia"
        node["plugins"]["musa"]["enabled"] = False
        node["plugins"]["nvidia_dcgm"] = {"enabled": True, "port": 9400}
        config = render(document)
        jobs = {job["job_name"]: job for job in config["scrape_configs"]}
        self.assertEqual(jobs["nvidia_dcgm"]["static_configs"][0]["targets"], ["192.0.2.10:9400"])


if __name__ == "__main__":
    unittest.main()
