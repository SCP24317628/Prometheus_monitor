ARG BASE_IMAGE=ubuntu:22.04
FROM quay.io/prometheus/node-exporter:v1.9.1 AS node_exporter
FROM ${BASE_IMAGE}

USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=node_exporter /bin/node_exporter /usr/local/bin/node_exporter
COPY exporters/musa_exporter.py /opt/inference-monitor/musa_exporter.py
COPY exporters/mtdcgm_exporter.py /opt/inference-monitor/mtdcgm_exporter.py
COPY images/node-musa/entrypoint.sh /usr/local/bin/inference-monitor-node
RUN chmod +x /usr/local/bin/node_exporter /usr/local/bin/inference-monitor-node
EXPOSE 9100 9500 9600
ENTRYPOINT ["/usr/local/bin/inference-monitor-node"]
