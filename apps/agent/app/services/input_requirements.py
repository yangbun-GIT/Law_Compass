from __future__ import annotations

from typing import Any


VERSION = "agent-input-requirements-v1"
LOOP_VERSION = "agent-followup-loop-v1"
MAX_FOLLOWUP_ITERATIONS = 3

EMPTY_VALUES = {None, "", "unknown", "모름", "None", "null"}

SIGNAL_RELEVANT_SCENARIOS = {
    "intersection_signal_violation",
    "pedestrian_crosswalk_accident",
    "school_zone_child_accident",
}

BASE_FIELD_SPECS: dict[str, dict[str, Any]] = {
    "accident_type": {
        "label": "사고 유형",
        "question": "어떤 유형의 사고였나요?",
        "reason": "사고 유형이 확정되어야 KNIA 기준과 법률 근거를 안정적으로 고를 수 있습니다.",
        "input_type": "single_choice",
        "options": ["후미추돌", "차선변경", "교차로", "보행자", "자전거", "단독/시설물"],
        "priority": 1,
        "blocks_decision": True,
    },
    "signal_state": {
        "label": "신호 상태",
        "question": "사고 당시 내 차량과 상대방의 신호 상태는 각각 어땠나요?",
        "reason": "교차로, 보행자, 어린이보호구역 사고에서는 신호 상태가 과실과 형사책임 판단의 핵심입니다.",
        "input_type": "single_choice",
        "options": ["내 신호 녹색", "내 신호 적색", "상대 신호위반", "신호등 없음", "확인 중"],
        "priority": 2,
        "blocks_decision": True,
    },
    "injury": {
        "label": "인명피해 여부",
        "question": "다친 사람이 있나요?",
        "reason": "인명피해 여부에 따라 신고, 대인접수, 형사책임 검토가 달라집니다.",
        "input_type": "single_choice",
        "options": ["다친 사람 없음", "내가 다침", "상대방이 다침", "보행자/자전거 운전자가 다침", "확인 중"],
        "priority": 1,
        "blocks_decision": True,
    },
    "opponent_behavior": {
        "label": "상대방 행동",
        "question": "충돌 직전 상대방은 어떤 행동을 했나요?",
        "reason": "상대방의 후방추돌, 차선변경, 신호위반, 급정거 여부가 과실 산정의 기준점입니다.",
        "input_type": "single_choice",
        "options": ["뒤에서 추돌", "차선변경", "신호위반", "급정거", "후진/출차", "확인 중"],
        "priority": 1,
        "blocks_decision": True,
    },
    "damage_level": {
        "label": "차량 손상 정도",
        "question": "차량 파손 정도는 어느 정도인가요?",
        "reason": "보험 접수, 수리 견적, 추가 증빙 안내를 정하기 위해 필요합니다.",
        "input_type": "single_choice",
        "options": ["경미한 흠집", "수리 필요", "견인 필요", "폐차 수준", "확인 중"],
        "priority": 4,
        "blocks_decision": False,
    },
}

