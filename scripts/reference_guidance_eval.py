import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = "logs/video_accuracy/reference_guidance_eval.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class GuidanceEvalError(RuntimeError):
    pass


CRITERIA = [
    {
        "id": "centerline_obstacle",
        "keywords": ["centerline", "central line", "중앙선"],
        "case_fields": ["centerline_crossed", "centerline_cross_reason", "road_type"],
        "video_fields": ["lane_change_actor", "collision_direction"],
        "evidence_requirements": [
            "KNIA/판례에서 중앙선 침범 기본 책임과 장애물 회피 예외를 분리해 확인",
            "상대 차량 회피 가능성과 정차 위치를 추가 사실로 확인",
        ],
        "gap": "중앙선 침범 사유를 별도 fact와 검색 키워드로 유지해야 합리적 과실 범위 평가가 가능합니다.",
    },
    {
        "id": "secondary_collision",
        "keywords": ["secondary", "후속", "2차", "rear after", "뒤차"],
        "case_fields": ["secondary_collision", "opponent_behavior"],
        "video_fields": ["collision_direction", "opponent_behavior"],
        "evidence_requirements": [
            "1차 충돌과 후속 추돌의 책임 주체를 분리해 평가",
            "후방 차량 안전거리 및 정차 후 추돌 기준 확인",
        ],
        "gap": "복합 사고는 단일 과실비율로 합치기 전에 충돌 단계를 분리해야 합니다.",
    },
    {
        "id": "signal_transition",
        "keywords": ["signal", "신호", "황색", "적색", "초록", "cctv"],
        "case_fields": ["signal_state", "signal_transition", "opponent_signal_state", "analysis_uncertainty"],
        "video_fields": ["opponent_signal_violation", "traffic_signal_state"],
        "evidence_requirements": [
            "신호 변경 시점, 교차로 진입 시점, 상대방 신호를 CCTV/신호체계로 확인",
            "신호위반 사고와 신호 변경 직후 진입 사고 기준을 분리해 검색",
        ],
        "gap": "신호 전환 사고는 영상 프레임만으로 확정하기 어려워 CCTV/신호체계 확인 질문이 필수입니다.",
    },
    {
        "id": "crosswalk_pedestrian_signal",
        "keywords": ["crosswalk", "횡단보도", "보행자"],
        "case_fields": ["crosswalk_nearby", "pedestrian_signal", "analysis_uncertainty"],
        "video_fields": ["crosswalk_nearby", "pedestrian_present", "traffic_signal_state"],
        "evidence_requirements": [
            "횡단보도 전 일시정지 의무와 보행자 신호 상태 확인",
            "우회전 중 횡단보도 접근 기준 확인",
        ],
        "gap": "횡단보도 위치와 보행자 신호는 정지 사유 판단의 핵심 fact입니다.",
    },
    {
        "id": "rear_end_default",
        "keywords": ["rear", "후방", "추돌", "안전거리"],
        "case_fields": ["accident_type", "opponent_behavior", "stopped", "sudden_brake"],
        "video_fields": ["stopped", "opponent_behavior", "impact_direction", "collision_direction", "sudden_brake"],
        "evidence_requirements": [
            "정차 또는 감속 차량 후방 추돌의 기본 책임 기준 확인",
            "급정지 사유와 예견 가능성을 감액/가산 요소로 분리",
        ],
        "gap": "후방 추돌 기본 원칙과 급정지 항변 가능성을 동시에 제시해야 합니다.",
    },
    {
        "id": "front_vehicle_stop_reason",
        "keywords": ["front vehicle", "앞차", "정지 사유", "이유 없는", "불가피성"],
        "case_fields": ["front_vehicle_stop_reason", "analysis_uncertainty", "opponent_behavior", "stopped"],
        "video_fields": ["stopped", "opponent_behavior", "sudden_brake"],
        "evidence_requirements": [
            "앞차가 정지한 이유, 보행자/횡단보도/위험 회피 여부 확인",
            "이유 없는 급정지 항변의 인정 가능성 확인",
        ],
        "gap": "앞차 정지 사유가 없으면 100:0과 일부 과실 가능성을 구분하기 어렵습니다.",
    },
    {
        "id": "unlit_stopped_vehicle_visibility",
        "keywords": ["unlit", "lights", "stealth", "무등화", "스텔스", "시인성", "야간"],
        "case_fields": ["stopped_vehicle_without_lights", "light_condition", "opponent_behavior"],
        "video_fields": ["opponent_behavior", "stopped", "visibility_condition"],
        "evidence_requirements": [
            "무등화 정차 차량의 시인성, 도로 조명, 정차 위치 확인",
            "야간 시인성 감정 또는 유사 판례 확인",
        ],
        "gap": "무등화 정차 차량은 단순 후방 추돌이 아니라 시인성과 예견 가능성을 별도 판단해야 합니다.",
    },
    {
        "id": "speed_avoidability",
        "keywords": ["speed", "속도", "회피", "감정", "100km", "141km"],
        "case_fields": ["speed_limit_kmh", "reported_speed_kmh", "analysis_uncertainty"],
        "video_fields": ["speed_estimate", "visibility_condition"],
        "evidence_requirements": [
            "제한속도와 실제 속도, 속도별 회피 가능성 감정 결과 확인",
            "형사상 과실과 민사상 과실비율을 분리",
        ],
        "gap": "속도위반만으로 결론을 내리지 말고 회피 가능성 감정과 연결해야 합니다.",
    },
    {
        "id": "criminal_civil_split",
        "keywords": ["criminal", "civil", "형사", "민사", "무죄", "항소"],
        "case_fields": ["fatality", "known_result", "analysis_uncertainty"],
        "video_fields": [],
        "evidence_requirements": [
            "형사 유무죄 판단과 민사 과실비율 판단의 기준 차이를 설명",
            "사망 사고 대응 안내와 보험 처리 가능성을 분리",
        ],
        "gap": "형사/민사/보험 판단을 같은 결론처럼 표시하면 사용자 오해가 커집니다.",
    },
    {
        "id": "stopped_state",
        "keywords": ["stopped", "정차 여부"],
        "case_fields": ["stopped", "analysis_uncertainty"],
        "video_fields": ["stopped"],
        "evidence_requirements": [
            "정차 위치, 정차 지속 시간, 정차 사유를 사용자 입력과 영상 관찰로 분리 확인",
            "정차 후 추돌인지 주행 중 접촉인지에 따라 KNIA 기준을 다르게 검색",
        ],
        "gap": "정차 여부는 영상이 확인하더라도 정차 사유와 위치가 함께 있어야 과실 범위를 좁힐 수 있습니다.",
    },
    {
        "id": "non_contact_bicycle_trigger",
        "keywords": ["bicycle", "자전거", "비접촉", "유발"],
        "case_fields": ["bicycle_involved", "possible_trigger_vehicle", "opponent_behavior", "analysis_uncertainty"],
        "video_fields": ["bicycle_present", "opponent_behavior", "sudden_brake"],
        "evidence_requirements": [
            "비접촉 유발 차량/자전거의 책임 인정 가능성 확인",
            "직접 충돌 차량과 유발 원인을 분리해 보험/법률 근거 확인",
        ],
        "gap": "비접촉 유발 요인을 별도 party/action fact로 다루어야 합니다.",
    },
    {
        "id": "time_gap_sudden_brake",
        "keywords": ["time", "4초", "시간", "급제동", "급차로"],
        "case_fields": ["time_gap_sec", "sudden_brake", "lane_change_actor", "analysis_uncertainty"],
        "video_fields": ["sudden_brake", "lane_change_actor"],
        "evidence_requirements": [
            "후방 차량이 대응할 수 있었던 시간 간격 확인",
            "급차로변경/급제동 여부와 안전거리 책임을 분리",
        ],
        "gap": "시간적 여유가 없으면 후방 차량 책임과 전방 차량 급정지 항변이 흔들립니다.",
    },
]


