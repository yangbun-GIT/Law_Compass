from __future__ import annotations

from typing import Any

from app.services.analysis_modes import normalize_analysis_mode


VERSION = "agent-dynamic-questionnaire-v1"
UNKNOWN_CHOICE = {"value": "unknown", "label": "잘 모르겠어요"}


def _choice(value: str, label: str) -> dict[str, str]:
    return {"value": value, "label": label}


def _yes_no_unknown() -> list[dict[str, str]]:
    return [_choice("yes", "예"), _choice("no", "아니오"), UNKNOWN_CHOICE]


def _question(
    *,
    question_id: str,
    title: str,
    plain_question: str,
    why_it_matters: str,
    choices: list[dict[str, str]] | None = None,
    default_choice: str = "unknown",
    affects_fault_ratio: bool = False,
    knia_factor_key: str | None = None,
    fact_key: str | None = None,
    priority: int = 5,
    required_for_modes: list[str] | None = None,
    source: str = "scenario_template",
    examples: list[str] | None = None,
) -> dict[str, Any]:
    final_choices = choices or _yes_no_unknown()
    if not any(choice.get("value") == "unknown" for choice in final_choices):
        final_choices = [*final_choices, UNKNOWN_CHOICE]
    return {
        "question_id": question_id,
        "title": title,
        "plain_question": plain_question,
        "why_it_matters": why_it_matters,
        "choices": final_choices,
        "default_choice": default_choice,
        "affects_fault_ratio": affects_fault_ratio,
        "knia_factor_key": knia_factor_key,
        "fact_key": fact_key or knia_factor_key or question_id.split(".")[-1],
        "priority": priority,
        "required_for_modes": required_for_modes or ["fault_ratio_focused", "full_deep_research"],
        "source": source,
        "examples": examples or [],
    }


