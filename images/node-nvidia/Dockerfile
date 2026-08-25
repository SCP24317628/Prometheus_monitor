FROM quay.io/prometheus/node-exporter:v1.9.1 AS node_exporter
FROM nvcr.io/nvidia/k8s/dcgm-exporter:3.3.8-3.6.0-ubuntu22.04
USER root
COPY --from=node_exporter /bin/node_exporter /usr/local/bin/node_exporter
COPY images/node-nvidia/entrypoint.sh /usr/local/bin/inference-monitor-node
RUN chmod +x /usr/local/bin/node_exporter /usr/local/bin/inference-monitor-node
ENV NVIDIA_DCGM_ENABLED=false NODE_EXPORTER_PORT=9100 NVIDIA_DCGM_PORT=9400
EXPOSE 9100 9400
ENTRYPOINT ["/usr/local/bin/inference-monitor-node"]