# Normalized criteria source of truth. The legacy block above is kept for
# compatibility with older generated outputs, but matching and reports use this
# readable Korean/English criteria set.
CRITERIA = [
    {
        "id": "centerline_obstacle",
        "keywords": ["centerline", "central line", "중앙선", "중앙선 침범", "주차", "장애물"],
        "case_fields": ["centerline_crossed", "centerline_cross_reason", "road_type"],
        "video_fields": ["lane_change_actor", "collision_direction", "impact_direction"],
        "evidence_requirements": [
            "중앙선 침범 기본 책임과 장애물 회피 예외를 KNIA/판례 기준으로 분리 확인",
            "상대 차량의 회피 가능성, 정차 위치, 차로 폭, 장애물 위치를 추가 사실로 확인",
        ],
        "gap": "중앙선 침범 사유를 별도 fact와 검색 쿼리로 유지해야 합리적인 과실 범위 평가가 가능합니다.",
    },
    {
        "id": "secondary_collision",
        "keywords": ["secondary", "2차", "후속", "뒤차", "rear after", "연쇄"],
        "case_fields": ["secondary_collision", "opponent_behavior"],
        "video_fields": ["collision_direction", "impact_direction", "opponent_behavior"],
        "evidence_requirements": [
            "1차 충돌과 후속 추돌의 책임 주체를 분리 평가",
            "후방 차량 안전거리, 정차 후 추돌 기준, 연쇄 충돌의 인과관계를 확인",
        ],
        "gap": "복합 사고는 단일 과실비율로 합치기 전에 충돌 단계를 분리해야 합니다.",
    },
    {
        "id": "signal_transition",
        "keywords": ["signal", "신호", "황색", "적색", "초록", "녹색", "cctv"],
        "case_fields": ["signal_state", "user_signal", "signal_transition", "opponent_signal_state", "analysis_uncertainty"],
        "video_fields": ["opponent_signal_violation", "traffic_signal_state", "user_signal", "opponent_signal_state", "signal_state"],
        "evidence_requirements": [
            "신호 변경 시점, 교차로 진입 시점, 양방향 신호를 CCTV 또는 신호체계 자료로 확인",
            "신호위반 사고와 신호 변경 직후 진입 사고 기준을 분리 검색",
        ],
        "gap": "신호 전환 사고는 영상 프레임만으로 확정하기 어렵기 때문에 CCTV/신호체계 확인 질문이 필수입니다.",
    },
    {
        "id": "crosswalk_pedestrian_signal",
        "keywords": ["crosswalk", "횡단보도", "보행자", "pedestrian"],
        "case_fields": ["crosswalk_nearby", "pedestrian_signal", "analysis_uncertainty"],
        "video_fields": ["crosswalk_nearby", "pedestrian_present", "traffic_signal_state"],
        "evidence_requirements": [
            "횡단보도 앞 일시정지 의무와 보행자 신호 상태 확인",
            "우회전 중 횡단보도 접근 기준과 안전거리 의무 확인",
        ],
        "gap": "횡단보도 위치와 보행자 신호는 정차 사유 판단의 핵심 fact입니다.",
    },
    {
        "id": "rear_end_default",
        "keywords": ["rear", "후방", "추돌", "안전거리", "뒤에서"],
        "case_fields": ["accident_type", "opponent_behavior", "stopped", "sudden_brake"],
        "video_fields": ["stopped", "opponent_behavior", "sudden_brake"],
        "evidence_requirements": [
            "정차 또는 감속 차량 후방 추돌의 기본 책임 기준 확인",
            "급정지 사유와 예견 가능성을 감산/가산 요소로 분리",
        ],
        "gap": "후방 추돌 기본 원칙과 급정지 예외 가능성을 동시에 제시해야 합니다.",
    },
    {
        "id": "front_vehicle_stop_reason",
        "keywords": ["front vehicle", "앞차", "정차 사유", "이유 없는", "불가피성"],
        "case_fields": ["front_vehicle_stop_reason", "analysis_uncertainty", "opponent_behavior", "stopped"],
        "video_fields": ["stopped", "opponent_behavior", "sudden_brake"],
        "evidence_requirements": [
            "앞차가 정차한 이유, 보행자/횡단보도/위험 회피 여부 확인",
            "이유 없는 급정지 항변이 일부 인정될 가능성 확인",
        ],
        "gap": "앞차 정차 사유가 없으면 100:0과 일부 과실 가능성을 구분하기 어렵습니다.",
    },
    {
        "id": "unlit_stopped_vehicle_visibility",
        "keywords": ["unlit", "lights", "stealth", "무등화", "스텔스", "시인성", "야간"],
        "case_fields": ["stopped_vehicle_without_lights", "light_condition", "opponent_behavior"],
        "video_fields": ["opponent_behavior", "stopped", "visibility_condition"],
        "evidence_requirements": [
            "무등화 정차 차량의 시인성, 도로 조명, 정차 위치 확인",
            "야간 시인성 감정 또는 유사 판례 확인",
        ],
        "gap": "무등화 정차 차량은 단순 후방 추돌이 아니라 시인성과 예견 가능성을 별도 판단해야 합니다.",
    },
    {
        "id": "speed_avoidability",
        "keywords": ["speed", "속도", "회피", "감정", "100km", "141km"],
        "case_fields": ["speed_limit_kmh", "reported_speed_kmh", "analysis_uncertainty"],
        "video_fields": ["speed_estimate", "visibility_condition"],
        "evidence_requirements": [
            "제한속도와 실제 속도, 속도별 회피 가능성 감정 결과 확인",
            "형사상 과실과 민사상 과실비율의 판단 기준 차이를 분리",
        ],
        "gap": "속도위반만으로 결론을 내리지 말고 회피 가능성 감정과 연결해야 합니다.",
    },
    {
        "id": "criminal_civil_split",
        "keywords": ["criminal", "civil", "형사", "민사", "무죄", "항소", "사망"],
        "case_fields": ["fatality", "known_result", "analysis_uncertainty"],
        "video_fields": [],
        "evidence_requirements": [
            "형사 유무죄 판단과 민사 과실비율 판단의 기준 차이를 설명",
            "사망 사고 대응 안내와 보험 처리 가능성을 분리",
        ],
        "gap": "형사/민사/보험 판단을 같은 결론처럼 표시하면 사용자 오해가 커집니다.",
    },
    {
        "id": "stopped_state",
        "keywords": ["stopped", "정차", "멈춤", "정지"],
        "case_fields": ["stopped", "analysis_uncertainty"],
        "video_fields": ["stopped"],
        "evidence_requirements": [
            "정차 위치, 정차 지속 시간, 정차 사유를 사용자 입력과 영상 관찰로 분리 확인",
            "정차 후 추돌인지 주행 중 접촉인지에 따라 KNIA 기준을 다르게 검색",
        ],
        "gap": "정차 여부가 영상에서 확인되더라도 정차 사유와 위치가 함께 있어야 과실 범위를 좁힐 수 있습니다.",
    },
    {
        "id": "non_contact_bicycle_trigger",
        "keywords": ["bicycle", "자전거", "비접촉", "유발", "역주행"],
        "case_fields": ["bicycle_involved", "possible_trigger_vehicle", "opponent_behavior", "analysis_uncertainty"],
        "video_fields": ["bicycle_present", "opponent_behavior", "sudden_brake"],
        "evidence_requirements": [
            "비접촉 유발 차량 또는 자전거의 책임 인정 가능성 확인",
            "직접 추돌 차량과 유발 원인의 책임을 분리한 보험/법률 근거 확인",
        ],
        "gap": "비접촉 유발 요인은 별도 party/action fact로 다뤄야 합니다.",
    },
    {
        "id": "time_gap_sudden_brake",
        "keywords": ["time", "4초", "시간", "급제동", "급차로"],
        "case_fields": ["time_gap_sec", "sudden_brake", "lane_change_actor", "analysis_uncertainty"],
        "video_fields": ["sudden_brake", "lane_change_actor"],
        "evidence_requirements": [
            "후방 차량이 대응할 수 있었던 시간 간격 확인",
            "급차로변경 또는 급제동 여부와 안전거리 책임을 분리",
        ],
        "gap": "시간적 여유가 없으면 후방 책임과 앞차 급정지 책임 판단이 흔들립니다.",
    },
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_manifest(path: Path) -> list[dict[str, Any]]:
    data = load_json(path)
    samples = data.get("samples") if isinstance(data, dict) else data
    if not isinstance(samples, list) or not samples:
        raise GuidanceEvalError("manifest must contain a non-empty samples array")
    return samples


def load_batch_samples(paths: list[Path]) -> dict[str, dict[str, Any]]:
    samples: dict[str, dict[str, Any]] = {}
    for path in paths:
        data = load_json(path)
        for sample in data.get("samples") or []:
            if not isinstance(sample, dict) or not sample.get("name"):
                continue
            name = str(sample["name"])
            previous = samples.get(name)
            if previous is None or should_replace(previous, sample):
                samples[name] = sample
    return samples


def load_batch_context(paths: list[Path]) -> dict[str, Any]:
    context: dict[str, Any] = {
        "sources": [str(path) for path in paths],
        "video_flow_summary": {},
        "question_priority_summary": {},
        "conflict_followup_summary": {},
        "calibration_recommendations": [],
    }
    for path in paths:
        data = load_json(path)
        if isinstance(data.get("video_flow_summary"), dict):
            context["video_flow_summary"] = data["video_flow_summary"]
        if isinstance(data.get("question_priority_summary"), dict):
            context["question_priority_summary"] = data["question_priority_summary"]
        if isinstance(data.get("conflict_followup_summary"), dict):
            context["conflict_followup_summary"] = data["conflict_followup_summary"]
        recommendations = data.get("calibration_recommendations") or data.get("recommendations") or []
        if isinstance(recommendations, list):
            context["calibration_recommendations"].extend(str(item) for item in recommendations)
    context["calibration_recommendations"] = dedupe(context["calibration_recommendations"])
    return context


def should_replace(previous: dict[str, Any], candidate: dict[str, Any]) -> bool:
    previous_status = str(previous.get("status") or "")
    candidate_status = str(candidate.get("status") or "")
    if previous_status != "passed" and candidate_status == "passed":
        return True
    if previous_status == "failed" and candidate_status != "failed":
        return True
    return candidate_status == previous_status


def load_case(sample: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    raw_path = str(sample.get("case_json") or "").strip()
    if not raw_path:
        return {}
    path = Path(raw_path)
    if not path.is_absolute():
        path = (manifest_path.parent.parent.parent / path).resolve() if raw_path.startswith("logs/") else (manifest_path.parent / path).resolve()
    if not path.exists():
        return {"_case_missing": str(path)}
    data = load_json(path)
    case = data.get("case") if isinstance(data, dict) and isinstance(data.get("case"), dict) else data
    return case if isinstance(case, dict) else {}


def case_facts(case: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    facts = case.get("structured_facts") if isinstance(case.get("structured_facts"), dict) else {}
    merged = dict(facts)
    if reference.get("known_result"):
        merged["known_result"] = reference["known_result"]
    return merged


def select_criterion(focus: str) -> dict[str, Any]:
    focus_lower = focus.lower()
    if any(keyword in focus_lower for keyword in ["crosswalk", "횡단보도", "보행자"]):
        return next(criterion for criterion in CRITERIA if criterion["id"] == "crosswalk_pedestrian_signal")
    for criterion in CRITERIA:
        if any(keyword.lower() in focus_lower for keyword in criterion["keywords"]):
            return criterion
    return {
        "id": "unmapped_focus",
        "keywords": [],
        "case_fields": ["analysis_uncertainty"],
        "video_fields": [],
        "evidence_requirements": ["해당 쟁점을 평가할 fact schema와 검색 기준을 명시적으로 추가"],
        "gap": "manifest의 평가 초점이 현재 기준표에 매핑되지 않았습니다.",
    }


def select_criterion(focus: str) -> dict[str, Any]:
    focus_lower = focus.lower()
    priority_rules = [
        ("crosswalk_pedestrian_signal", ["crosswalk", "횡단보도", "보행자", "pedestrian"]),
        ("non_contact_bicycle_trigger", ["bicycle", "자전거", "비접촉", "유발", "역주행"]),
        ("criminal_civil_split", ["criminal", "civil", "형사", "민사", "무죄", "항소", "사망"]),
        ("unlit_stopped_vehicle_visibility", ["unlit", "stealth", "무등화", "스텔스", "시인성", "야간"]),
    ]
    for criterion_id, keywords in priority_rules:
        if any(keyword.lower() in focus_lower for keyword in keywords):
            return next(criterion for criterion in CRITERIA if criterion["id"] == criterion_id)
    for criterion in CRITERIA:
        if any(keyword.lower() in focus_lower for keyword in criterion["keywords"]):
            return criterion
    return {
        "id": "unmapped_focus",
        "keywords": [],
        "case_fields": ["analysis_uncertainty"],
        "video_fields": [],
        "evidence_requirements": ["해당 쟁점에 대응하는 fact schema와 검색 기준을 명시적으로 추가"],
        "gap": "manifest 평가 초점이 현재 기준표에 매핑되지 않았습니다.",
    }


def sample_field_metrics(batch_sample: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_field: dict[str, list[dict[str, Any]]] = {}
    for item in batch_sample.get("field_metrics") or []:
        if isinstance(item, dict) and item.get("field"):
            by_field.setdefault(str(item["field"]), []).append(item)
    return by_field


def conflict_followup(batch_sample: dict[str, Any]) -> dict[str, Any]:
    followup = batch_sample.get("conflict_followup")
    return followup if isinstance(followup, dict) else {}


def conflict_followup_resolved(batch_sample: dict[str, Any]) -> bool:
    followup = conflict_followup(batch_sample)
    if not followup.get("present"):
        return False
    return int(followup.get("latest_conflict_count") or 0) == 0


def evaluate_focus(
    *,
    focus: str,
    facts: dict[str, Any],
    batch_sample: dict[str, Any],
    field_metrics: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    criterion = select_criterion(focus)
    followup_resolved = conflict_followup_resolved(batch_sample)
    case_fields_present = [field for field in criterion["case_fields"] if has_value(facts.get(field))]
    video_metrics = [
        metric
        for field in criterion["video_fields"]
        for metric in field_metrics.get(field, [])
        if metric.get("from_observation")
    ]
    video_fields_observed = sorted({str(metric.get("field")) for metric in video_metrics if metric.get("field")})
    video_fields_applied = sorted({
        str(metric.get("field"))
        for metric in video_metrics
        if metric.get("applied") or metric.get("confirmed") or metric.get("in_fact_patch")
    })
    conflicts = sorted({
        str(metric.get("field"))
        for metric in video_metrics
        if metric.get("conflict")
    })
    status = focus_status(
        pipeline_status=str(batch_sample.get("status") or "missing"),
        case_fields_present=case_fields_present,
        video_fields_observed=video_fields_observed,
        video_fields_applied=video_fields_applied,
        conflicts=conflicts,
        conflict_followup_resolved=followup_resolved,
        criterion=criterion,
    )
    return {
        "focus": focus,
        "criterion_id": criterion["id"],
        "status": status,
        "case_fields_present": case_fields_present,
        "video_fields_observed": video_fields_observed,
        "video_fields_applied_or_confirmed": video_fields_applied,
        "video_conflict_fields": conflicts,
        "conflict_followup_resolved": bool(conflicts and followup_resolved),
        "evidence_requirements": criterion["evidence_requirements"],
        "gap_note": criterion["gap"],
    }


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if value is False:
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def focus_status(
    *,
    pipeline_status: str,
    case_fields_present: list[str],
    video_fields_observed: list[str],
    video_fields_applied: list[str],
    conflicts: list[str],
    conflict_followup_resolved: bool,
    criterion: dict[str, Any],
) -> str:
    if pipeline_status == "failed":
        return "pipeline_failed"
    if conflicts:
        if conflict_followup_resolved:
            return "conflict_resolved_ready_for_evidence_review"
        return "needs_user_video_conflict_resolution"
    if video_fields_applied:
        return "video_supported_ready_for_evidence_review"
    if case_fields_present and video_fields_observed:
        return "case_fact_with_unpromoted_video_observation"
    if case_fields_present:
        return "case_fact_only_needs_evidence_review"
    if video_fields_observed:
        return "video_observed_needs_user_confirmation"
    if not criterion["video_fields"]:
        return "policy_or_evidence_issue_needs_non_video_review"
    return "missing_fact_schema_or_observation"


def sample_readiness(focus_rows: list[dict[str, Any]], batch_sample: dict[str, Any]) -> str:
    statuses = {row["status"] for row in focus_rows}
    if str(batch_sample.get("status") or "missing") == "failed":
        return "pipeline_fix_required"
    if "missing_fact_schema_or_observation" in statuses:
        return "needs_fact_schema_or_followup_question"
    if "needs_user_video_conflict_resolution" in statuses:
        return "needs_conflict_resolution_before_guidance"
    if "video_observed_needs_user_confirmation" in statuses:
        return "needs_user_confirmation_before_guidance"
    return "ready_for_legal_knia_insurance_evidence_eval"


def evaluate_sample(sample: dict[str, Any], manifest_path: Path, batch_sample: dict[str, Any]) -> dict[str, Any]:
    reference = sample.get("reference") if isinstance(sample.get("reference"), dict) else {}
    case = load_case(sample, manifest_path)
    facts = case_facts(case, reference)
    metrics = sample_field_metrics(batch_sample)
    focuses = reference.get("evaluation_focus") if isinstance(reference.get("evaluation_focus"), list) else []
    focus_rows = [
        evaluate_focus(focus=str(focus), facts=facts, batch_sample=batch_sample, field_metrics=metrics)
        for focus in focuses
    ]
    readiness = sample_readiness(focus_rows, batch_sample)
    expert_status = evaluate_expert_guidance_card(batch_sample, readiness)
    return {
        "name": str(sample.get("name") or ""),
        "pipeline_status": str(batch_sample.get("status") or "missing"),
        "expected_guidance_range": reference.get("expected_guidance_range"),
        "known_result": reference.get("known_result"),
        "case_title": case.get("title"),
        "frame_observation_count": batch_sample.get("frame_observation_count"),
        "agent_accepted_count": batch_sample.get("agent_accepted_count"),
        "agent_uncertain_count": batch_sample.get("agent_uncertain_count"),
        "applied_count": batch_sample.get("applied_count"),
        "confirmed_count": batch_sample.get("confirmed_count"),
        "conflict_count": batch_sample.get("conflict_count"),
        "conflict_followup": conflict_followup(batch_sample) or {"present": False},
        "conflict_followup_resolved": conflict_followup_resolved(batch_sample),
        "supporting_count": batch_sample.get("agent_supporting_count"),
        "video_display": batch_sample.get("video_display") if isinstance(batch_sample.get("video_display"), dict) else {},
        "missing_info_priority": batch_sample.get("missing_info_priority") if isinstance(batch_sample.get("missing_info_priority"), dict) else {},
        "guidance_readiness": readiness,
        "expert_guidance_status": expert_status["status"],
        "expert_guidance_checks": expert_status["checks"],
        "expert_guidance": batch_sample.get("expert_guidance") if isinstance(batch_sample.get("expert_guidance"), dict) else {"present": False},
        "focus_evaluations": focus_rows,
        "next_actions": next_actions(focus_rows, readiness),
    }


def evaluate_expert_guidance_card(batch_sample: dict[str, Any], readiness: str) -> dict[str, Any]:
    card = batch_sample.get("expert_guidance") if isinstance(batch_sample.get("expert_guidance"), dict) else {}
    if str(batch_sample.get("status") or "missing") == "failed":
        return {"status": "not_evaluated_pipeline_failed", "checks": []}
    if not card.get("present"):
        return {"status": "missing_expert_guidance_card", "checks": [{"id": "present", "passed": False}]}

    checks = [
        {"id": "fault_range_visible", "passed": bool(card.get("fault_range_label"))},
        {"id": "legal_points_visible", "passed": int(card.get("legal_point_count") or 0) > 0},
        {"id": "insurance_steps_visible", "passed": int(card.get("insurance_step_count") or 0) > 0},
        {"id": "basis_visible", "passed": int(card.get("basis_count") or 0) > 0},
    ]
    if readiness in {"needs_conflict_resolution_before_guidance", "needs_user_confirmation_before_guidance", "needs_fact_schema_or_followup_question"}:
        checks.append({
            "id": "pending_facts_visible",
            "passed": int(card.get("missing_item_count") or 0) > 0 or "추가" in str(card.get("status_label") or ""),
        })

    failed = [item for item in checks if not item["passed"]]
    if failed:
        return {"status": "expert_guidance_needs_display_fix", "checks": checks}
    if readiness == "ready_for_legal_knia_insurance_evidence_eval":
        return {"status": "expert_guidance_ready_for_reference_review", "checks": checks}
    return {"status": "expert_guidance_safe_with_pending_facts", "checks": checks}


def next_actions(focus_rows: list[dict[str, Any]], readiness: str) -> list[str]:
    actions: list[str] = []
    if readiness == "pipeline_fix_required":
        actions.append("E2E pipeline failure를 먼저 해소하고 동일 샘플을 재측정한다.")
    if readiness == "needs_conflict_resolution_before_guidance":
        actions.append("영상 관찰값과 사용자 입력 충돌 항목을 보완 질문 또는 관리자 진단에서 먼저 확인한다.")
    if readiness == "needs_fact_schema_or_followup_question":
        actions.append("누락된 쟁점에 대한 structured_facts field와 사용자 보완 질문을 추가한다.")
    actions.append("유사 KNIA 기준, 법령, 판례, 보험 처리 기준 검색 결과와 focus별 쟁점을 대조한다.")
    for row in focus_rows:
        if row["status"] in {"missing_fact_schema_or_observation", "case_fact_only_needs_evidence_review"}:
            actions.extend(row["evidence_requirements"])
    return dedupe(actions)


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out


def next_actions(focus_rows: list[dict[str, Any]], readiness: str) -> list[str]:
    actions: list[str] = []
    if readiness == "pipeline_fix_required":
        actions.append("E2E pipeline failure를 먼저 해소하고 동일 샘플을 재측정한다.")
    if readiness == "needs_conflict_resolution_before_guidance":
        actions.append("영상 관찰값과 사용자 입력이 충돌한 항목을 보완 질문 또는 관리자 진단에서 먼저 확인한다.")
    if readiness == "needs_user_confirmation_before_guidance":
        actions.append("영상에서만 관찰된 핵심 사실은 사용자 확인 질문을 거친 뒤 법률/보험 안내에 반영한다.")
    if readiness == "needs_fact_schema_or_followup_question":
        actions.append("누락된 쟁점에 대응하는 structured_facts field 또는 사용자 보완 질문을 추가한다.")
    actions.append("유사 KNIA 기준, 법령, 판례, 보험 처리 기준 검색 결과를 focus별 쟁점과 대조한다.")
    for row in focus_rows:
        if row["status"] in {"missing_fact_schema_or_observation", "case_fact_only_needs_evidence_review"}:
            actions.extend(row["evidence_requirements"])
    return dedupe(actions)


def reference_recommendations(
    *,
    readiness_counts: Counter,
    expert_counts: Counter,
    focus_counts: Counter,
    batch_context: dict[str, Any],
) -> list[str]:
    recommendations: list[str] = []
    if readiness_counts.get("pipeline_fix_required"):
        recommendations.append("실패 샘플은 정확도 조정보다 pipeline timeout 또는 E2E 실패 원인을 먼저 해결한다.")
    if readiness_counts.get("needs_conflict_resolution_before_guidance"):
        recommendations.append("충돌 샘플은 결과 카드 확정보다 보완 질문/재분석 흐름의 우선순위를 높인다.")
    if readiness_counts.get("needs_fact_schema_or_followup_question"):
        recommendations.append("manifest 평가 초점 중 fact schema가 없는 항목은 Agent 입력 계약에 먼저 반영한다.")
    if readiness_counts.get("ready_for_legal_knia_insurance_evidence_eval"):
        recommendations.append("준비 완료 샘플은 다음 단계에서 KNIA/법령/판례/보험 근거 카드의 실제 근거 정합성을 대조한다.")
    if expert_counts.get("missing_expert_guidance_card") or expert_counts.get("expert_guidance_needs_display_fix"):
        recommendations.append("전문가 안내 카드 누락 또는 표시 실패가 있으면 정확도 튜닝보다 Gateway/Frontend 표시 계약을 먼저 고친다.")

    if focus_counts.get("conflict_resolved_ready_for_evidence_review"):
        recommendations.append("영상-사용자 입력 충돌이 해소된 샘플은 충돌 대기열에 남기지 말고 KNIA/법령/판례/보험 근거 대조 단계로 넘긴다.")

    video_summary = batch_context.get("video_flow_summary") if isinstance(batch_context.get("video_flow_summary"), dict) else {}
    if video_summary:
        conflict_rate = float(video_summary.get("conflict_rate") or 0)
        uncertain_rate = float(video_summary.get("uncertain_rate") or 0)
        if conflict_rate > 0:
            recommendations.append("실제 OpenAI 관찰값에서 사용자 입력 충돌이 발생하므로 충돌 항목은 확정 과실 근거로 바로 쓰지 않는다.")
        if uncertain_rate >= 0.3:
            recommendations.append("보류 관찰 비율이 높으므로 사용자 보완 질문과 관리자 진단의 field label 우선순위를 유지한다.")
    return dedupe(recommendations)


def aggregate(samples: list[dict[str, Any]], batch_context: dict[str, Any] | None = None) -> dict[str, Any]:
    batch_context = batch_context or {}
    readiness_counts = Counter(sample["guidance_readiness"] for sample in samples)
    expert_counts = Counter(sample["expert_guidance_status"] for sample in samples)
    focus_counts = Counter(row["status"] for sample in samples for row in sample["focus_evaluations"])
    criterion_counts = Counter(row["criterion_id"] for sample in samples for row in sample["focus_evaluations"])
    recurring_gaps = [
        {"criterion_id": criterion, "count": count}
        for criterion, count in criterion_counts.most_common()
        if count >= 2
    ]
    return {
        "reference_guidance_eval": "completed",
        "sample_count": len(samples),
        "pipeline_passed_count": sum(1 for sample in samples if sample["pipeline_status"] == "passed"),
        "readiness_counts": dict(sorted(readiness_counts.items())),
        "expert_guidance_status_counts": dict(sorted(expert_counts.items())),
        "focus_status_counts": dict(sorted(focus_counts.items())),
        "batch_video_flow_summary": batch_context.get("video_flow_summary") or {},
        "batch_question_priority_summary": batch_context.get("question_priority_summary") or {},
        "batch_conflict_followup_summary": batch_context.get("conflict_followup_summary") or {},
        "recurring_gaps": recurring_gaps,
        "recommendations": reference_recommendations(
            readiness_counts=readiness_counts,
            expert_counts=expert_counts,
            focus_counts=focus_counts,
            batch_context=batch_context,
        ),
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate lawyer-reference accident samples for guidance readiness.")
    parser.add_argument("--manifest", required=True, help="JSON manifest with samples and reference evaluation metadata.")
    parser.add_argument(
        "--batch-output",
        action="append",
        required=True,
        help="video_accuracy_batch aggregate.json. Pass more than once to merge retries.",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest_samples = load_manifest(manifest_path)
    batch_output_paths = [Path(path).expanduser().resolve() for path in args.batch_output]
    batch_samples = load_batch_samples(batch_output_paths)
    batch_context = load_batch_context(batch_output_paths)
    evaluated = []
    for sample in manifest_samples:
        name = str(sample.get("name") or "")
        evaluated.append(evaluate_sample(sample, manifest_path, batch_samples.get(name, {"name": name, "status": "missing"})))
    summary = aggregate(evaluated, batch_context)
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GuidanceEvalError as exc:
        print(f"reference_guidance_eval=failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