REAR_END_QUESTIONS = [
    _question(
        question_id="rear_end.user_vehicle_role",
        title="내 차량 위치",
        plain_question="사용자는 앞차였나요, 뒤차였나요?",
        why_it_matters="후미추돌은 앞차인지 뒤차인지에 따라 기본 과실 출발점이 달라집니다.",
        choices=[_choice("front_vehicle", "앞차였습니다"), _choice("following_vehicle", "뒤차였습니다"), UNKNOWN_CHOICE],
        affects_fault_ratio=True,
        fact_key="user_vehicle_role",
        priority=0,
        required_for_modes=["quick_summary", "fault_ratio_focused", "full_deep_research"],
    ),
    _question(
        question_id="rear_end.stopped",
        title="정차 여부",
        plain_question="내 차가 사고 직전에 완전히 멈춰 있었나요?",
        why_it_matters="정상적으로 멈춰 있던 앞차를 뒤차가 들이받은 사고라면 뒤차의 안전거리 미확보 책임을 크게 봅니다.",
        affects_fault_ratio=True,
        knia_factor_key="front_vehicle_stopped",
        fact_key="stopped",
        priority=1,
        required_for_modes=["quick_summary", "fault_ratio_focused", "full_deep_research"],
    ),
    _question(
        question_id="rear_end.stop_reason",
        title="정차한 이유",
        plain_question="왜 멈춰 있었나요?",
        why_it_matters="빨간불 신호대기, 정체, 보행자 회피처럼 정당한 정차 사유가 있으면 앞차 과실을 올리지 않는 쪽으로 봅니다.",
        choices=[
            _choice("red_light", "빨간불 신호대기"),
            _choice("traffic", "앞차 정체"),
            _choice("pedestrian_or_obstacle", "보행자/장애물 때문에 정지"),
            _choice("no_reason", "이유 없이 갑자기 정지"),
            UNKNOWN_CHOICE,
        ],
        affects_fault_ratio=True,
        knia_factor_key="lawful_stop_reason",
        fact_key="stop_reason",
        priority=2,
        required_for_modes=["quick_summary", "fault_ratio_focused", "full_deep_research"],
    ),
    _question(
        question_id="rear_end.sudden_brake",
        title="급정거 여부",
        plain_question="내 차가 아주 갑자기 멈췄나요?",
        why_it_matters="이유 없이 급하게 멈췄다면 내 과실이 일부 생길 수 있습니다.",
        affects_fault_ratio=True,
        knia_factor_key="sudden_brake_without_reason",
        fact_key="sudden_brake",
        priority=3,
    ),
    _question(
        question_id="rear_end.sudden_brake_reason",
        title="급정거 사유",
        plain_question="급정거가 있었다면 이유가 무엇이었나요?",
        why_it_matters="정당한 정차 사유인지, 이유 없는 급정거인지에 따라 앞차 과실 가산 여부가 달라집니다.",
        choices=[
            _choice("red_light", "신호대기"),
            _choice("traffic", "정체"),
            _choice("pedestrian_or_obstacle", "보행자/장애물 회피"),
            _choice("no_reason", "이유 없음"),
            UNKNOWN_CHOICE,
        ],
        affects_fault_ratio=True,
        knia_factor_key="sudden_brake_without_reason",
        fact_key="sudden_brake_reason",
        priority=4,
    ),
    _question(
        question_id="rear_end.brake_light",
        title="브레이크등",
        plain_question="브레이크등이 정상적으로 켜졌나요?",
        why_it_matters="브레이크등이 고장 나 있었다면 뒤차가 정지를 알아보기 어려워 내 과실이 일부 생길 수 있습니다.",
        choices=[_choice("normal", "정상 작동"), _choice("failed", "고장 또는 미점등"), UNKNOWN_CHOICE],
        affects_fault_ratio=True,
        knia_factor_key="brake_light_failure",
        fact_key="brake_light",
        priority=5,
    ),
    _question(
        question_id="rear_end.normal_lane",
        title="정차 위치",
        plain_question="정상 차로에서 멈춰 있었나요?",
        why_it_matters="도로 한가운데 비정상 정차나 불법 주정차 상태였다면 앞차 과실이 일부 올라갈 수 있습니다.",
        choices=[_choice("normal_lane", "정상 차로"), _choice("abnormal_stop", "비정상 정차/불법 주정차"), UNKNOWN_CHOICE],
        affects_fault_ratio=True,
        knia_factor_key="abnormal_stop_position",
        fact_key="abnormal_stop_position",
        priority=6,
    ),
    _question(
        question_id="rear_end.visibility",
        title="야간/시야",
        plain_question="사고 당시 야간이거나 시야가 좋지 않았나요?",
        why_it_matters="야간, 시야장애, 무등화 여부는 정차 차량 발견 가능성과 과실 조정에 영향을 줍니다.",
        choices=[_choice("night_dark", "야간 또는 어두운 곳"), _choice("low_visibility", "비·안개 등 시야장애"), _choice("clear", "시야 양호"), UNKNOWN_CHOICE],
        affects_fault_ratio=True,
        fact_key="visibility_condition",
        priority=7,
    ),
    _question(
        question_id="rear_end.video_evidence",
        title="영상 자료",
        plain_question="블랙박스나 CCTV로 정차 사유와 브레이크등을 확인할 수 있나요?",
        why_it_matters="영상 자료가 있으면 급정거, 제동등, 안전거리 쟁점을 더 좁힐 수 있습니다.",
        choices=[_choice("blackbox", "블랙박스 있음"), _choice("cctv", "CCTV 가능"), _choice("none", "없음"), UNKNOWN_CHOICE],
        fact_key="rear_end_video_evidence",
        priority=8,
    ),
    _question(
        question_id="rear_end.safe_distance",
        title="뒤차 안전거리",
        plain_question="뒤차가 내 차와 너무 가까이 따라오고 있었나요?",
        why_it_matters="뒤차의 안전거리 미확보는 상대 과실을 높이는 요소입니다.",
        affects_fault_ratio=True,
        knia_factor_key="following_vehicle_safe_distance",
        fact_key="following_vehicle_safe_distance",
        priority=9,
    ),
]


