from pathlib import Path
from runpy import run_path

globals().update({k: v for k, v in run_path(str(Path(__file__).resolve().parents[1] / "apps" / "agent" / "tests" / "test_rear_end_user_perspective.py")).items() if not k.startswith("__")})