SCENARIO_FIELD_SPECS: dict[str, list[dict[str, Any]]] = {
    "rear_end_collision": [
        {
            "field": "stopped",
            "label": "정차 여부",
            "question": "내 차량은 사고 직전에 완전히 정차 중이었나요, 주행 중 감속 또는 급정거 중이었나요?",
            "reason": "정차 중 후방추돌인지 급정거 후 추돌인지에 따라 과실비율이 크게 달라집니다.",
            "input_type": "single_choice",
            "options": ["완전히 정차 중", "서행/감속 중", "급정거 직후", "확인 중"],
            "priority": 1,
            "blocks_decision": True,
        },
        {
            "field": "sudden_brake",
            "label": "급정거 사유",
            "question": "급정거가 있었다면 보행자, 앞차 정체, 신호 등 불가피한 이유가 있었나요?",
            "reason": "불가피한 급정거인지 여부는 앞차 과실 가감요소입니다.",
            "input_type": "single_choice",
            "options": ["급정거 없음", "앞차/정체 때문", "보행자/장애물 때문", "이유 불명"],
            "priority": 3,
            "blocks_decision": False,
        },
    ],
    "lane_change_collision": [
        {
            "field": "lane_change_actor",
            "label": "차선변경 차량",
            "question": "차선을 변경한 차량은 내 차량인가요, 상대 차량인가요?",
            "reason": "차선변경 차량과 직진 차량을 구분해야 KNIA A/B 기준을 사용자 관점으로 변환할 수 있습니다.",
            "input_type": "single_choice",
            "options": ["내 차량", "상대 차량", "둘 다 차선변경", "확인 중"],
            "priority": 1,
            "blocks_decision": True,
        },
        {
            "field": "turn_signal",
            "label": "방향지시등",
            "question": "차선변경 차량이 방향지시등을 켰나요?",
            "reason": "방향지시등 사용 여부는 차선변경 사고의 주요 가감요소입니다.",
            "input_type": "single_choice",
            "options": ["켰음", "켜지 않음", "영상으로 확인 필요"],
            "priority": 2,
            "blocks_decision": True,
        },
    ],
    "intersection_signal_violation": [
        {
            "field": "user_signal",
            "label": "내 진행 신호",
            "question": "내 차량이 교차로에 진입할 때 신호는 무엇이었나요?",
            "reason": "내 신호와 상대 신호를 분리해야 신호위반 책임을 잘못 뒤집지 않습니다.",
            "input_type": "single_choice",
            "options": ["녹색", "황색", "적색", "비보호/점멸", "확인 중"],
            "priority": 0,
            "blocks_decision": True,
        },
        {
            "field": "opponent_signal",
            "label": "상대 진행 신호",
            "question": "상대 차량이 교차로에 진입할 때 신호는 무엇이었나요?",
            "reason": "상대 신호위반 여부가 과실비율과 형사책임 판단의 핵심입니다.",
            "input_type": "single_choice",
            "options": ["녹색", "황색", "적색", "비보호/점멸", "확인 중"],
            "priority": 0,
            "blocks_decision": True,
        },
    ],
    "pedestrian_crosswalk_accident": [
        {
            "field": "crosswalk_nearby",
            "label": "횡단보도 여부",
            "question": "사고 지점이 횡단보도 위 또는 횡단보도 근처였나요?",
            "reason": "횡단보도 여부는 보행자 보호의무와 운전자 책임 판단의 핵심입니다.",
            "input_type": "single_choice",
            "options": ["횡단보도 위", "횡단보도 근처", "횡단보도 아님", "확인 중"],
            "priority": 1,
            "blocks_decision": True,
        },
        {
            "field": "pedestrian_signal",
            "label": "보행자 신호",
            "question": "보행자 신호는 녹색이었나요, 적색이었나요?",
            "reason": "보행자 신호 상태는 운전자와 보행자 과실 판단에 직접 영향을 줍니다.",
            "input_type": "single_choice",
            "options": ["보행자 녹색", "보행자 적색", "신호등 없음", "확인 중"],
            "priority": 2,
            "blocks_decision": True,
        },
    ],
    "school_zone_child_accident": [
        {
            "field": "school_zone",
            "label": "어린이보호구역 여부",
            "question": "사고 지점이 어린이보호구역 표지나 노면 표시가 있는 구역이었나요?",
            "reason": "어린이보호구역 여부는 특례법과 신고 필요성 판단에 직접 연결됩니다.",
            "input_type": "single_choice",
            "options": ["어린이보호구역 맞음", "아님", "표지 확인 필요"],
            "priority": 1,
            "blocks_decision": True,
        },
        {
            "field": "victim_is_child",
            "label": "어린이 피해자 여부",
            "question": "피해자가 만 13세 미만 어린이인가요?",
            "reason": "피해자 연령은 어린이보호구역 사고의 형사책임 검토에 중요합니다.",
            "input_type": "single_choice",
            "options": ["만 13세 미만", "만 13세 이상", "확인 중"],
            "priority": 1,
            "blocks_decision": True,
        },
    ],
    "bicycle_collision": [
        {
            "field": "bicycle_location",
            "label": "자전거 주행 위치",
            "question": "자전거는 차도, 자전거도로, 횡단보도 중 어디를 지나고 있었나요?",
            "reason": "자전거의 주행 위치에 따라 적용 기준과 과실 가감요소가 달라집니다.",
            "input_type": "single_choice",
            "options": ["차도", "자전거도로", "횡단보도", "보도", "확인 중"],
            "priority": 1,
            "blocks_decision": True,
        },
        {
            "field": "bicycle_direction",
            "label": "자전거 진행 방향",
            "question": "자전거와 차량은 같은 방향이었나요, 교차하거나 마주 오는 방향이었나요?",
            "reason": "진행 방향은 충돌 유형과 과실 기준 매칭에 필요합니다.",
            "input_type": "single_choice",
            "options": ["같은 방향", "교차 진행", "마주 오는 방향", "확인 중"],
            "priority": 2,
            "blocks_decision": True,
        },
    ],
}

