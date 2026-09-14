import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "exporters"))
import nvidia_smi_exporter  # noqa: E402


SAMPLE = """0, GPU-test, NVIDIA B300, 00000000:17:00.0, 570.00, 80, 50, 81920, 40960, 40960, 42, 400.5, 700, 1500, 3000
"""


class NvidiaSmiExporterTest(unittest.TestCase):
    def test_collect_maps_csv_to_prometheus(self):
        completed = mock.Mock(stdout=SAMPLE)
        with mock.patch.object(nvidia_smi_exporter.subprocess, "run", return_value=completed):
            output = nvidia_smi_exporter.collect()
        self.assertIn("nvidia_smi_exporter_scrape_success{} 1", output)
        self.assertIn("nvidia_attached_gpus{} 1", output)
        self.assertIn('pci_bus_id="00000000:17:00.0"', output)
        self.assertIn("nvidia_gpu_utilization_ratio", output)
        self.assertIn(" 0.8", output)
        self.assertIn("nvidia_gpu_memory_used_bytes", output)
        self.assertIn("nvidia_gpu_power_watts", output)

    def test_missing_nvidia_smi_is_visible(self):
        with mock.patch.object(nvidia_smi_exporter.subprocess, "run", side_effect=FileNotFoundError):
            output = nvidia_smi_exporter.collect()
        self.assertIn("nvidia_smi_exporter_scrape_success{} 0", output)
        self.assertIn("nvidia_attached_gpus{} 0", output)


if __name__ == "__main__":
    unittest.main()
