# 指标目录

本文区分三种状态：

- **产品接口**：产品支持抓取或转换的指标。
- **当前 MUSA 环境**：77 中心 Prometheus 当前曾采集到的指标系列。
- **运行时数据**：只有 endpoint 可访问且服务正在运行时才会有当前值。

## 1. 采集端口和来源

| 来源 | 端口 | 启用方式 | 说明 |
|---|---:|---|---|
| SGLang Prefill/Decode | 用户填写 | `services` | SGLang 原生 `/metrics`，必须服务正在运行并启用 metrics |
| node_exporter | 9100 | `plugins.node.enabled` | CPU、内存、磁盘、文件系统、网卡、RDMA、内核 |
| MUSA exporter | 9500 | `plugins.musa.enabled` | `mthreads-gmi -q --json`，GPU 基础/性能 |
| MUSA MTDCGM | 9600 | `plugins.musa_dcgm.enabled` | 默认关闭，依赖宿主 MTDCGM/mt-hostengine |
| NVIDIA DCGM | 9400 | `plugins.nvidia_dcgm.enabled` | 默认关闭，依赖 NVIDIA runtime/toolkit |

中心 Prometheus 还记录自身的 `up`、抓取耗时、抓取样本数等 self-monitoring
指标。Router 不在默认 target 中。

## 2. SGLang 指标

SGLang 指标来自用户填写的 Prefill/Decode `/metrics`，产品不会从日志生成这些
指标。下面的后缀规则适用于 histogram：`_bucket` 用于 P50/P90/P99，`_sum` 和
`_count` 用于均值。

### 请求、并发和队列

```text
sglang:num_running_reqs
sglang:num_queue_reqs
sglang:num_prefill_bootstrap_queue_reqs
sglang:num_prefill_inflight_queue_reqs
sglang:num_decode_prealloc_queue_reqs
sglang:num_decode_transfer_queue_reqs
sglang:num_grammar_queue_reqs
sglang:num_paused_reqs
sglang:num_retracted_reqs
sglang:num_unique_running_routing_keys
sglang:routing_keys_active
sglang:routing_key_all_req_count
sglang:routing_key_running_req_count
sglang:http_requests_active
sglang:http_requests_total
sglang:http_responses_total
sglang:num_requests_total
```

### 延迟

```text
sglang:time_to_first_token_seconds_bucket
sglang:time_to_first_token_seconds_count
sglang:time_to_first_token_seconds_sum
sglang:e2e_request_latency_seconds_bucket
sglang:e2e_request_latency_seconds_count
sglang:e2e_request_latency_seconds_sum
sglang:queue_time_seconds_bucket
sglang:queue_time_seconds_count
sglang:queue_time_seconds_sum
sglang:per_stage_req_latency_seconds_bucket
sglang:per_stage_req_latency_seconds_count
sglang:per_stage_req_latency_seconds_sum
```

当前 77/78 使用的 SGLang 版本没有暴露 `inter_token_latency` 系列。因此 TPOT/ITL
不能由当前 exporter 真实计算；不能用吞吐量或日志行数代替。

### 吞吐、Token 和请求长度

```text
sglang:gen_throughput
sglang:prompt_tokens_total
sglang:generation_tokens_total
sglang:realtime_tokens_total
sglang:cached_tokens_total        # 版本支持时
sglang:prompt_tokens_histogram_bucket/count/sum
sglang:generation_tokens_histogram_bucket/count/sum
sglang:uncached_prompt_tokens_histogram_bucket/count/sum
```

### KV Cache、SWA、Mamba 和 PD

```text
sglang:token_usage
sglang:full_token_usage
sglang:kv_available_tokens
sglang:kv_used_tokens
sglang:kv_evictable_tokens
sglang:swa_available_tokens
sglang:swa_used_tokens
sglang:swa_evictable_tokens
sglang:swa_token_usage
sglang:mamba_available_tokens
sglang:mamba_used_tokens
sglang:mamba_evictable_tokens
sglang:mamba_usage
sglang:pending_prealloc_token_usage
sglang:kv_transfer_speed_gb_s_bucket/count/sum
sglang:kv_transfer_latency_ms_bucket/count/sum
sglang:kv_transfer_bootstrap_ms_bucket/count/sum
sglang:kv_transfer_alloc_ms_bucket/count/sum
sglang:kv_transfer_total_mb_bucket/count/sum
sglang:num_bootstrap_failed_reqs_total
sglang:num_transfer_failed_reqs_total
sglang:num_prefill_retries_total
sglang:failed_session_recoveries_total
```

### 调度、容量和运行时

