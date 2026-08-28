FROM prom/prometheus:v3.5.0 AS prometheus
FROM grafana/grafana:12.1.1

USER root
COPY --from=prometheus /bin/prometheus /usr/local/bin/prometheus
COPY --from=prometheus /bin/promtool /usr/local/bin/promtool
COPY monitoring/grafana /opt/inference-monitor/grafana
COPY images/center/entrypoint.sh /usr/local/bin/inference-monitor-center
RUN mkdir -p /etc/inference-monitor/rules /prometheus /var/lib/grafana/plugins && chmod +x /usr/local/bin/inference-monitor-center
ENV GF_SERVER_HTTP_PORT=3000 \
    GF_AUTH_ANONYMOUS_ENABLED=false \
    GF_USERS_ALLOW_SIGN_UP=false \
    GF_PATHS_PROVISIONING=/opt/inference-monitor/grafana/provisioning \
    GF_PATHS_PLUGINS=/var/lib/grafana/plugins \
    GF_ANALYTICS_CHECK_FOR_UPDATES=false \
    GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false \
    GF_PLUGINS_PREINSTALL_DISABLED=true \
    GF_PLUGINS_PLUGIN_ADMIN_ENABLED=false \
    GF_PLUGINS_PUBLIC_KEY_RETRIEVAL_DISABLED=true
EXPOSE 3000 9090
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD wget -q -T 3 -O /dev/null http://127.0.0.1:9090/-/ready && \
      wget -q -T 3 -O /dev/null http://127.0.0.1:3000/api/health || exit 1
ENTRYPOINT ["/usr/local/bin/inference-monitor-center"]
