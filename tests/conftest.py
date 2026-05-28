from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_APP = ROOT / "apps" / "agent"
if str(AGENT_APP) not in sys.path:
    sys.path.insert(0, str(AGENT_APP))
