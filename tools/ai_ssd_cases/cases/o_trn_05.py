from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.ai_ssd_cases.runner import main
if __name__ == "__main__":
    raise SystemExit(main("O-TRN-05"))
