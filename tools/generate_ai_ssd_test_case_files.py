"""Generate one executable test_*.py file per AI SSD case in the core plan."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ai_ssd_test_cases"


def _steps(category: str, config: str, metrics: str) -> list[str]:
    templates = {
        "base": [
            f"确认 DUT、数据盘和结果盘映射，记录 {config}。",
            "采集测试前容量、健康状态和 Windows PhysicalDisk 基线。",
            "按本 Case 的路径或填充率条件运行，重复记录实际读写。",
            f"对照 {metrics}，确认路径、容量和性能变化可解释。",
        ],
        "training": [
            f"准备 {config} 对应的训练数据，数据盘与结果盘分离。",
            "固定 seed 和 worker/accelerator 配置，完成不计分预热。",
            "使用对应 test_training_*.py 运行重复测试并保存每次结果。",
            f"对齐 AU、{metrics}、PhysicalDisk 队列和温度，检查后半程退化。",
        ],
        "checkpoint": [
            f"准备 {config} 对应的 checkpoint 分片和容量余量。",
            "按固定 rank/分片布局执行带 fsync 的写入，并记录最慢 rank。",
            "清理或重启后执行恢复读取；无法证明 cold 时标记 warm-only。",
            f"校验 10 次保存/读取、完整性、{metrics} 和恢复时间。",
        ],
        "kv": [
            f"准备 {config} 的 KV Cache tier、模型和用户/上下文配置。",
            "固定随机种子，先完成 warm-up，再按用户或 context 阶梯运行。",
            "记录 NVMe tier entries、读写字节、tokens/s 和各分位尾延迟。",
            f"对照 {metrics}，确认没有 OOM、丢请求或缓存目录落错盘。",
        ],
        "vdb": [
            f"准备 {config} 的向量、索引和固定 planted query。",
            "先完成建库/加载，再按 Case 变量执行查询或后台写入。",
            "记录 Recall、QPS、P99、实际读写、容量和温度。",
            f"在相同 Recall 门槛下比较 {metrics}，确认结果可复现。",
        ],
        "mixed": [
            f"分别完成前台和后台 {config} 的单项基线。",
            "同时启动前台/后台负载，固定到达节奏并记录 UTC 时间线。",
            "重复运行并采集前台尾延迟、后台吞吐、队列和错误。",
            f"对照单项基线，判断 {metrics} 是否满足通过门槛。",
        ],
    }
    return templates[category]


def _case(category: str, case_id: str, name: str, config: str, purpose: str, metrics: str, duration: str, standard: str, *, mode: str | None = None, shards: int | None = None, users: int | None = None, dimensions: int | None = None) -> dict[str, object]:
    filename = f"test_{category}_{name}.py"
    spec: dict[str, object] = {
        "case_id": case_id,
        "category": category,
        "case_name": name,
        "config": config,
        "purpose": purpose,
        "steps": _steps(category, config, metrics),
        "test_duration": duration,
        "command": f"python ai_ssd_test_cases/{filename} --execute --data-dir <DUT_DATA> --result-dir <RESULTS>",
        "standard": standard,
        "metrics": metrics,
        "mode": mode or category,
    }
    if shards is not None:
        spec["shards"] = shards
    if users is not None:
        spec["users"] = users
    if dimensions is not None:
        spec["dimensions"] = dimensions
    return spec


CASES: list[dict[str, object]] = []


def add(*args: object, **kwargs: object) -> None:
    CASES.append(_case(*args, **kwargs))  # type: ignore[arg-type]


# BASE (4)
add("base", "AI-BASE-001", "dut_path_capacity", "S0 / 4 块盘 / 卷映射", "建立 DUT、数据盘和结果盘的可追踪基线。", "路径映射、容量、健康状态", "约 20–30 分钟", "PASS：DUT、data、result 路径映射正确；结果目录不在 DUT；容量和序列号可追溯。")
add("base", "AI-BASE-002", "cache_path_modes", "Q1 / Buffered、cold、Direct", "区分缓冲、冷缓存和直接访问对结果的影响。", "PhysicalDisk 实际读字节、吞吐、P99", "约 45–60 分钟", "PASS：三种路径独立完成；cold/direct 的实际读字节可解释；不混报 warm-only 结果。")
add("base", "AI-BASE-003", "repeatability_monitor_overhead", "Q1 / 3 runs / monitor off-on", "验证重复性并量化监控开销。", "吞吐 CV、监控前后差异", "约 45–60 分钟", "PASS：3 次吞吐 CV≤5%；监控开销≤2%；日志和时间覆盖完整。")
add("base", "AI-BASE-004", "fill_level_degradation", "Q1/X / 20、50、80、90% fill", "观察 SSD 填充率升高后的性能退化曲线。", "吞吐、IOPS、P99、队列", "约 2–4 小时", "PASS：输出各填充率结果；不得覆盖未授权目录；退化趋势和瓶颈可解释。")

# TRAINING (16)
add("training", "AI-TRN-001", "unet3d_a100_baseline", "UNet3D/A100 NPZ，accelerator 1/2/4", "建立大文件训练数据的连续供给基线。", "samples/s、GiB/s、AU、P99", "约 45–60 分钟", "PASS：AU≥90%；3 次吞吐 CV≤5%；PhysicalDisk 实际读字节可解释；无数据错误。", mode="sequential")
add("training", "AI-TRN-002", "unet3d_h100_compute_gap", "UNet3D/H100 NPZ，accelerator 1/2/4", "验证 compute gap 缩短后的供数稳定性。", "AU、吞吐、queue、P99", "约 45–60 分钟", "PASS：AU≥90%；吞吐无持续下降；队列不持续增长；无供数中断。", mode="sequential")
add("training", "AI-TRN-003", "unet3d_b200_large_read", "UNet3D/B200 NPZ，accelerator 1/2/4/8", "验证大规模 NPZ 数据长时间连续读取。", "AU、samples/s、GiB/s、后半程漂移", "约 60–90 分钟", "PASS：AU≥90%；后半程吞吐下降≤10%；温度、队列和数据完整性正常。", mode="sequential")
add("training", "AI-TRN-004", "retinanet_b200_small_files", "RetinaNet/B200 JPEG，accelerator 1/4/8/16", "验证百万级 JPEG 小文件的元数据和 IOPS 能力。", "files/s、IOPS、P99、AU", "约 45–60 分钟", "PASS：AU≥85%；files/s 达标；P99 无异常尖峰；无缺文件。", mode="small_file")
add("training", "AI-TRN-005", "retinanet_mi355_batch_pressure", "RetinaNet/MI355 JPEG，batch/compute sweep", "验证 batch 和处理节奏变化下的小文件供给稳定性。", "files/s、P99、等待时间、AU", "约 45–60 分钟", "PASS：AU≥85%；不同 batch 结果可重复；files/s 无持续下降。", mode="small_file")
add("training", "AI-TRN-006", "cosmoflow_a100_shuffle", "CosmoFlow/A100 TFRecord，accelerator 1/2/4", "验证中小对象随机访问和 shuffle 供数。", "IOPS、P99、queue、AU", "约 60–90 分钟", "PASS：AU≥70%；shuffle 无供数空洞；IOPS/P99 达标；数据完整。", mode="shuffle")
add("training", "AI-TRN-007", "cosmoflow_h100_high_rate", "CosmoFlow/H100 TFRecord，accelerator 1/2/4/8", "验证更高请求速率下的随机读取尾延迟。", "P99、IOPS、queue、AU", "约 60–90 分钟", "PASS：AU≥70%；P99 达标；请求速率提高后无供数中断。", mode="shuffle")
add("training", "AI-TRN-008", "resnet50_a100_tfrecord_samples", "ResNet50/A100 TFRecord，固定 batch/threads", "验证 TFRecord 文件内多 sample 读取效率。", "samples/s、吞吐、P99、AU", "约 45–60 分钟", "PASS：AU≥90%；samples/s 达标；batch 结果稳定；无读取错误。", mode="record")
add("training", "AI-TRN-009", "resnet50_h100_tfrecord_rate", "ResNet50/H100 TFRecord，accelerator 1/2/4/8", "验证更高 TFRecord 供给速率下的持续吞吐。", "throughput、P99、queue、AU", "约 60–90 分钟", "PASS：AU≥90%；throughput 无持续下降；无供数中断。", mode="record")
add("training", "AI-TRN-010", "dlrm_b200_parquet_columns", "DLRM/B200 Parquet，prefetch 0/2/4", "验证 Parquet 行组和列裁剪读取表现。", "row-groups/s、带宽、P99、AU", "约 60–90 分钟", "PASS：AU≥70%；row-groups/s 达标；无异常读放大；CPU 不成为主瓶颈。", mode="columnar", dimensions=128)
add("training", "AI-TRN-011", "dlrm_mi355_parquet_parallel", "DLRM/MI355 Parquet，threads 1/4/8/16", "验证 Parquet 并行读取带宽和主机开销。", "read BW、CPU、P99、AU", "约 60–90 分钟", "PASS：AU 达标；read BW 随线程变化可解释；CPU、队列和 P99 无异常。", mode="columnar", dimensions=128)
add("training", "AI-TRN-012", "flux_b200_parquet_large_object", "Flux/B200 Parquet，threads 4/8/16", "验证大 Parquet 对象的持续读取带宽。", "GiB/s、P99、温度、AU", "约 90–120 分钟", "PASS：AU≥90%；GiB/s 达标；吞吐无持续下降；空间余量安全。", mode="sequential")
add("training", "AI-TRN-013", "flux_mi355_burst_read", "Flux/MI355 Parquet，batch 72，threads sweep", "验证长 compute gap 后突发读取的恢复能力。", "burst latency、恢复时间、AU", "约 90–120 分钟", "PASS：AU≥90%；突发读取在目标窗口内恢复；无供数中断。", mode="burst")
add("training", "AI-TRN-014", "concurrent_accelerator_scaling", "UNet3D/RetinaNet，workers 1/2/4/8/16", "定位并发增加后的最大合格供数能力。", "AU、speedup、吞吐、P99、queue", "约 90–120 分钟", "PASS：输出最大合格并发；AU 达标；speedup 可解释；饱和拐点明确。", mode="saturation")
add("training", "AI-TRN-015", "reader_thread_scaling", "固定训练数据，read_threads 1/2/4/8/16/32", "定位读取线程增加后的 SSD/CPU 饱和拐点。", "throughput、CPU、queue、P99", "约 60–90 分钟", "PASS：饱和拐点可复现；吞吐 CV≤5%；瓶颈可归因；无持续错误。", mode="saturation")
add("training", "AI-TRN-016", "cache_path_matrix", "warm/cold/--o-direct", "量化缓存污染对训练结果的影响。", "PhysicalDisk 实际读字节、吞吐、AU、P99", "约 45–60 分钟", "PASS：三种路径独立可复现；cold/direct 实际读字节与逻辑量一致；AU 差异可解释。", mode="cache_matrix")

# CHECKPOINT (9)
add("checkpoint", "AI-CKP-001", "8b_full_baseline", "8B full，8 ranks，105 GB/checkpoint", "建立单节点 8B checkpoint 写入和恢复基线。", "10 save/load、fsync、cold read", "约 60–90 分钟", "PASS：10 次保存和读取完成；所有分片完整；fsync 成功；最慢 rank 可追溯。", shards=8)
add("checkpoint", "AI-CKP-002", "70b_subset", "70B subset，8 ranks，114 GB/checkpoint", "验证单盘模拟 70B 分片的写入和恢复。", "最慢 rank、最小吞吐、hash", "约 60–90 分钟", "PASS：每个 rank 完成；字节数符合配置；hash 一致；无空间或写入错误。", shards=8)
add("checkpoint", "AI-CKP-003", "70b_full_distributed", "70B full，64 ranks，912 GB/checkpoint", "验证多节点并发写入和恢复的 rank skew。", "rank skew、global duration、吞吐", "约 2–4 小时", "PASS：所有 rank 完成；global duration 和 skew 可解释；无丢分片或损坏。", shards=64)
add("checkpoint", "AI-CKP-004", "405b_subset", "405B subset，8 ranks，94 GB/checkpoint", "验证大模型 node-local SSD 的 checkpoint 行为。", "save/load、cold bytes、恢复时间", "约 60–90 分钟", "PASS：写入、读取和完整性检查通过；容量余量保持安全；冷读方法有记录。", shards=8)
add("checkpoint", "AI-CKP-005", "405b_full_shared", "405B full，512 ranks，5.29 TB/checkpoint", "验证 TB 级 shared storage 的并发 checkpoint 扩展。", "scale、最慢 rank、global duration", "约 4–8 小时", "PASS：512 ranks 均完成；无丢分片；skew、吞吐和容量变化可解释。", shards=512)
add("checkpoint", "AI-CKP-006", "1t_subset", "1T subset，8 ranks，161 GB/checkpoint", "验证最大单节点分片的突发写入和恢复。", "burst、GC、恢复时间", "约 90–120 分钟", "PASS：突发写入完成；fsync 和 hash 通过；恢复时间达到目标；无持续 GC 异常。", shards=8)
add("checkpoint", "AI-CKP-007", "1t_full_distributed", "1T full，1024 ranks，18 TB/checkpoint", "验证极大模型 checkpoint 的全局保存和恢复。", "global save/load、rank skew", "约 8–12 小时", "PASS：1024 ranks 全部完成；global save/load 可重跑；无损坏、缺 rank 或容量越界。", shards=1024)
add("checkpoint", "AI-CKP-008", "cold_warm_recovery", "write-only→purge/reboot→read-only", "证明恢复读实际命中 SSD，而不是页缓存。", "PhysicalDisk bytes、load time、hash", "约 90–120 分钟", "PASS：cold 方法明确；实际物理读字节与逻辑量一致；warm/cold 结果分开报告。", shards=8)
add("checkpoint", "AI-CKP-009", "interval_burst_gc", "interval 5/30/300 s，1/2/10 cycles", "评价连续 checkpoint 和后台 GC 对后续保存的影响。", "后续 checkpoint 退化、P99、GC", "约 2–4 小时", "PASS：所有 cycle 完成；后续 checkpoint 退化可量化；无持续超过目标的尾延迟。", shards=8)

# KV CACHE (22)
add("kv", "AI-KV-001", "option1_8b_nvme_only", "MLPerf option 1，8B，200 users，CPU/GPU=0", "验证 8B NVMe-only 高并发 KV Cache。", "worst P95、tokens/s、tier bytes", "约 60–90 分钟", "PASS：storage_entries>0；所有 trial 完成；worst P95 和 tokens/s 达到对应 SLA；NVMe tier 有实际 I/O。", users=200)
add("kv", "AI-KV-002", "option2_cpu_spill", "MLPerf option 2，4 GB CPU spill，100 users", "验证 CPU spill 边界和 NVMe tier 仍有实际负载。", "spill 时刻、P95、evictions、tier bytes", "约 60–90 分钟", "PASS：spill 行为可观察；NVMe tier entries>0；无 OOM；P95 达到 SLA。", users=100)
add("kv", "AI-KV-003", "option3_70b", "MLPerf option 3，70B，70 users，allocs=4", "验证大模型 KV 对象下的带宽、尾延迟和 RAM 峰值。", "P95、BW、RAM 峰值、tier bytes", "约 90–120 分钟", "PASS：所有 trial 完成；tier I/O 可证；RAM 无越界；P95 和 BW 达到 SLA。", users=70)
add("kv", "AI-KV-004", "tiny1b_smoke", "tiny-1b，users 10→500", "用小模型快速验证 KV Cache 的小对象 IOPS。", "IOPS、P99、entries", "约 30–45 分钟", "PASS：用户阶梯可重跑；entries>0；P99 无异常尖峰；无丢请求。", users=100)
add("kv", "AI-KV-005", "mistral7b_gqa", "mistral-7b，128 KiB/token GQA", "验证 GQA KV 对象大小对尾延迟和带宽的影响。", "tail latency、BW、tokens/s", "约 60–90 分钟", "PASS：context/users sweep 完整；P99 达到 SLA；带宽变化与对象大小一致。", users=50)
add("kv", "AI-KV-006", "llama2_7b_upper_bound", "llama2-7b，512 KiB/token，alloc 1/2/4/8", "验证较大 KV/token 下的 P99.9 和 OOM 边界。", "P99.9、OOM guard、tier bytes", "约 60–90 分钟", "PASS：各 alloc 点结果完整；OOM guard 正常；无 silent eviction 或目录误写。", users=50)
add("kv", "AI-KV-007", "llama31_8b_users", "llama3.1-8b，users 25/50/100/200", "绘制 8B 独立负载的最大合格用户曲线。", "max compliant users、P99.99、tokens/s", "约 90–120 分钟", "PASS：最大合格用户明确；Interactive SLA 全部满足；无 tier I/O 缺失。", users=100)
add("kv", "AI-KV-008", "llama31_70b_users", "llama3.1-70b，users 10/35/70/140", "绘制大模型独立负载的最大合格用户曲线。", "max compliant users、P99.99、BW", "约 90–120 分钟", "PASS：用户阶梯完整；最大合格点可复现；P99.99 和 BW 达标。", users=70)
add("kv", "AI-KV-009", "deepseek_v3_mla", "deepseek-v3，context 4K/8K/25K，MLA", "验证 MLA 压缩 KV 对小对象效率的影响。", "对象大小、bytes/token、P99", "约 60–90 分钟", "PASS：三档 context 完成；对象大小和 bytes/token 可解释；尾延迟满足 SLA。", users=35)
add("kv", "AI-KV-010", "qwen3_32b_sweep", "qwen3-32b，256 KiB/token", "验证 32B KV 对象在用户和上下文变化下的供给。", "P99、BW、tokens/s", "约 60–90 分钟", "PASS：context/users sweep 完整；P99 和 BW 达到目标；无丢请求。", users=50)
add("kv", "AI-KV-011", "gpt_oss_20b_moe", "gpt-oss-20b，MoE 小 KV，高 users", "验证 MoE 小 KV 在高并发下的 IOPS 和 CPU 开销。", "IOPS、CPU overhead、P99", "约 60–90 分钟", "PASS：高用户点可完成；CPU 开销可归因；IOPS 和 P99 达标。", users=100)
add("kv", "AI-KV-012", "gpt_oss_120b", "gpt-oss-120b，大模型低 KV/token", "验证大模型低 KV/token 配置的吞吐和尾延迟。", "throughput、P99、RAM、tier bytes", "约 90–120 分钟", "PASS：users/context sweep 完整；throughput 和 P99 达标；tier I/O 可证。", users=50)
add("kv", "AI-KV-013", "tier_capacity_matrix", "GPU/CPU=0/4/16/32 GiB", "定位 GPU/CPU tier 变化下的 offload 拐点。", "tier occupancy、spill latency、P99", "约 90–120 分钟", "PASS：每个 tier 点完成；spill 拐点可定位；无 OOM 或缓存目录误写。", users=50)
add("kv", "AI-KV-014", "tensor_parallel_matrix", "TP 1/2/4/8，num_gpus≥TP", "量化 TP 变化对 per-rank shard 对象和聚合带宽的影响。", "per-rank bytes、aggregate BW、P99", "约 90–120 分钟", "PASS：各 TP 点 rank 对齐；bytes 和 BW 可解释；尾延迟满足 SLA。", users=50)
add("kv", "AI-KV-015", "prefill_write", "Prefill-only，model/users/context sweep", "验证 disaggregated prefill 的写密集 KV 行为。", "write BW、fsync、P99", "约 60–90 分钟", "PASS：写入字节完整；fsync 成功；write BW 和 P99 达到目标。", users=50)
add("kv", "AI-KV-016", "decode_read", "Decode-only，预置 cache，model/users", "验证 disaggregated decode 的读密集 KV 行为。", "read BW、P99.99、tokens/s", "约 60–90 分钟", "PASS：预置 cache 可复用；实际读字节可证；P99.99 和 tokens/s 达标。", users=50)
add("kv", "AI-KV-017", "context_personas", "chatbot/coding/document 短/长上下文", "比较不同上下文 persona 的对象分布和尾延迟。", "object CDF、P99、tier bytes", "约 90–120 分钟", "PASS：三类 persona 结果完整；object CDF 和尾延迟可解释；无丢请求。", users=50)
add("kv", "AI-KV-018", "generation_modes", "none/fast/realistic generation", "区分峰值生成节奏与真实生成节奏下的资源占用。", "wall/active BW、SLA、P99", "约 60–90 分钟", "PASS：三种节奏可区分；wall/active BW 均有记录；SLA 判定不混淆。", users=50)
add("kv", "AI-KV-019", "rag_prefix_multiturn", "RAG/prefix/multi-turn，docs 10/100", "验证 KV 复用和额外文档 I/O 的收益与代价。", "hit rate、bytes saved、P99、docs I/O", "约 90–120 分钟", "PASS：开关和 docs 阶梯完整；hit rate 与 bytes saved 可解释；P99 达标。", users=50)
add("kv", "AI-KV-020", "saturation_autoscale", "users/request-rate 逐步增加 20/25%", "定位最大合格负载、队列拐点和恢复时间。", "knee、queue、recovery、P99", "约 90–120 分钟", "PASS：最大合格点明确；超过拐点能恢复；无持续丢请求或队列失控。", users=100)
add("kv", "AI-KV-021", "tier2_trace_replay", "Tier-2 trace，1×/2×/4×，Windows Direct I/O", "在 Windows Direct I/O 下复现过滤后的 Tier-2 访问。", "P50/P95/P99、aligned BW、实际读字节", "约 90–120 分钟", "PASS：trace 过滤范围可追溯；三种速率完成；aligned BW 和尾延迟可复现。", users=50)
add("kv", "AI-KV-022", "burstgpt_sharegpt", "BurstGPT/ShareGPT arrival/context trace", "验证真实 arrival 和 context 分布下的突发尾延迟。", "burst tail、queue、drop、tokens/s", "约 2–4 小时", "PASS：外部数据集版本和 trace speed 固定；无异常 drop；突发尾延迟可解释。", users=50)

# VECTOR DB (16)
add("vdb", "AI-VDB-001", "hnsw_1k_smoke", "1K×128 HNSW，planted query，L2", "完成 Windows smoke 并验证 trace 完整性。", "Recall、QPS、trace 完整性", "约 20–30 分钟", "PASS：Recall 达标；QPS 可记录；trace、索引和结果文件完整。", dimensions=128)
add("vdb", "AI-VDB-002", "hnsw_1m", "1M×1536 HNSW，M64，ef 32/128/256", "建立内存图索引的 Recall-QPS-P99 基线。", "Recall、QPS、P99、容量", "约 2–4 小时", "PASS：同一 Recall 门槛下比较；ef 阶梯完整；P99 和容量可追溯。", dimensions=1536)
add("vdb", "AI-VDB-003", "diskann_1m_1536", "1M×1536 DISKANN，degree64", "建立磁盘 ANN 的搜索和实际读基线。", "Recall、QPS、physical read、P99", "约 2–4 小时", "PASS：Recall 达标；physical read 命中 DUT；QPS/P99 可重跑。", dimensions=1536)
add("vdb", "AI-VDB-004", "diskann_1m_512", "1M×512 DISKANN，和 1536 维对照", "量化向量维度变化对查询字节和 QPS 的影响。", "bytes/query、QPS、Recall", "约 90–120 分钟", "PASS：两种维度同 Recall 门槛；bytes/query 变化可解释；无索引错配。", dimensions=512)
add("vdb", "AI-VDB-005", "aisaq_1m_512", "1M×512 AISAQ，inline_pq 16/32", "验证压缩索引的容量、Recall 和 QPS 权衡。", "capacity、Recall、QPS、P99", "约 90–120 分钟", "PASS：PQ 16/32 结果完整；Recall 达标；容量收益和性能代价可解释。", dimensions=512)
add("vdb", "AI-VDB-006", "hnsw_10m", "10M×1536 HNSW，10 shards，query proc 1/4/8", "验证大数据集 HNSW 的加载、扩展和 P99。", "scale、load time、P99、QPS", "约 4–8 小时", "PASS：10 shards 可加载；query proc 变化可解释；无容器重启或数据缺失。", dimensions=1536)
add("vdb", "AI-VDB-007", "diskann_10m", "10M×1536 DISKANN，10 shards", "验证大磁盘型索引的 QPS、物理 I/O 和温度。", "QPS、physical IO、temperature、Recall", "约 4–8 小时", "PASS：Recall 达标；physical IO 命中 DUT；温度和空间余量安全。", dimensions=1536)
add("vdb", "AI-VDB-008", "index_family_sweep", "DISKANN/HNSW/AISAQ/IVF/FLAT 六类 index", "在相同 Recall 门槛下比较索引家族。", "Recall、QPS、容量、P99", "约 4–8 小时", "PASS：所有支持的 index 均记录版本；同 Recall 下比较；不支持项明确标注。", dimensions=128)
add("vdb", "AI-VDB-009", "search_effort_sweep", "ef/search-list 32→512", "绘制搜索努力度与精度、性能的关系。", "Recall、QPS、P99、search effort", "约 90–120 分钟", "PASS：参数阶梯完整；Recall 单调性和 QPS/P99 变化可解释。", dimensions=128)
add("vdb", "AI-VDB-010", "query_process_scaling", "query process 1/2/4/8/16", "定位查询并发的饱和点和队列拐点。", "aggregate QPS、queue、P99、CPU", "约 90–120 分钟", "PASS：最大合格进程数明确；队列拐点可定位；Recall 不下降。", dimensions=128)
add("vdb", "AI-VDB-011", "search_batch_scaling", "batch 1/8/32/64", "验证批查询对 QPS 和单查询尾延迟的影响。", "QPS、per-query P99、Recall", "约 60–90 分钟", "PASS：四档 batch 完成；per-query P99 不被 aggregate QPS 掩盖；Recall 达标。", dimensions=128)
add("vdb", "AI-VDB-012", "ingest_tuning", "batch 1K/10K，compact on/off", "验证写入批次和 compact 对建索引效率的影响。", "vectors/s、flush/index time、写放大", "约 90–120 分钟", "PASS：四种组合结果完整；无丢向量；flush/index 时间和写放大可解释。", dimensions=128)
add("vdb", "AI-VDB-013", "topk_metric_dimension", "K10/100；COSINE/L2/IP；多维度", "验证查询形状对 Recall、结果字节和延迟的影响。", "Recall、result bytes、latency、QPS", "约 90–120 分钟", "PASS：K、metric、dimension 组合完整；Recall 计算口径一致；结果字节可解释。", dimensions=128)
add("vdb", "AI-VDB-014", "cold_warm_search", "restart/load、重复 round、search-only", "区分索引加载、缓存和 steady-state 搜索影响。", "load time、first P99、steady P99、physical read", "约 90–120 分钟", "PASS：cold/warm/search-only 分开；first/steady 结果可重跑；physical read 证据完整。", dimensions=128)
add("vdb", "AI-VDB-015", "logical_trace_replay", "both/search-only，1×/2×/4×", "复现 VectorDB 逻辑 SSD 负载并验证对齐带宽。", "aligned BW、P99、trace 覆盖", "约 90–120 分钟", "PASS：trace 版本和过滤范围固定；三种速率完成；aligned BW/P99 可比较。", dimensions=128)
add("vdb", "AI-VDB-016", "ingest_search_coexist", "独立 ingest/query clients", "评价后台写入和建索引对前台搜索的影响。", "Recall、foreground P99、ingest rate", "约 2–4 小时", "PASS：前台 Recall 不降；P99 满足 SLA；后台 ingest rate 和影响可量化。", dimensions=128)

# MIXED (5)
add("mixed", "AI-MIX-001", "training_checkpoint", "前台 Training，后台 Checkpoint save", "验证持续读与突发写同盘时的训练和保存窗口。", "AU、checkpoint throughput、foreground P99", "约 90–120 分钟", "PASS：AU 达标；checkpoint throughput≥solo 的 0.8×；无数据或分片错误。")
add("mixed", "AI-MIX-002", "kv_decode_checkpoint", "前台 KV decode，后台 Checkpoint save", "验证 LLM 推理尾延迟对大写入的抗干扰能力。", "KV P99、tokens/s、checkpoint throughput", "约 90–120 分钟", "PASS：KV P99≤1.5×solo 且满足 SLA；checkpoint 写入完整；无丢请求。", users=50)
add("mixed", "AI-MIX-003", "vdb_search_ingest", "前台 VectorDB search，后台 ingest/index", "验证 RAG 在线查询对后台建库的容忍度。", "Recall、foreground P99、ingest rate", "约 90–120 分钟", "PASS：Recall 不降；前台 P99≤1.5×solo 且满足 SLA；后台 ingest 可完成。", dimensions=128)
add("mixed", "AI-MIX-004", "kv_interactive_vdb_search", "前台 KV interactive + VectorDB search", "验证两类前台随机读共存时的双 SLA。", "KV P99、VDB P99、Recall、QPS", "约 90–120 分钟", "PASS：两类前台 workload 的 SLA 均达标；Recall 不降；无持续队列堆积。", users=50, dimensions=128)
add("mixed", "AI-MIX-005", "four_class_soak", "4 类循环，fill/GC background，8 小时", "验证长时间混合 AI SSD 稳定性和持续退化。", "错误数、前台尾延迟、吞吐退化、温度", "约 8 小时", "PASS：0 错误；无持续超过 10% 的退化；温度、空间和队列在安全范围。", users=50, dimensions=128)


def _write_case(spec: dict[str, object]) -> None:
    filename = f"test_{spec['category']}_{spec['case_name']}.py"
    payload = json.dumps(spec, ensure_ascii=False, indent=4)
    content = f'''"""{spec['case_id']} · {spec['case_name']}\n\nGenerated from docs/AI_SSD_TEST_PLAN.xlsx.\n"""\n\nfrom __future__ import annotations\n\nimport sys\nfrom pathlib import Path\n\n_REPO_ROOT = Path(__file__).resolve().parents[1]\nif str(_REPO_ROOT) not in sys.path:\n    sys.path.insert(0, str(_REPO_ROOT))\n\nfrom ai_ssd_test_cases.runner_support import execute_case\n\nCASE_SPEC = {payload}\n\n\nif __name__ == "__main__":\n    raise SystemExit(execute_case(CASE_SPEC))\n'''
    (OUT / filename).write_text(content, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for existing in OUT.glob("test_*.py"):
        existing.unlink()
    for spec in CASES:
        _write_case(spec)
    catalog = {str(spec["case_id"]): spec for spec in CASES}
    (OUT / "case_catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    readme = """# AI SSD Test Cases

