"""Per-case wrappers for the 16 AI SSD Training cases.

Each ``test_training_ai_trn_<NNN>_<model>.py`` is a thin shell that delegates
to ``_common.run_case``; the case-specific rationale (model, accelerator,
data format, dataset size, hardware blockers) lives in the wrapper's
docstring so it is visible without opening any other file.

The wrappers in this directory are derived from
``docs/AI_SSD_ALL_CASE_PLAN.xlsx`` (Training Case 表) plus the eight
corrections documented in ``docs/AI_SSD_TRAINING_CASE_PLAN_REVIEW.md``:

* the "测试命令" column is non-executable as-written; the wrapper
  fills in ``--execute`` / ``--prepare`` / ``--confirm-dut`` /
  ``--scale-mb`` as the case profile requires;
* the "测试工具" column says ``mlperform``; the real entry point is
  ``tools/ai_ssd_training_case_runner.py`` (or the catalog-native
  benchmark entry);
* the "Capacity" column conflates the *target SSD* (1 TB / 2 TB / 4 TB)
  with the *dataset size* (22.9 GiB / 352 GiB / 983 GiB); the wrapper
  records the dataset size separately so the two are not confused;
* the "测试标准" thresholds (AU ≥ 70/85/90 %) are aspirational and
  are not enforced anywhere in the codebase; the wrapper does not
  invent a new threshold;
* sweep / multi-stage steps in the "测试步骤" column cannot be
  reproduced by the Python-scaled harness (TRN-014/015/016); the
  wrapper documents the limitation and labels the run NOT_FORMAL;
* ``multiprocessing_context: fork`` in the four native YAMLs is the
  actual Windows blocker for TRN-001/003/004/005; the wrapper
  surfaces this in its docstring and lets the operator decide.

The four native cases (TRN-001/003/004/005) need a target disk with at
least 1.2x the dataset size and an ``mlpstorage init``-ed results
directory.  The twelve python_scaled cases need nothing more than a
scratch data dir; the wrapper auto-cleans the synthetic
``python_scaled/`` subtree on exit unless ``--keep-data`` is passed.
"""
