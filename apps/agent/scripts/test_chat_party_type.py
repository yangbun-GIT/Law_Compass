from __future__ import annotations
import json
from app.services.chat.chat_orchestrator import handle_chat_message

CASES = [
    ("정차 중 뒤차가 박았어.", "car_vs_car", "후미"),
    ("횡단보도에서 사람과 접촉 사고가 났어.", "car_vs_person", "다친"),
    ("자전거랑 부딪혔어.", "car_vs_bicycle", "자전거"),
    ("혼자 가드레일을 들이받았어.", "car_vs_object", "시설물"),
    ("빗길에 미끄러져 혼자 사고가 났어.", "single_vehicle", "단독"),
]

def main() -> int:
    rows = []
    for text, party, phrase in CASES:
        res = handle_chat_message({"session_id": "party-test", "message": text, "context": {"page": "dashboard"}, "history": []})
        draft = res.get("draft_case") or {}
        facts = draft.get("structured_facts") or {}
        assert facts.get("accident_party_type") == party, f"{text}: {facts}"
        assert phrase in res.get("reply", "") or phrase in json.dumps(draft, ensure_ascii=False), f"{text}: reply lacks {phrase}"
        labels = [s.get("label") for s in res.get("suggestions") or []]
        assert "많이 검색된 사고유형 보기" in labels, f"{text}: ranking suggestion missing"
        assert any(label in labels for label in ["비슷한 과실비율 기준 보기", "관련 영상 보기", "원문 기준 보기"]), f"{text}: KNIA suggestion missing {labels}"
        rows.append({"text": text, "party": party, "reply": res.get("reply"), "suggestions": labels[:6]})
    print(json.dumps({"chat_party_type_tests": "passed", "items": rows}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