```text
sglang:cache_hit_rate
sglang:utilization
sglang:fwd_occupancy
sglang:new_token_ratio
sglang:max_total_num_tokens
sglang:num_pages
sglang:page_size
sglang:context_len
sglang:decode_sum_seq_lens
sglang:startup_available_gpu_memory_gb
sglang:spec_accept_rate
sglang:spec_accept_length
sglang:spec_num_draft_tokens
sglang:spec_num_steps
sglang:is_cuda_graph
sglang:cuda_graph_passes_total
sglang:engine_startup_time
sglang:engine_load_weights_time
sglang:process_cpu_seconds_total
```

## 3. MUSA exporter 指标（9500）

这些指标由本产品的 `musa_exporter.py` 生成，标签包含 `device`、`uuid`、
`name`、`pci_bus_id`，GPU 信息还包含驱动版本、序列号和性能状态。

```text
musa_exporter_scrape_success
musa_exporter_scrape_duration_seconds
musa_exporter_command_duration_seconds
musa_attached_gpus
musa_gpu_info
musa_gpu_utilization_ratio
musa_gpu_memory_utilization_ratio
musa_gpu_memory_total_bytes
musa_gpu_memory_used_bytes
musa_gpu_memory_free_bytes
musa_gpu_temperature_celsius
musa_gpu_power_watts
musa_gpu_power_limit_watts
musa_gpu_graphics_clock_hertz
musa_gpu_memory_clock_hertz
musa_gpu_thermal_slowdown_total
```

## 4. MUSA MTDCGM 指标（9600，可选）

默认关闭。只有 `musa_dcgm.enabled: true` 且宿主 MTDCGM 正常时才会出现：

```text
musa_dcgm_scrape_success
musa_dcgm_gpu_utilization_ratio       # field 203
musa_dcgm_sm_active_ratio              # field 2002
musa_dcgm_sm_occupancy_ratio           # field 2003
musa_dcgm_dram_active_ratio            # field 2005
musa_dcgm_edc_uncorrectable_total      # field 3100
musa_dcgm_edc_correctable_total        # field 3101
```

## 5. NVIDIA DCGM 指标（9400，可选）

默认关闭，由 NVIDIA 官方 `dcgm-exporter` 提供。产品 recording rule 兼容以下
常用指标并转换为统一 `accelerator_*` 接口：

```text
DCGM_FI_DEV_GPU_UTIL
DCGM_FI_DEV_FB_USED
DCGM_FI_DEV_FB_FREE
DCGM_FI_DEV_GPU_TEMP
DCGM_FI_DEV_POWER_USAGE
```

不同 dcgm-exporter 版本可能提供额外 DCGM 字段；产品不删除原始指标。

## 6. node_exporter 指标（9100）

node exporter 是标准上游组件，当前 `performance` 组启用的主要类别为：

| 类别 | 典型指标 |
|---|---|
| CPU | `node_cpu_seconds_total`、`node_load1/5/15`、CPU 频率/限频 |
| 内存 | `node_memory_MemTotal_bytes`、`MemAvailable`、`MemFree`、Swap、PSI |
| 磁盘/文件系统 | `node_disk_*`、`node_filesystem_*` |
| 以太网 | `node_network_receive_bytes_total`、`transmit_bytes_total`、`node_network_speed_bytes`、carrier/errors/drop |
| RDMA/InfiniBand | `node_infiniband_port_data_received_bytes_total`、`port_data_transmitted_bytes_total`、`node_infiniband_rate_bytes_per_second`、errors/discards/link state |
| 内核/进程 | `node_procs_*`、`node_context_switches_total`、`node_forks_total`、`node_vmstat_*`、pressure |
| 主机信息 | `node_uname_info`、`node_os_info`、`node_exporter_build_info` |

RDMA 当前能直接展示带宽/速率；只有存在可信链路容量指标时才可以计算占用率，
产品不会凭空生成百分比。

## 7. 统一 recording rule 接口

Grafana 优先使用以下稳定名称，以屏蔽 MUSA/NVIDIA 原始指标差异：

```text
accelerator_gpu_utilization_ratio
accelerator_gpu_sm_active_ratio
accelerator_gpu_sm_occupancy_ratio
accelerator_gpu_dram_active_ratio
accelerator_gpu_edc_uncorrectable_total
accelerator_gpu_edc_correctable_total
accelerator_gpu_memory_utilization_ratio
accelerator_gpu_memory_used_bytes
accelerator_gpu_memory_total_bytes
accelerator_gpu_temperature_celsius
accelerator_gpu_power_watts
inference:request_rate_per_second
inference:prompt_tokens_per_second
inference:generation_tokens_per_second
inference:cached_tokens_per_second
```

## 8. 当前环境的真实状态

77 中心最近检查结果：

```text
node exporter：72–78 均有数据
MUSA exporter：72–78 均有数据
MTDCGM：默认关闭，无 musa_dcgm_* 当前样本
SGLang：仅配置 77 Prefill、78 Decode；两项服务停止时无当前样本
Router：未配置为默认 target
```

Grafana 卡片无数据时，先检查对应 `/metrics` endpoint 和 Prometheus target；
看板不会从日志或端口名称猜测指标。