SCENARIO_QUESTIONS: dict[str, list[dict[str, Any]]] = {
    "rear_end_collision": REAR_END_QUESTIONS,
    "intersection_signal_violation": [
        _question(question_id="signal.who_entered_red", title="빨간불 진입 차량", plain_question="누가 빨간불에 교차로로 들어갔나요?", why_it_matters="신호를 위반해 진입한 차량이 과실 판단의 출발점입니다.", choices=[_choice("me", "내 차"), _choice("opponent", "상대 차"), _choice("both", "둘 다 가능성 있음"), UNKNOWN_CHOICE], affects_fault_ratio=True, priority=1, required_for_modes=["quick_summary", "fault_ratio_focused", "legal_precedent_focused", "full_deep_research"]),
        _question(question_id="signal.user_signal", title="내 신호", plain_question="내 차가 진입할 때 신호는 무엇이었나요?", why_it_matters="내 신호와 상대 신호를 분리해야 신호위반 책임을 잘못 뒤집지 않습니다.", choices=[_choice("green", "녹색"), _choice("yellow", "황색"), _choice("red", "적색"), UNKNOWN_CHOICE], affects_fault_ratio=True, fact_key="user_signal", priority=2),
        _question(question_id="signal.opponent_signal_visible", title="상대 신호 확인", plain_question="상대 차량 신호를 확인할 수 있나요?", why_it_matters="상대 신호가 확인되어야 신호위반 주장 가능성을 좁힐 수 있습니다.", choices=[_choice("visible", "확인 가능"), _choice("not_visible", "확인 불가"), UNKNOWN_CHOICE], fact_key="opponent_signal_visible", priority=3),
        _question(question_id="signal.entry_order", title="진입 순서", plain_question="누가 교차로에 먼저 진입했나요?", why_it_matters="선진입 여부는 신호와 함께 교차로 과실비율을 조정하는 요소입니다.", choices=[_choice("me_first", "내 차 먼저"), _choice("opponent_first", "상대 먼저"), _choice("same_time", "동시 진입"), UNKNOWN_CHOICE], fact_key="intersection_entry_order", priority=4),
        _question(question_id="signal.direction", title="진행 방향", plain_question="각 차량은 어떤 방향으로 진행했나요?", why_it_matters="직진, 좌회전, 우회전 관계에 따라 적용 기준이 달라집니다.", choices=[_choice("straight_vs_left", "직진 대 좌회전"), _choice("crossing", "교차 진행"), _choice("same_direction", "같은 방향"), UNKNOWN_CHOICE], fact_key="intersection_movement", priority=5),
        _question(question_id="signal.video_visible", title="CCTV/신호주기표", plain_question="CCTV나 신호주기표를 확인할 수 있나요?", why_it_matters="영상에 신호가 보이면 보험사와 분쟁심의에서 훨씬 명확하게 설명할 수 있습니다.", fact_key="signal_evidence_available", priority=6, required_for_modes=["legal_precedent_focused", "full_deep_research"]),
    ],
    "lane_change_collision": [
        _question(question_id="lane.actor", title="차선변경 차량", plain_question="누가 차선을 바꿨나요?", why_it_matters="차선을 바꾼 차량과 직진 차량을 구분해야 KNIA 기준을 맞게 적용할 수 있습니다.", choices=[_choice("me", "내 차"), _choice("opponent", "상대 차"), _choice("both", "둘 다"), UNKNOWN_CHOICE], affects_fault_ratio=True, fact_key="lane_change_actor", priority=1),
        _question(question_id="lane.turn_signal", title="방향지시등", plain_question="차선을 바꾼 차량이 방향지시등을 켰나요?", why_it_matters="방향지시등 사용 여부는 차선변경 사고의 주요 가감요소입니다.", affects_fault_ratio=True, knia_factor_key="turn_signal", fact_key="turn_signal", priority=2),
        _question(question_id="lane.impact_position", title="충돌 부위", plain_question="충돌 부위는 어느 쪽이었나요?", why_it_matters="충돌 부위는 선진입과 회피 가능성을 판단하는 데 중요합니다.", choices=[_choice("front_side", "앞쪽/앞문"), _choice("middle_side", "옆면 중앙"), _choice("rear_side", "뒤쪽/뒷문"), UNKNOWN_CHOICE], fact_key="impact_position", priority=3),
        _question(question_id="lane.first_entry", title="선진입", plain_question="차선변경 차량이 이미 차로에 상당히 들어와 있었나요?", why_it_matters="선진입 여부는 차선변경 차량과 직진 차량 책임 배분에 영향을 줍니다.", choices=[_choice("lane_changer_first", "차선변경 차량 선진입"), _choice("straight_vehicle_first", "직진 차량 우선"), UNKNOWN_CHOICE], fact_key="lane_change_first_entry", priority=4),
        _question(question_id="lane.speed_difference", title="속도 차이", plain_question="두 차량 사이 속도 차이가 컸나요?", why_it_matters="급차로변경이나 고속 접근 여부는 회피 가능성 판단에 영향을 줍니다.", choices=[_choice("large", "컸습니다"), _choice("small", "크지 않았습니다"), UNKNOWN_CHOICE], fact_key="speed_difference", priority=5),
        _question(question_id="lane.solid_line", title="차선 종류", plain_question="실선 구간이었나요, 점선 구간이었나요?", why_it_matters="실선에서 차선을 바꾸면 차선변경 차량 책임이 더 커질 수 있습니다.", choices=[_choice("solid", "실선"), _choice("dashed", "점선"), UNKNOWN_CHOICE], affects_fault_ratio=True, fact_key="lane_marking", priority=6),
    ],
    "bicycle_collision": [
        _question(question_id="bicycle.role", title="사용자 위치", plain_question="사용자는 차량 운전자였나요, 자전거 운전자였나요?", why_it_matters="차량과 자전거 중 어느 쪽 관점인지에 따라 과실비율 설명이 달라집니다.", choices=[_choice("car_driver", "차량 운전자"), _choice("bicycle_rider", "자전거 운전자"), UNKNOWN_CHOICE], priority=1),
        _question(question_id="bicycle.location", title="자전거 위치", plain_question="자전거는 어디를 지나고 있었나요?", why_it_matters="자전거도로, 차도, 횡단보도 여부에 따라 적용 기준이 달라집니다.", choices=[_choice("bike_lane", "자전거도로"), _choice("road", "차도"), _choice("crosswalk", "횡단보도"), _choice("sidewalk", "인도"), UNKNOWN_CHOICE], affects_fault_ratio=True, priority=2),
        _question(question_id="bicycle.light", title="야간 등화", plain_question="밤이거나 어두운 상황에서 자전거 등이 켜져 있었나요?", why_it_matters="야간 무등화는 자전거 쪽 과실 가감요소가 될 수 있습니다.", affects_fault_ratio=True, priority=3),
    ],
    "pedestrian_crosswalk_accident": [
        _question(question_id="ped.crosswalk", title="횡단보도", plain_question="보행자가 횡단보도 위 또는 바로 근처에 있었나요?", why_it_matters="횡단보도 사고는 운전자의 보호의무가 더 강하게 문제 됩니다.", affects_fault_ratio=True, priority=1),
        _question(question_id="ped.signal", title="보행자 신호", plain_question="보행자 신호는 무엇이었나요?", why_it_matters="보행자 신호와 차량 신호가 보행자 사고의 핵심 판단 기준입니다.", choices=[_choice("green", "보행자 녹색"), _choice("red", "보행자 적색"), _choice("none", "신호등 없음"), UNKNOWN_CHOICE], affects_fault_ratio=True, priority=2),
        _question(question_id="ped.child_zone", title="어린이보호구역", plain_question="어린이보호구역인가요?", why_it_matters="어린이보호구역이면 신고와 법률 쟁점이 더 중요해질 수 있습니다.", priority=3),
    ],
    "motorcycle_collision": [
        _question(question_id="motorcycle.location", title="이륜차 위치", plain_question="오토바이 또는 이륜차는 어느 위치에서 진행 중이었나요?", why_it_matters="차로, 교차로, 갓길 주행 여부에 따라 적용 기준이 달라집니다.", choices=[_choice("roadway", "차로"), _choice("intersection", "교차로"), _choice("shoulder", "갓길"), UNKNOWN_CHOICE], affects_fault_ratio=True, fact_key="motorcycle_location", priority=1),
        _question(question_id="motorcycle.movement", title="진행 방향", plain_question="차량과 이륜차의 진행 방향은 어땠나요?", why_it_matters="같은 방향, 교차 진행, 진로변경 여부에 따라 과실 판단이 달라집니다.", choices=[_choice("same_direction", "같은 방향"), _choice("crossing", "교차 진행"), _choice("lane_change", "진로변경"), UNKNOWN_CHOICE], fact_key="motorcycle_movement", priority=2),
    ],
    "parking_or_stopped_vehicle_accident": [
        _question(question_id="parking.position", title="주정차 위치", plain_question="상대 차량은 어디에 정차 또는 주차되어 있었나요?", why_it_matters="정상 주차구역인지, 통행 공간인지에 따라 상대 과실이 달라집니다.", choices=[_choice("normal_parking", "정상 주차구역"), _choice("traffic_space", "통행 공간"), _choice("under_bridge", "교량 아래"), _choice("roadside", "갓길/도로 가장자리"), UNKNOWN_CHOICE], fact_key="parked_vehicle_position", priority=1),
        _question(question_id="parking.lighting", title="등화/비상등", plain_question="상대 차량의 미등, 비상등, 차폭등이 켜져 있었나요?", why_it_matters="야간 무등화는 발견 가능성과 상대 과실 가산의 핵심입니다.", choices=[_choice("all_lights_on", "식별 가능"), _choice("hazard_only", "비상등만"), _choice("unlit_stealth", "등화 없음"), UNKNOWN_CHOICE], fact_key="parked_vehicle_lighting", priority=2),
        _question(question_id="parking.visibility", title="야간/조도", plain_question="야간, 교량 아래, 조도 불량처럼 보기 어려웠나요?", why_it_matters="시야 조건은 회피 가능성과 과실 조정에 영향을 줍니다.", choices=[_choice("under_bridge_dark", "교량 아래 어두움"), _choice("night_dark", "야간 어두움"), _choice("clear", "시야 양호"), UNKNOWN_CHOICE], fact_key="visibility_condition", priority=3),
        _question(question_id="parking.impairment", title="음주운전 여부", plain_question="상대 차량의 음주운전 또는 비정상 정차 원인이 확인되나요?", why_it_matters="음주운전은 민사 100:0 자동 확정은 아니지만 위험 상태를 만든 가산 요소입니다.", choices=[_choice("drunk_driving_confirmed", "음주운전 확인"), _choice("suspected_drunk", "의심"), _choice("not_drunk", "아님"), UNKNOWN_CHOICE], fact_key="opponent_impairment", priority=4),
        _question(question_id="parking.avoidability", title="회피 가능성", plain_question="발견한 뒤 피하거나 멈출 시간이 있었나요?", why_it_matters="회피 가능성이 낮을수록 내 과실을 낮추는 근거가 됩니다.", choices=[_choice("nearly_impossible", "거의 불가능"), _choice("limited", "제한적"), _choice("avoidable", "가능"), UNKNOWN_CHOICE], fact_key="avoidability", priority=5),
        _question(question_id="parking.speed", title="내 차량 속도", plain_question="내 차량 속도가 제한속도 이내였나요?", why_it_matters="과속이 확인되면 내 과실이 증가할 수 있습니다.", choices=[_choice("within_limit", "제한속도 이내"), _choice("speeding", "과속 가능성"), UNKNOWN_CHOICE], fact_key="speed_context", priority=6),
    ],
}

