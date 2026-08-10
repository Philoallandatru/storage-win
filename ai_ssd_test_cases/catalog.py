"""Machine-readable catalog for the legacy AI SSD 72-case matrix.

The Excel plan predates the current ``full_test_plan_cases`` catalog.  This
module keeps the old IDs executable without pretending that every old
workload has a current MLPerf-native implementation.  ``execution`` tells
the runner whether it delegates to a native case, uses a real Python scaled
workload, or must stop with a controlled explanation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    family: str
    entrypoint: str
    execution: str
    profile: str
    native_case_id: str | None = None
    destructive: bool = False


_LEGACY_FILENAMES = {
    "AI-TRN-001": "test_ai_trn_001_unet3d_a100.py",
    "AI-TRN-002": "test_ai_trn_002_unet3d_h100.py",
    "AI-TRN-003": "test_ai_trn_003_unet3d_b200.py",
    "AI-TRN-004": "test_ai_trn_004_retinanet_b200_jpeg.py",
    "AI-TRN-005": "test_ai_trn_005_retinanet_mi355_jpeg.py",
    "AI-TRN-006": "test_ai_trn_006_cosmoflow_a100_tfrecord.py",
    "AI-TRN-007": "test_ai_trn_007_cosmoflow_h100_tfrecord.py",
    "AI-TRN-008": "test_ai_trn_008_resnet50_a100_tfrecord.py",
    "AI-TRN-009": "test_ai_trn_009_resnet50_h100_tfrecord.py",
    "AI-TRN-010": "test_ai_trn_010_dlrm_b200_parquet.py",
    "AI-TRN-011": "test_ai_trn_011_dlrm_mi355_parquet.py",
    "AI-TRN-012": "test_ai_trn_012_flux_b200_parquet.py",
    "AI-TRN-013": "test_ai_trn_013_flux_mi355_parquet.py",
    "AI-TRN-014": "test_ai_trn_014_training_concurrency.py",
    "AI-TRN-015": "test_ai_trn_015_read_threads_saturation.py",
    "AI-TRN-016": "test_ai_trn_016_warm_cold_direct.py",
    "AI-BASE-001": "test_base_dut_path_capacity.py",
    "AI-BASE-002": "test_base_cache_path_modes.py",
    "AI-BASE-003": "test_base_repeatability_monitor_overhead.py",
    "AI-BASE-004": "test_base_fill_level_degradation.py",
    "AI-CKP-001": "test_checkpoint_8b_full_baseline.py",
    "AI-CKP-002": "test_checkpoint_70b_subset.py",
    "AI-CKP-003": "test_checkpoint_70b_full_distributed.py",
    "AI-CKP-004": "test_checkpoint_405b_subset.py",
    "AI-CKP-005": "test_checkpoint_405b_full_shared.py",
    "AI-CKP-006": "test_checkpoint_1t_subset.py",
    "AI-CKP-007": "test_checkpoint_1t_full_distributed.py",
    "AI-CKP-008": "test_checkpoint_cold_warm_recovery.py",
    "AI-CKP-009": "test_checkpoint_interval_burst_gc.py",
    "AI-KV-001": "test_kv_option1_8b_nvme_only.py",
    "AI-KV-002": "test_kv_option2_cpu_spill.py",
    "AI-KV-003": "test_kv_option3_70b.py",
    "AI-KV-004": "test_kv_tiny1b_smoke.py",
    "AI-KV-005": "test_kv_mistral7b_gqa.py",
    "AI-KV-006": "test_kv_llama2_7b_upper_bound.py",
    "AI-KV-007": "test_kv_llama31_8b_users.py",
    "AI-KV-008": "test_kv_llama31_70b_users.py",
    "AI-KV-009": "test_kv_deepseek_v3_mla.py",
    "AI-KV-010": "test_kv_qwen3_32b_sweep.py",
    "AI-KV-011": "test_kv_gpt_oss_20b_moe.py",
    "AI-KV-012": "test_kv_gpt_oss_120b.py",
    "AI-KV-013": "test_kv_tier_capacity_matrix.py",
    "AI-KV-014": "test_kv_tensor_parallel_matrix.py",
    "AI-KV-015": "test_kv_prefill_write.py",
    "AI-KV-016": "test_kv_decode_read.py",
    "AI-KV-017": "test_kv_context_personas.py",
    "AI-KV-018": "test_kv_generation_modes.py",
    "AI-KV-019": "test_kv_rag_prefix_multiturn.py",
    "AI-KV-020": "test_kv_saturation_autoscale.py",
    "AI-KV-021": "test_kv_tier2_trace_replay.py",
    "AI-KV-022": "test_kv_burstgpt_sharegpt.py",
    "AI-VDB-001": "test_vdb_hnsw_1k_smoke.py",
    "AI-VDB-002": "test_vdb_hnsw_1m.py",
    "AI-VDB-003": "test_vdb_diskann_1m_1536.py",
    "AI-VDB-004": "test_vdb_diskann_1m_512.py",
    "AI-VDB-005": "test_vdb_aisaq_1m_512.py",
    "AI-VDB-006": "test_vdb_hnsw_10m.py",
    "AI-VDB-007": "test_vdb_diskann_10m.py",
    "AI-VDB-008": "test_vdb_index_family_sweep.py",
    "AI-VDB-009": "test_vdb_search_effort_sweep.py",
    "AI-VDB-010": "test_vdb_query_process_scaling.py",
    "AI-VDB-011": "test_vdb_search_batch_scaling.py",
    "AI-VDB-012": "test_vdb_ingest_tuning.py",
    "AI-VDB-013": "test_vdb_topk_metric_dimension.py",
    "AI-VDB-014": "test_vdb_cold_warm_search.py",
    "AI-VDB-015": "test_vdb_logical_trace_replay.py",
    "AI-VDB-016": "test_vdb_ingest_search_coexist.py",
    "AI-MIX-001": "test_mixed_training_checkpoint.py",
    "AI-MIX-002": "test_mixed_kv_decode_checkpoint.py",
    "AI-MIX-003": "test_mixed_vdb_search_ingest.py",
    "AI-MIX-004": "test_mixed_kv_interactive_vdb_search.py",
    "AI-MIX-005": "test_mixed_four_class_soak.py",
}


def _entrypoint(case_id: str) -> str:
    return f"ai_ssd_test_cases/{_LEGACY_FILENAMES[case_id]}"


def _case(
    case_id: str,
    family: str,
    execution: str,
    profile: str,
    *,
    native_case_id: str | None = None,
    destructive: bool = False,
) -> CaseSpec:
    return CaseSpec(
        case_id=case_id,
        family=family,
        entrypoint=_entrypoint(case_id),
        execution=execution,
        profile=profile,
        native_case_id=native_case_id,
        destructive=destructive,
    )


CASES: dict[str, CaseSpec] = {}


for number in range(1, 17):
    case_id = f"AI-TRN-{number:03d}"
    if number in {3, 4, 5}:
        execution = "native"
        native_case_id = case_id
    elif number == 1:
        execution = "native_special"
        native_case_id = case_id
    else:
        execution = "python_scaled"
        native_case_id = None
    CASES[case_id] = _case(
        case_id,
        "Training",
        execution,
        f"training_{number:03d}",
        native_case_id=native_case_id,
    )


for number, profile in (
    (1, "path_capacity"),
    (2, "cache_modes"),
    (3, "repeatability"),
    (4, "fill_degradation"),
):
    case_id = f"AI-BASE-{number:03d}"
    CASES[case_id] = _case(
        case_id,
        "BASE",
        "python_base",
        profile,
        destructive=number == 4,
    )


for number in range(1, 10):
    case_id = f"AI-CKP-{number:03d}"
    execution = "native" if number <= 7 else "python_scaled"
    CASES[case_id] = _case(
        case_id,
        "Checkpoint",
        execution,
        f"checkpoint_{number:03d}",
        native_case_id=case_id if number <= 7 else None,
        destructive=True,
    )


for number in range(1, 23):
    case_id = f"AI-KV-{number:03d}"
    execution = "native" if number <= 8 else "python_scaled"
    CASES[case_id] = _case(
        case_id,
        "KV Cache",
        execution,
        f"kv_{number:03d}",
        native_case_id=case_id if number <= 8 else None,
    )


for number in range(1, 17):
    case_id = f"AI-VDB-{number:03d}"
    if number == 15:
        execution = "trace"
        native_case_id = None
    elif number == 16 or number <= 14:
        execution = "native"
        native_case_id = case_id
    else:
        execution = "python_scaled"
        native_case_id = None
    CASES[case_id] = _case(
        case_id,
        "VectorDB",
        execution,
        f"vdb_{number:03d}",
        native_case_id=native_case_id,
    )


for number in range(1, 6):
    case_id = f"AI-MIX-{number:03d}"
    CASES[case_id] = _case(
        case_id,
        "Mixed",
        "python_scaled",
        f"mixed_{number:03d}",
        destructive=True,
    )


def get_case(case_id: str) -> CaseSpec:
    """Return a case definition using case-insensitive IDs."""

    try:
        return CASES[case_id.upper()]
    except KeyError as error:
        known = ", ".join(sorted(CASES))
        raise KeyError(f"Unknown AI SSD case {case_id!r}; known cases: {known}") from error


def entrypoint_paths(repo_root: Path) -> list[Path]:
    """Return the expected entrypoint files in stable catalog order."""

    return [repo_root / spec.entrypoint for spec in CASES.values()]
