from __future__ import annotations

import json
import os
from pathlib import Path

if os.getenv("LAWCOMPASS_SAMPLE_USE_LLM", "0") != "1":
    os.environ["OPENAI_API_KEY"] = ""

from app.services.orchestrator import analyze_scenario

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "sample_scenarios"


def main():
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = analyze_scenario(payload)
        evidence = result.get("evidence", [])
        print("=" * 100)
        print(f"scenario name={path.name}")
        print(f"scenario_type={result.get('scenario_type')}")
        print(f"legal_analysis={json.dumps(result.get('legal_analysis'), ensure_ascii=False)}")
        print(f"fault_ratio={json.dumps(result.get('fault_ratio'), ensure_ascii=False)}")
        print(f"criminal_liability={json.dumps(result.get('legal_liability'), ensure_ascii=False)}")
        print(f"insurance_guide={json.dumps(result.get('insurance_guide'), ensure_ascii=False)}")
        print(f"evidence count={len(evidence)}")
        if evidence:
            top = evidence[0]
            print(f"top evidence={top.get('title')} / {top.get('source')} / score={top.get('score')}")
        print(f"final report summary={result.get('accident_summary')}")


if __name__ == "__main__":
    main()