SCENARIO_QUESTIONS["stealth_illegal_parked_vehicle_collision"] = SCENARIO_QUESTIONS["parking_or_stopped_vehicle_accident"]
SCENARIO_QUESTIONS["intersection_collision"] = SCENARIO_QUESTIONS["intersection_signal_violation"]


MODE_QUESTION_LIMITS = {
    "quick_summary": 3,
    "fault_ratio_focused": 10,
    "legal_precedent_focused": 6,
    "insurance_response_focused": 5,
    "full_deep_research": 12,
}


def build_dynamic_questionnaire(
    *,
    scenario_type: str,
    accident_party_type: str | None,
    analysis_mode: str | None,
    description_text: str = "",
    structured_facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    video_observations: dict[str, Any] | None = None,
    matched_knia_chart: dict[str, Any] | None = None,
    knia_adjustment_factors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    mode = normalize_analysis_mode(analysis_mode)
    questions = list(SCENARIO_QUESTIONS.get(scenario_type) or [])
    questions.extend(_questions_from_knia_factors(knia_adjustment_factors or [], existing_ids={q["question_id"] for q in questions}))
    filtered = [
        q for q in questions
        if mode in set(q.get("required_for_modes") or []) or mode == "full_deep_research"
    ]
    filtered.sort(key=lambda item: (int(item.get("priority", 9)), item.get("question_id", "")))
    limit = MODE_QUESTION_LIMITS.get(mode, 6)
    selected = filtered[:limit]
    return {
        "version": VERSION,
        "scenario_type": scenario_type,
        "accident_party_type": accident_party_type or "unknown",
        "analysis_mode": mode,
        "question_count": len(selected),
        "questions": selected,
        "auto_analysis_policy": {
            "can_auto_start_when_required_answered": True,
            "user_controls": ["이대로 분석하기", "답변 더 추가하기"],
            "batch_size_hint": 3 if mode != "quick_summary" else 2,
        },
        "source_context": {
            "description_present": bool((description_text or "").strip()),
            "selected_keyword_count": len(selected_keywords or []),
            "video_observation_present": bool(video_observations),
            "matched_knia_chart_no": (matched_knia_chart or {}).get("chart_no"),
        },
    }


def _questions_from_knia_factors(factors: list[dict[str, Any]], existing_ids: set[str]) -> list[dict[str, Any]]:
    generated: list[dict[str, Any]] = []
    for factor in factors[:8]:
        label = str(factor.get("label") or "").strip()
        if not label:
            continue
        lowered = label.lower()
        if "제동" in label or "브레이크" in label:
            question_id = "knia.brake_light_failure"
            title = "브레이크등"
            question = "브레이크등이 정상적으로 켜졌나요?"
            why = "KNIA 가감요소에 제동등 또는 정지 신호 확인이 포함되어 있어 과실비율에 영향을 줄 수 있습니다."
        elif "급" in label and ("정" in label or "제동" in label):
            question_id = "knia.sudden_brake"
            title = "급정거"
            question = "사고 직전에 이유 없는 급정거가 있었나요?"
            why = "KNIA 원문 가감요소에 급정거 또는 현저한 과실 항목이 있어 확인이 필요합니다."
        elif "야간" in label or "시야" in label or "등화" in label:
            question_id = "knia.visibility"
            title = "시야와 등화"
            question = "밤이거나 시야가 나쁜 상황에서 등화가 충분히 켜져 있었나요?"
            why = "야간, 시야장애, 등화 상태는 과실 조정 요소가 될 수 있습니다."
        elif "방향" in label or "지시" in label:
            question_id = "knia.turn_signal"
            title = "방향지시등"
            question = "방향지시등을 켰나요?"
            why = "방향지시등 사용 여부는 차선변경 또는 진로변경 사고의 주요 가감요소입니다."
        else:
            safe_key = "".join(ch for ch in lowered if ch.isalnum())[:24] or str(len(generated))
            question_id = f"knia.factor.{safe_key}"
            title = label[:24]
            question = f"{label}에 해당하는 사정이 있었나요?"
            why = "KNIA 원문에 표시된 가감요소라 과실비율에 영향을 줄 수 있습니다."
        if question_id in existing_ids:
            continue
        existing_ids.add(question_id)
        generated.append(_question(
            question_id=question_id,
            title=title,
            plain_question=question,
            why_it_matters=why,
            affects_fault_ratio=True,
            knia_factor_key=str(factor.get("condition_code") or label),
            fact_key=str(factor.get("fact_key") or factor.get("condition_code") or question_id.split(".")[-1]),
            priority=7 + len(generated),
            source="knia_adjustment_factor",
        ))
    return generated
