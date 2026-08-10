"""Machine-readable catalog for the consumer AI-PC SSD matrix.

The catalog intentionally contains the 17 core and 3 optional native workload
cases from the consumer AI-PC plan, rather than the larger exploratory matrix.
Each case has a real ``mlpstorage`` action in ``runner.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    stage: str
    family: str
    mode: str
    kind: str
    purpose: str
    pass_criteria: str
    duration: str
    destructive: bool = False
    requirements: tuple[str, ...] = field(default_factory=tuple)
    default_model: str | None = None


def _case(
    case_id: str,
    stage: str,
    family: str,
    mode: str,
    kind: str,
    purpose: str,
    pass_criteria: str,
    duration: str,
    *,
    destructive: bool = False,
    requirements: tuple[str, ...] = (),
    default_model: str | None = None,
) -> CaseSpec:
    return CaseSpec(
        case_id=case_id,
        stage=stage,
        family=family,
        mode=mode,
        kind=kind,
        purpose=purpose,
        pass_criteria=pass_criteria,
        duration=duration,
        destructive=destructive,
        requirements=requirements,
        default_model=default_model,
    )


CASES: dict[str, CaseSpec] = {
    "S2-TRN-01": _case(
        "S2-TRN-01", "Stage 2", "Training", "Native", "training_smoke",
        "验证 UNet3D 数据实际从 DUT 读取并产生有效 AU/吞吐",
        "退出码 0、AU/吞吐存在、DUT 物理读量大于 0",
        "20–30 min", default_model="unet3d",
    ),
    "S2-CKPT-01": _case(
        "S2-CKPT-01", "Stage 2", "Checkpoint", "Native", "checkpoint_smoke",
        "验证 Llama3-8B checkpoint 写入、读取和完整性闭环",
        "读写字节、文件大小和 hash 一致；恢复退出码 0",
        "30–60 min", default_model="llama3-8b",
    ),
    "S2-KV-01": _case(
        "S2-KV-01", "Stage 2", "KV Cache", "Native", "kv_smoke",
        "验证 Tier-2 cache directory 命中 DUT 并产生真实 I/O",
        "Tier-2 bytes > 0；无异常 eviction/I/O error",
        "15–25 min", default_model="llama3.1-8b",
    ),
    "S2-VDB-01": _case(
        "S2-VDB-01", "Stage 2", "VectorDB", "Native", "vdb_smoke",
        "验证 Docker/Milvus 的 ingest、flush、load 和 query 链路",
        "服务 ready、row count 正确、查询成功、证据齐全",
        "30–60 min", requirements=("Docker Desktop", "Milvus"),
    ),
    "S3-TRN-01": _case(
        "S3-TRN-01", "Stage 3", "Training", "Hybrid", "training_profile",
        "测 UNet3D 大文件持续供给、AU 和 reader 扩展",
        "AU >= 0.90；scaled/native 标识清晰；找到饱和点",
        "60–120 min", default_model="unet3d",
    ),
    "S3-TRN-02": _case(
        "S3-TRN-02", "Stage 3", "Training", "Hybrid", "training_profile",
        "测 RetinaNet 小文件 metadata、IOPS 和尾延迟",
        "AU >= 0.85；并发增加无错误和数据缺失",
        "60–120 min", default_model="retinanet",
    ),
    "S3-CKPT-01": _case(
        "S3-CKPT-01", "Stage 3", "Checkpoint", "Native", "checkpoint_profile",
        "测 8B checkpoint 多轮写读、fsync 和冷恢复退化",
        "hash 一致；连续窗口下降 <= 10%，否则标记 cliff",
        "2–4 h", destructive=True, default_model="llama3-8b",
    ),
    "S3-CKPT-02": _case(
        "S3-CKPT-02", "Stage 3", "Checkpoint", "Hybrid", "checkpoint_subset",
        "测 70B 8-rank 分片形态而不伪装 full 规模",
        "subset/trace 标识清晰；hash 正确；恢复成功",
        "60–120 min", default_model="llama3-70b",
    ),
    "S3-CKPT-03": _case(
        "S3-CKPT-03", "Stage 3", "Checkpoint", "Hybrid", "checkpoint_burst",
        "测连续 checkpoint 间隔、GC 和后续恢复退化",
        "无错误；后半程下降 > 10% 时报告 cliff 和恢复时间",
        "90–180 min", destructive=True, default_model="llama3-8b",
    ),
    "S3-KV-01": _case(
        "S3-KV-01", "Stage 3", "KV Cache", "Native", "kv_native",
        "测 8B NVMe-only KV 的并发读写和尾延迟",
        "Tier-2 bytes > 0；P99 可复现；无 eviction/I/O error",
        "45–90 min", default_model="llama3.1-8b",
    ),
    "S3-KV-02": _case(
        "S3-KV-02", "Stage 3", "KV Cache", "Native", "kv_spill",
        "定位 CPU tier 耗尽后的 NVMe spill 拐点",
        "spill 可解释；Tier-2 bytes 增长；无数据丢失",
        "45–90 min", default_model="llama3.1-8b",
    ),
    "S3-VDB-01": _case(
        "S3-VDB-01", "Stage 3", "VectorDB", "Native", "vdb_native",
        "建立 1M×1536 HNSW/DISKANN RAG 基线",
        "Recall 达标；row count 正确；QPS/P99 可重复",
        "2–4 h", requirements=("Docker Desktop", "Milvus"),
    ),
    "S3-VDB-02": _case(
        "S3-VDB-02", "Stage 3", "VectorDB", "Hybrid", "vdb_large",
        "测 5M/10M DISKANN 的 load、compaction 和在线搜索干扰",
        "Recall/row count 正确；前后台指标分开报告",
        "4–8 h", requirements=("Docker Desktop", "Milvus"),
    ),
    "S4-MIX-01": _case(
        "S4-MIX-01", "Stage 4", "Mixed", "Hybrid", "mix_kv_checkpoint",
        "测 checkpoint 大写对 KV decode 尾延迟的影响",
        "前台 P99 <= solo 1.5x；后台吞吐 >= solo 80%",
        "60–120 min", destructive=True, default_model="llama3-8b",
    ),
    "S4-MIX-02": _case(
        "S4-MIX-02", "Stage 4", "Mixed", "Native", "mix_vdb",
        "测 VDB search 在 ingest/compaction 下的 QoS",
        "Recall 下降 <= 1 个百分点；P99 <= solo 1.5x",
        "60–120 min", requirements=("Docker Desktop", "Milvus"),
    ),
    "S4-MIX-03": _case(
        "S4-MIX-03", "Stage 4", "Mixed", "Hybrid", "mix_training_checkpoint",
        "测训练读与 checkpoint 写共存时的 AU 和写入窗口",
        "AU 下降 <= 10%；checkpoint hash 正确；无 I/O error",
        "60–120 min", destructive=True, default_model="llama3-8b",
    ),
    "S5-SOAK-02": _case(
        "S5-SOAK-02", "Stage 5", "Stability", "Hybrid", "soak_mixed",
        "测多小时 KV、checkpoint、VDB 混合负载的漂移",
        "无数据损坏/重启；漂移可解释；恢复偏差 <= 10%",
        "4–24 h", destructive=True, default_model="llama3-8b",
    ),
    "O-CKPT-04": _case(
        "O-CKPT-04", "Optional", "Checkpoint", "Hybrid", "checkpoint_subset",
        "比较 405B subset 的 shard 形态，不证明 full 405B",
        "明确 subset；hash 一致；不得称 full",
        "60–120 min", default_model="llama3-405b",
    ),
    "O-KV-05": _case(
        "O-KV-05", "Optional", "KV Cache", "Native", "kv_persona",
        "覆盖 RAG、prefix cache、multi-turn 和 autoscaling",
        "相对 baseline 的退化可解释；无异常 eviction",
        "2–4 h", default_model="llama3.1-8b",
    ),
    "O-VDB-03": _case(
        "O-VDB-03", "Optional", "VectorDB", "Native", "vdb_aisaq",
        "分析 1M×512 AISAQ 的压缩、容量和 Recall",
        "Recall 达标；容量和 I/O 放大有记录",
        "2–4 h", requirements=("Docker Desktop", "Milvus"),
    ),
}


def get_case(case_id: str) -> CaseSpec:
    """Return a case spec or raise a useful error."""

    try:
        return CASES[case_id.upper()]
    except KeyError as error:
        known = ", ".join(sorted(CASES))
        raise KeyError(f"Unknown case {case_id!r}; known cases: {known}") from error