TEXT_SIGNALS: dict[str, tuple[str, ...]] = {
    "accident_type": ("추돌", "차선변경", "교차로", "횡단보도", "보행자", "자전거", "시설물", "단독"),
    "signal_state": ("신호", "빨간불", "적색", "녹색", "초록불", "황색", "점멸"),
    "injury": ("다쳤", "부상", "통증", "진단", "대인", "인명피해", "다친 사람 없음", "부상 없음"),
    "opponent_behavior": ("상대", "뒤에서", "추돌", "끼어", "차선변경", "신호위반", "급정거", "후진", "출차"),
    "damage_level": ("파손", "수리", "견인", "범퍼", "찌그러", "폐차"),
    "stopped": ("정차", "신호대기", "멈춰", "주차"),
    "sudden_brake": ("급정거", "갑자기 멈", "제동"),
    "lane_change_actor": ("차선변경", "끼어", "진로변경"),
    "turn_signal": ("방향지시", "깜빡", "깜박"),
    "user_signal": ("내 신호", "제 신호", "녹색", "초록불", "적색", "빨간불"),
    "opponent_signal": ("상대 신호", "상대방 신호", "신호위반", "빨간불"),
    "crosswalk_nearby": ("횡단보도", "보행자"),
    "pedestrian_signal": ("보행자 신호", "횡단 신호"),
    "school_zone": ("어린이보호구역", "스쿨존", "학교 앞"),
    "victim_is_child": ("어린이", "아이", "초등학생", "만 13세"),
    "bicycle_location": ("자전거도로", "횡단보도", "차도", "보도"),
    "bicycle_direction": ("같은 방향", "마주", "교차", "직진", "좌회전", "우회전"),
}


def build_input_requirements(
    *,
    facts: dict[str, Any] | None,
    scenario_type: str,
    missing_fields: list[str] | None,
    description_text: str = "",
    accident_party_type: str | None = None,
    max_questions: int = 8,
) -> dict[str, Any]:
    fact_map = facts or {}
    text = description_text or ""
    questions: list[dict[str, Any]] = []
    seen: set[str] = set()

    for field in missing_fields or []:
        if _skip_base_missing_field(str(field), fact_map, scenario_type, accident_party_type):
            continue
        spec = _base_spec_for_field(str(field), scenario_type)
        if _is_satisfied(str(field), fact_map, text, scenario_type):
            continue
        _append_question(questions, seen, field=str(field), spec=spec, source="base_required")

    for raw in SCENARIO_FIELD_SPECS.get(scenario_type, []):
        field = str(raw["field"])
        if _is_satisfied(field, fact_map, text, scenario_type):
            continue
        _append_question(questions, seen, field=field, spec=raw, source="scenario_required")

    questions.sort(key=lambda item: (int(item.get("priority", 9)), 0 if item.get("blocks_decision") else 1, item["field"]))
    questions = questions[:max_questions]
    blocking_fields = [item["field"] for item in questions if item.get("blocks_decision")]
    optional_fields = [item["field"] for item in questions if not item.get("blocks_decision")]
    return {
        "version": VERSION,
        "scenario_type": scenario_type,
        "accident_party_type": accident_party_type or "unknown",
        "blocking_fields": blocking_fields,
        "optional_fields": optional_fields,
        "questions": questions,
        "question_texts": [str(item["question"]) for item in questions],
        "summary": _summary(blocking_fields, optional_fields),
    }


def input_question_texts(input_requirements: dict[str, Any] | None) -> list[str]:
    if not input_requirements:
        return []
    texts = input_requirements.get("question_texts")
    if isinstance(texts, list) and texts:
        return [str(item) for item in texts if str(item).strip()]
    out: list[str] = []
    for item in input_requirements.get("questions") or []:
        if isinstance(item, dict) and item.get("question"):
            out.append(str(item["question"]))
    return out


def build_followup_loop_state(input_requirements: dict[str, Any], facts: dict[str, Any] | None) -> dict[str, Any]:
    fact_map = facts or {}
    blocking_fields = list(input_requirements.get("blocking_fields") or [])
    optional_fields = list(input_requirements.get("optional_fields") or [])
    remaining_fields = [*blocking_fields, *optional_fields]
    iteration = _as_int(fact_map.get("_followup_iteration"), 0)
    answered_fields = _string_list(fact_map.get("_followup_answered_fields"))
    unresolved_fields = _string_list(fact_map.get("_followup_unresolved_fields"))
    if not remaining_fields:
        status = "complete"
        stop_reason = "required_inputs_resolved"
    elif iteration >= MAX_FOLLOWUP_ITERATIONS:
        status = "stopped"
        stop_reason = "max_iterations_reached"
    elif not answered_fields and not unresolved_fields:
        status = "waiting_for_input"
        stop_reason = "awaiting_first_followup"
    elif not blocking_fields:
        status = "optional_followup_available"
        stop_reason = "blocking_inputs_resolved"
    else:
        status = "continue"
        stop_reason = "blocking_inputs_remaining"
    return {
        "version": LOOP_VERSION,
        "status": status,
        "iteration": iteration,
        "max_iterations": MAX_FOLLOWUP_ITERATIONS,
        "stop_reason": stop_reason,
        "answered_fields": answered_fields,
        "unresolved_fields": unresolved_fields,
        "remaining_blocking_fields": blocking_fields,
        "remaining_optional_fields": optional_fields,
        "remaining_question_count": len(remaining_fields),
        "can_request_more_input": status in {"waiting_for_input", "continue", "optional_followup_available"},
    }


