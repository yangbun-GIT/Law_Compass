from pathlib import Path
from runpy import run_path

globals().update({k: v for k, v in run_path(str(Path(__file__).resolve().parents[1] / "apps" / "agent" / "tests" / "test_input_filter_knia_major_party.py")).items() if not k.startswith("__")})