本目录按 `docs/AI_SSD_TEST_PLAN.xlsx` 拆分为 72 个独立用例。

## 命名规则

每个脚本均为 `test_<类别>_<case_name>.py`：

- `test_base_*.py`：基础路径、缓存和填充率
- `test_training_*.py`：训练供数
- `test_checkpoint_*.py`：Checkpoint 持久化与恢复
- `test_kv_*.py`：KV Cache tier 与尾延迟
- `test_vdb_*.py`：VectorDB 建库与查询
- `test_mixed_*.py`：前台/后台混合干扰

## 运行方式

默认只生成执行计划和 manifest，不会启动重负载：

```powershell
python ai_ssd_test_cases/test_training_unet3d_a100_baseline.py
```

执行可重复的 scaled smoke probe：

```powershell
python ai_ssd_test_cases/test_training_unet3d_a100_baseline.py --execute --prepare --data-dir <DUT_DATA> --result-dir <RESULTS>
```

`--execute` 的 Checkpoint/KV/VectorDB/Mixed 脚本使用标准库实现小规模 probe，结果用于验证路径、读写、尾延迟和并发逻辑；Checkpoint 默认最多写 8 个缩放分片，只有在授权 DUT 上才使用 `--full-scale`。正式容量、模型、Milvus 索引或 MLPerf SLA 测试应替换为批准的 workload，并保留同一 Case ID。

所有脚本都包含测试目的、编号步骤、测试时长、命令和通过标准；完整字段可查 `case_catalog.json`。
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    print(f"generated={len(CASES)} directory={OUT}")


if __name__ == "__main__":
    main()