def _base_spec_for_field(field: str, scenario_type: str) -> dict[str, Any]:
    spec = dict(BASE_FIELD_SPECS.get(field) or _unknown_spec(field))
    if field == "signal_state" and scenario_type not in SIGNAL_RELEVANT_SCENARIOS:
        spec["priority"] = 5
        spec["blocks_decision"] = False
        spec["reason"] = "신호가 사고 상황에 영향을 준 경우에만 과실 판단 보조 정보로 사용합니다."
    if field == "damage_level":
        spec["blocks_decision"] = False
    return spec


def _skip_base_missing_field(
    field: str,
    facts: dict[str, Any],
    scenario_type: str,
    accident_party_type: str | None,
) -> bool:
    if field == "injury" and accident_party_type == "car_vs_car":
        return True
    if field == "signal_state" and scenario_type not in SIGNAL_RELEVANT_SCENARIOS:
        return True
    if field == "signal_state" and scenario_type == "intersection_signal_violation":
        return any(
            not _is_empty(facts.get(candidate))
            for candidate in ("user_signal", "opponent_signal", "signal_transition", "opponent_signal_visible")
        )
    if field == "opponent_behavior" and scenario_type == "parking_or_stopped_vehicle_accident":
        return any(
            not _is_empty(facts.get(candidate))
            for candidate in (
                "collision_partner_type",
                "primary_collision_target",
                "centerline_crossed",
                "stopped_vehicle_without_lights",
                "opposing_vehicle_present",
            )
        )
    return False


def _unknown_spec(field: str) -> dict[str, Any]:
    label = field.replace("_", " ")
    return {
        "label": label,
        "question": f"{label} 정보를 입력해 주세요.",
        "reason": "Agent 판단을 확정 표현으로 내보내기 전에 필요한 사고 사실입니다.",
        "input_type": "text",
        "options": [],
        "priority": 3,
        "blocks_decision": True,
    }


def _append_question(
    questions: list[dict[str, Any]],
    seen: set[str],
    *,
    field: str,
    spec: dict[str, Any],
    source: str,
) -> None:
    if field in seen:
        return
    seen.add(field)
    questions.append(
        {
            "field": field,
            "label": spec.get("label") or field.replace("_", " "),
            "question": spec.get("question") or f"{field.replace('_', ' ')} 정보를 입력해 주세요.",
            "reason": spec.get("reason") or "판단 정확도를 높이기 위해 필요한 정보입니다.",
            "input_type": spec.get("input_type") or "text",
            "options": list(spec.get("options") or []),
            "priority": int(spec["priority"]) if spec.get("priority") is not None else 5,
            "blocks_decision": bool(spec.get("blocks_decision")),
            "source": source,
        }
    )


def _is_satisfied(field: str, facts: dict[str, Any], text: str, scenario_type: str) -> bool:
    if not _is_empty(facts.get(field)):
        return True
    if scenario_type == "intersection_signal_violation" and field in {"user_signal", "opponent_signal", "opponent_signal_violation"}:
        return False
    if field == "accident_type" and scenario_type not in {"general_collision", "general_vehicle_collision", "unknown"}:
        return True
    if scenario_type == "rear_end_collision" and field == "opponent_behavior":
        if any(keyword in text for keyword in ("뒤에서", "후미", "뒷차", "추돌당", "받혔", "받힘")):
            return True
    if scenario_type == "rear_end_collision" and field == "stopped":
        if any(keyword in text for keyword in ("정차", "신호대기", "멈춰", "주차")):
            return True
    haystack = text.lower()
    return any(keyword.lower() in haystack for keyword in TEXT_SIGNALS.get(field, ()))


def _is_empty(value: Any) -> bool:
    if isinstance(value, (dict, list, set, tuple)):
        return len(value) == 0
    if value in EMPTY_VALUES:
        return True
    if isinstance(value, str) and value.strip() in EMPTY_VALUES:
        return True
    return False


def _summary(blocking_fields: list[str], optional_fields: list[str]) -> str:
    if blocking_fields:
        return f"확정 표현을 피해야 하는 필수 확인 항목 {len(blocking_fields)}개가 남아 있습니다."
    if optional_fields:
        return f"판단 보강에 도움이 되는 추가 확인 항목 {len(optional_fields)}개가 있습니다."
    return "현재 입력만으로 필수 확인 항목은 충족된 상태입니다."


def _as_int(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [str(value)] if str(value).strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]
