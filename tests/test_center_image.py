import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class CenterImageTest(unittest.TestCase):
    def test_entrypoint_is_posix_and_supervises_without_wait_n(self):
        text = (ROOT / "images/center/entrypoint.sh").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/usr/bin/env sh"))
        self.assertNotIn("wait -n", "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#")))
        self.assertIn('trap on_signal INT TERM', text)
        self.assertIn('kill -0 "$prom_pid"', text)
        self.assertIn('kill -0 "$grafana_pid"', text)

    def test_center_requires_explicit_bind_and_disables_anonymous_grafana(self):
        entrypoint = (ROOT / "images/center/entrypoint.sh").read_text(encoding="utf-8")
        dockerfile = (ROOT / "images/center/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("PROMETHEUS_LISTEN_ADDRESS must be explicitly configured", entrypoint)
        self.assertIn("GF_AUTH_ANONYMOUS_ENABLED=false", dockerfile)
        self.assertIn("HEALTHCHECK", dockerfile)


if __name__ == "__main__":
    unittest.main()
