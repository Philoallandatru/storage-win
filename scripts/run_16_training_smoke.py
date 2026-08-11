"""Run all 16 Training wrappers inline."""
import importlib.util, json, sys, time, traceback, re
from pathlib import Path

REPO = Path(r"C:\Users\Administrator\Documents\Code\repos\storage")
TRAINING = REPO / "ai_ssd_test_cases" / "training"
DATA = REPO / ".smoke_data"
RESULT = REPO / ".smoke_results"
DATA.mkdir(parents=True, exist_ok=True)
RESULT.mkdir(parents=True, exist_ok=True)

wrappers = sorted(TRAINING.glob("test_training_*.py"))
print(f"== running {len(wrappers)} wrappers inline ==")

# 从文件名提 case_id
def parse_case_id(stem):
    m = re.search(r"ai_trn_(\d{3})", stem)
    return f"AI-TRN-{m.group(1)}" if m else None

results = []
for path in wrappers:
    case_id = parse_case_id(path.stem)
    if not case_id:
        continue
    name = path.name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"  IMPORT_FAIL {name}: {e}")
        results.append({"name": name, "status": "IMPORT_FAIL", "error": str(e)})
        continue
    info = mod.DEFAULT_CASES.get(case_id)
    if info is None:
        print(f"  NO_CASE_INFO {name}")
        continue
    sys.argv = [name, "--data-dir", str(DATA), "--result-dir", str(RESULT),
                "--scale-mb", "256", "--duration-sec", "5", "--repeat", "1", "--timeout-sec", "60"]
    t0 = time.perf_counter()
    try:
        rc = mod.main(case_id, info)
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    except Exception:
        traceback.print_exc()
        rc = 1
    wall = time.perf_counter() - t0
    status = {0: "PASS", 2: "BLOCKED", 124: "TIMEOUT"}.get(rc, "FAIL")
    print(f"  {status:<8} rc={rc:<3} wall={wall:.2f}s {name}")
    results.append({"name": name, "rc": rc, "status": status, "wall": round(wall, 2)})

print()
print("== summary ==")
counts = {}
for r in results:
    counts[r["status"]] = counts.get(r["status"], 0) + 1
print("  status counts:", counts)
