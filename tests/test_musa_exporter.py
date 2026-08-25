import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "exporters"))

import musa_exporter  # noqa: E402


SAMPLE = {
    "Driver Version": "3.3.5-server",
    "GPU": [
        {
            "Index": "0",
            "Product Name": "MTT S5000",
            "GPU UUID": "test-uuid",
            "Serial Number": "test-serial",
            "Performance State": "P0",
            "PCI": {"PCI/Bus ID": "00000000:2a:00.0"},
            "FB Memory Usage": {"Total": "81920MiB", "Used": "40960MiB", "Free": "40960MiB"},
            "Utilization": {"Gpu": "75%", "Memory": "50%"},
            "Temperature": {"GPU Current Temp": "42C"},
            "Power Readings": {"Power Draw ": "400.5W", "Current Power Limit": "950W"},
            "Clocks": {"Graphics": "1750MHz", "Memory": "2500MHz"},
            "Thermal Slowdown Stats": {"Count": "0"},
        }
    ],
}


class MusaExporterTest(unittest.TestCase):
    def test_collect_maps_json_to_prometheus(self):
        with mock.patch.object(musa_exporter, "_query", return_value=(SAMPLE, 0.01)):
            output = musa_exporter.collect()
        self.assertIn("musa_exporter_scrape_success{} 1", output)
        self.assertIn("musa_attached_gpus{} 1", output)
        self.assertIn('pci_bus_id="00000000:2a:00.0"', output)
        self.assertIn("musa_gpu_utilization_ratio", output)
        self.assertIn(" 0.75", output)
        self.assertIn("musa_gpu_memory_used_bytes", output)
        self.assertIn("musa_gpu_power_watts", output)

    def test_collection_failure_is_exposed(self):
        with mock.patch.object(musa_exporter, "_query", side_effect=RuntimeError("failed")):
            output = musa_exporter.collect()
        self.assertIn("musa_exporter_scrape_success{} 0", output)
        self.assertIn("musa_attached_gpus{} 0", output)


if __name__ == "__main__":
    unittest.main()
