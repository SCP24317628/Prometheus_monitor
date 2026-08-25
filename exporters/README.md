# Exporters

`musa_exporter.py` converts the stable JSON output of `mthreads-gmi -q --json`
into Prometheus metrics. It intentionally keeps command collection local to the
node and exposes no process arguments or user data.

The exporter provides both vendor-native `musa_*` metrics and enough labels for
the central recording rules to create hardware-neutral `accelerator_*` series.
