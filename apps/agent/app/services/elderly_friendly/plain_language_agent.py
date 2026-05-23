from __future__ import annotations

from typing import Any
from app.services.elderly_friendly.ui_text_mapper import as_percent, confidence_label, field_label, risk_label, scenario_label, scrub_user_text

SAFE_QUESTION_FIELDS = {
    "accident_type",
    "signal_state",
    "injury",
    "opponent_behavior",
    "damage_level",
    "stopped",
    "sudden_brake",
    "school_zone",
    "victim_is_child",
    "crosswalk_nearby",
    "lane_change_actor",
    "turn_signal",
    "user_signal",
    "opponent_signal",
    "opponent_signal_violation",
    "pedestrian_signal",
    "bicycle_location",
    "bicycle_direction",
}

class PlainLanguageAgent:
    def make_headline(self, result: dict[str, Any]) -> str:
        scenario = result.get("scenario_type") or result.get("structured_facts", {}).get("scenario_type")
        facts = result.get("structured_facts", {}) or {}
        fault = result.get("fault_ratio", {}) or {}
        legal = result.get("legal_liability", {}) or {}
        if _needs_review(fault) or _needs_review(legal):
            return "입력하신 사고는 근거가 더 필요해 과실과 신고 필요 여부를 조심스럽게 확인해야 합니다."
        if scenario == "school_zone_child_accident" or facts.get("school_zone"):
            return "어린이보호구역 사고로 보이며, 신고와 형사 문제를 꼭 확인해 보셔야 합니다."
        if scenario == "rear_end_collision":
            return "이번 사고는 정차 중 뒤차가 들이받은 사고로 보이며, 상대 차량 책임이 더 클 가능성이 높습니다."
        if scenario == "intersection_signal_violation":
            return "교차로에서 상대 차량의 신호위반 여부가 핵심으로 보입니다."
        if scenario == "lane_change_collision":
            return "상대 차량이 차선을 바꿀 때 충분히 조심했는지 확인해야 합니다."
        if scenario == "pedestrian_crosswalk_accident":
            return "보행자 보호 의무와 다친 사람이 있는지를 먼저 확인해야 하는 사고입니다."
        return "입력하신 사고는 추가 사실을 확인하면서 과실과 신고 필요 여부를 살펴봐야 합니다."

    def make_summary(self, result: dict[str, Any]) -> dict[str, str]:
        scenario = result.get("scenario_type") or result.get("structured_facts", {}).get("scenario_type")
        summary = scrub_user_text(result.get("accident_summary"), "입력하신 사고 내용을 바탕으로 교통사고 대응 방향을 정리했습니다.")
        fault = result.get("fault_ratio", {}) or {}
        confidence = "추가 확인 필요" if _needs_review(fault) else confidence_label(fault.get("confidence"))
        return {"accident_type_label": scenario_label(scenario), "short_summary": self._shorten(summary), "confidence_label": confidence, "warning": _section_notice(fault, "정확한 과실비율은 보험사나 분쟁심의 결과에 따라 달라질 수 있습니다.")}

    def make_top_actions(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        facts = result.get("structured_facts", {}) or {}
        legal = result.get("legal_liability", {}) or {}
        scenario = result.get("scenario_type")
        actions: list[dict[str, str]] = [{"title": "블랙박스 원본 보관", "description": "영상 파일을 삭제하지 말고 따로 저장해 두세요.", "importance": "매우 중요"}]
        if facts.get("injury") or legal.get("reporting_required") or scenario == "school_zone_child_accident":
            actions.append({"title": "병원 진료 확인", "description": "목이나 허리가 아프면 병원 진료를 받고 진단서 또는 진료확인서를 받아두세요.", "importance": "중요"})
        if legal.get("reporting_required") or scenario == "school_zone_child_accident":
            actions.append({"title": "경찰 신고 여부 확인", "description": "다친 사람이 있거나 어린이보호구역 사고라면 경찰 신고가 필요한지 확인하세요.", "importance": "중요"})
        actions.append({"title": "보험사 사고 접수", "description": "보험사에 사고를 접수하고 사고접수번호를 기록하세요.", "importance": "중요"})
        actions.append({"title": "사진과 서류 정리", "description": "차량 파손 사진, 사고 현장 사진, 수리 견적서를 한곳에 모아두세요.", "importance": "중요"})
        unique: list[dict[str, Any]] = []
        seen = set()
        for item in actions:
            if item["title"] in seen: continue
            seen.add(item["title"])
            unique.append({"order": len(unique) + 1, **item})
            if len(unique) == 3: break
        return unique

    def make_fault_explanation(self, result: dict[str, Any]) -> dict[str, Any]:
        fault = result.get("fault_ratio", {}) or {}
        scenario = result.get("scenario_type")
        my = as_percent(fault.get("my"), 10 if scenario == "rear_end_collision" else None)
        other = as_percent(fault.get("other"), 90 if scenario == "rear_end_collision" else None)
        if my is None and other is not None: my = max(0, 100 - other)
        if other is None and my is not None: other = max(0, 100 - my)
        if my is None:
            my = 50
        if other is None:
            other = max(0, 100 - my)
        if scenario == "rear_end_collision":
            easy = "정차 중 뒤에서 추돌당한 사고라면 일반적으로 뒤차의 책임이 더 크게 볼 수 있습니다."
            why = ["내 차량이 정차 중이었다는 점", "상대 차량이 뒤에서 추돌했다는 점", "뒤차는 앞차와 안전거리를 유지해야 한다는 점"]
            caution = "단, 급정거 여부나 사고 당시 도로 상황에 따라 달라질 수 있습니다."
        elif scenario == "lane_change_collision":
            easy = "차선을 바꾸는 차량은 주변 차량을 살피고 안전하게 들어와야 합니다."
            why = ["상대 차량의 차선 변경 여부", "방향지시등 사용 여부", "충돌 부위와 당시 속도"]
            caution = "블랙박스 각도와 차선 위치에 따라 판단이 달라질 수 있습니다."
        elif scenario == "intersection_signal_violation":
            easy = "교차로 사고는 신호를 누가 지켰는지가 중요한 판단 기준입니다."
            why = ["교차로에서 발생했다는 점", "상대 차량의 신호위반 여부", "내 차량의 진행 신호"]
            caution = "신호등 상태를 확인할 수 있는 영상이나 목격자 진술이 중요합니다."
        else:
            easy = "입력하신 사고 내용과 관련 근거를 바탕으로 참고용 과실비율을 추정했습니다."
            why = ["사고 유형", "다친 사람 여부", "신호와 차선 상황"]
            caution = "추가 사실에 따라 과실비율은 달라질 수 있습니다."
        if _needs_review(fault):
            easy = "현재 연결된 근거만으로는 과실비율을 확정하기 어렵고, 아래 비율은 추가 확인이 필요한 참고 추정입니다."
            why = _review_reasons(fault, why)
            caution = _section_notice(fault, "KNIA 기준이나 영상·현장 자료가 보강되기 전까지는 과실비율을 확정처럼 보아서는 안 됩니다.")
        return {"my_percent": my, "other_percent": other, "easy_explanation": easy, "why": why, "caution": caution}

    def make_insurance_explanation(self, result: dict[str, Any]) -> dict[str, Any]:
        insurance = result.get("insurance_guide", {}) or {}
        steps = [scrub_user_text(x) for x in (insurance.get("steps") or []) if x] or ["보험사에 사고를 접수합니다.", "블랙박스 원본을 제출할 수 있도록 보관합니다.", "차량 수리 견적서를 받아둡니다.", "통증이 있으면 병원 진료 후 진단서를 받아둡니다."]
        docs = [scrub_user_text(x) for x in (insurance.get("required_documents") or []) if x] or ["블랙박스 영상", "사고 현장 사진", "차량 파손 사진", "수리 견적서", "진단서 또는 진료확인서"]
        summary = scrub_user_text(insurance.get("summary"), "대물 접수와 대인 접수 여부를 확인해야 합니다.")
        if _needs_review(insurance):
            summary = _section_notice(insurance, "보험 처리 방향은 일반 절차 기준의 참고 안내이며, 보험사 접수 후 실제 보장 범위와 서류를 다시 확인해야 합니다.")
        return {"simple_summary": summary, "steps": steps[:6], "documents": docs[:8]}

    def make_legal_explanation(self, result: dict[str, Any]) -> dict[str, Any]:
        legal = result.get("legal_liability", {}) or {}
        facts = result.get("structured_facts", {}) or {}
        checklist = [scrub_user_text(x) for x in (legal.get("checklist") or []) if x] or ["다친 사람이 있는지 확인", "음주운전이나 무면허 여부 확인", "도주 여부 확인", "신호위반이나 중앙선 침범 같은 중대한 위반 여부 확인"]
        if facts.get("school_zone"): checklist.insert(0, "어린이보호구역 사고인지 확인")
        if _needs_review(legal):
            summary = "현재 근거만으로는 신고나 형사책임 여부를 단정하기 어렵고, 아래 항목을 추가로 확인해야 합니다."
            label = "확인 필요"
            caution = _section_notice(legal, "형사책임 여부는 경찰이나 법원의 판단이 필요하며, 직접적인 법률 근거가 보강되면 다시 확인해야 합니다.")
        else:
            summary = "신고나 형사 문제를 확인해 볼 필요가 있습니다." if legal.get("reporting_required") else "인명피해가 있거나 큰 위반이 의심되면 신고 여부를 확인해야 합니다."
            label = risk_label(legal.get("criminal_risk_level"))
            caution = "형사책임 여부는 경찰이나 법원의 판단이 필요합니다."
        return {"simple_summary": summary, "risk_label": label, "checklist": list(dict.fromkeys(checklist))[:7], "caution": caution}

    def make_missing_info(self, result: dict[str, Any]) -> dict[str, Any]:
        facts = result.get("structured_facts", {}) or {}
        required_questions = _required_questions(result)
        required_question_texts = [item["question"] for item in required_questions]
        missing = required_question_texts + list(result.get("suggested_next_inputs") or []) + list(result.get("followup_questions") or [])
        if not required_question_texts:
            missing = list(facts.get("missing_fields") or []) + missing
        if not missing: missing = ["사고 당시 완전히 정차 중이었는지", "급정거가 있었는지", "목이나 허리 통증이 있는지", "경찰 신고를 했는지"]
        items: list[str] = []
        for item in missing:
            text = field_label(item) if isinstance(item, str) and item in {"accident_type", "signal_state", "injury", "opponent_behavior", "damage_level"} else scrub_user_text(item)
            if text and text not in items: items.append(text)
        return {"items": items[:6], "questions": required_questions[:6]}

    def _shorten(self, text: str, max_len: int = 150) -> str:
        return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def _needs_review(section: dict[str, Any]) -> bool:
    return section.get("judgment_status") in {"needs_review", "unsupported"} or section.get("evidence_support_level") in {"partial", "insufficient"}


def _required_questions(result: dict[str, Any]) -> list[dict[str, Any]]:
    questions = result.get("required_input_questions") or (result.get("input_requirements") or {}).get("questions") or []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in questions:
        if isinstance(item, dict):
            raw_field = str(item.get("field") or "").strip()
            field = raw_field if raw_field in SAFE_QUESTION_FIELDS else ""
            text = scrub_user_text(item.get("question") or item.get("label"))
            label = scrub_user_text(item.get("label") or item.get("field") or text)
            input_type = scrub_user_text(item.get("input_type") or "text")
            options = [scrub_user_text(option) for option in (item.get("options") or []) if scrub_user_text(option)]
        else:
            field = ""
            text = scrub_user_text(item)
            label = text
            input_type = "text"
            options = []
        key = field or text
        if text and key not in seen:
            seen.add(key)
            out.append({
                "field": field,
                "label": label,
                "question": text,
                "input_type": input_type,
                "options": options,
            })
    return out


def _section_notice(section: dict[str, Any], fallback: str) -> str:
    raw = section.get("caveats") or []
    items = [raw] if isinstance(raw, (str, bytes)) else raw
    caveats = [scrub_user_text(item) for item in items if item]
    return caveats[0] if caveats else fallback


def _review_reasons(section: dict[str, Any], existing: list[str]) -> list[str]:
    reasons = list(existing)
    support = section.get("evidence_support_level")
    if support == "insufficient":
        reasons.insert(0, "직접 연결된 근거가 부족하다는 점")
    elif support == "partial":
        reasons.insert(0, "직접 근거가 아닌 간접 근거가 포함되어 있다는 점")
    if section.get("required_evidence_family") == "knia":
        reasons.insert(0, "KNIA 과실비율 기준 확인이 더 필요하다는 점")
    return list(dict.fromkeys(reasons))[:4]
