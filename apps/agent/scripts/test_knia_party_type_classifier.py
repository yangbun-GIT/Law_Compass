from __future__ import annotations
import json
from app.services.scenario_classifier import classify_scenario

CASES = [
    ("신호대기 중 정차했는데 뒤차가 박았어.", "car_vs_car", "rear_end_collision"),
    ("횡단보도에서 사람과 접촉 사고가 났어.", "car_vs_person", "pedestrian_crosswalk_accident"),
    ("자전거랑 부딪혔어.", "car_vs_bicycle", "bicycle_collision"),
    ("혼자 가드레일을 들이받았어.", "car_vs_object", "object_collision"),
    ("빗길에 미끄러져 혼자 사고가 났어.", "single_vehicle", "single_vehicle_accident"),
]

def main() -> int:
    rows = []
    for text, party, scenario in CASES:
        result = classify_scenario(text, {}, [])
        assert result["accident_party_type"] == party, f"{text}: {result}"
        assert result["scenario_type"] == scenario, f"{text}: {result}"
        rows.append({"text": text, **result})
    print(json.dumps({"party_type_classifier_tests": "passed", "items": rows}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
