@echo off
REM ============================================================
REM  AI-VDB-005  - cannot run on this machine
REM ============================================================
setlocal
echo [%~n0] SKIPPED: AISAQ index requires a full Milvus server (Milvus Lite: unknown index_type 'AISAQ')
echo To run this case, satisfy the requirement above and use the suite
echo script or run_case directly (see docs/AI_SSD_CASE_MATRIX.md).
exit /b 1
