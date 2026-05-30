from __future__ import annotations

from typing import Any

from app.services.knia.party_guard import canonicalize_party_type, filter_tags_by_party
from app.services.knia.taxonomy import infer_party_type_from_text, party_label


def classify_scenario(text: str, facts: dict[str, Any] | None = None, keywords: list[str] | None = None) -> dict[str, Any]:
    facts = facts or {}
    keywords = keywords or []
    haystack = " ".join([text or "", str(facts), " ".join(keywords)]).lower()

    scenario_type = "general_collision"
    tags: set[str] = set()
    accident_type = str(facts.get("accident_type") or "").strip().lower()
    fixed_party_type = canonicalize_party_type(facts.get("knia_major_party_type") or facts.get("accident_party_type"))
    accident_party_type = fixed_party_type if fixed_party_type != "unknown" else infer_party_type_from_text(haystack, facts)

    collision_partner_type = str(facts.get("collision_partner_type") or "").strip().lower()
    if accident_party_type == "unknown" and collision_partner_type == "vehicle":
        accident_party_type = "car_vs_car"
    if fixed_party_type != "unknown":
        accident_party_type = fixed_party_type
    vehicle_collision_declared = accident_party_type == "car_vs_car" or collision_partner_type == "vehicle"

    if _is_road_worker_pedestrian_accident(facts, haystack):
        tags.update(["pedestrian", "road_work", "worker", "sudden_entry", "fault_ratio"])
        return {
            "scenario_type": "pedestrian_accident",
            "accident_type": "pedestrian_roadway_worker_accident",
            "accident_party_type": "car_vs_person",
            "major_party_type": "car_vs_person",
            "accident_party_label": party_label("car_vs_person"),
            "scenario_subtype": "pedestrian_roadway_or_work_zone",
            "scenario_tags": filter_tags_by_party(sorted(tags), "car_vs_person", facts),
            "knia_tree_hint": {
                "major": "자동차와 보행자의 사고",
                "mid": "횡단보도 없음 또는 기타 사고유형",
                "leaf_candidates": ["보25", "보27-2", "보28", "보30", "보34"],
            },
            "confidence": 0.9,
        }

    if _is_one_side_traffic_sign_intersection(facts, haystack):
        tags.update(["intersection", "traffic_sign", "straight_vs_straight", "fault_ratio"])
        return {
            "scenario_type": "intersection_collision",
            "accident_type": "one_side_traffic_sign_straight_collision",
            "accident_party_type": "car_vs_car",
            "major_party_type": "car_vs_car",
            "accident_party_label": party_label("car_vs_car"),
            "scenario_subtype": "one_side_traffic_sign_straight_vs_straight",
            "scenario_tags": filter_tags_by_party(sorted(tags), "car_vs_car", facts),
            "knia_tree_hint": {
                "major": "자동차와 자동차의 사고",
                "mid": "교차로(+자로, T자로 등) 사고",
                "leaf_candidates": ["차7", "차7-1"],
            },
            "confidence": 0.88,
        }

    pedestrian_context = (
            not vehicle_collision_declared
            and (
                    _pedestrian_collision_target_confirmed(facts)
                    or collision_partner_type == "pedestrian"
                    or accident_party_type == "car_vs_person"
                    or accident_type == "pedestrian_crosswalk_accident"
                    or facts.get("victim_is_child")
                    or facts.get("pedestrian")
                    or any(w in haystack for w in ["보행자를", "사람을", "사람과", "무단횡단"])
            )
    )

    person_scenario = _person_scenario_from_context(accident_type, facts, haystack)

    if accident_party_type == "car_vs_person" and person_scenario:
        scenario_type = person_scenario
        accident_party_type = "car_vs_person"
        tags.update(["pedestrian", "injury"])
        if facts.get("pedestrian_worker") or facts.get("road_work_context"):
            tags.update(["worker", "road_work"])
        if facts.get("pedestrian_sudden_entry") or any(w in haystack for w in ["갑자기", "튀어나", "뛰어나", "차도"]):
            tags.add("sudden_entry")
        if facts.get("crosswalk_nearby") or "횡단보도" in haystack:
            tags.add("crosswalk")
    elif _is_stealth_illegal_parked_vehicle_context(facts, haystack):
        scenario_type = "stealth_illegal_parked_vehicle_collision"
        accident_party_type = "car_vs_car"
        tags.update([
            "parking",
            "stopped_vehicle",
            "unlit_stopped_vehicle",
            "visibility",
            "night",
            "road_obstruction",
            "avoidability",
        ])
        if facts.get("opponent_drunk_or_abnormal_operation") or "음주" in haystack:
            tags.update(["drunk_driving", "twelve_gross_negligence"])
        if facts.get("parked_vehicle_position") in {"under_bridge", "flowerbed_or_median", "traffic_space"}:
            tags.add("abnormal_parking_position")
    elif pedestrian_context and (facts.get("school_zone") or "어린이보호구역" in haystack or "민식이" in haystack):
        scenario_type = "school_zone_child_accident"
        accident_party_type = "car_vs_person"
        tags.update(["school_zone", "child_protection", "injury", "speed_limit", "pedestrian"])
    elif _is_intersection_signal_turning_conflict(facts, accident_type, haystack):
        scenario_type = "intersection_signal_violation"
        accident_party_type = "car_vs_car"
        tags.update(["intersection", "signal_violation", "right_of_way"])
    elif accident_type == "right_turn_front_stop":
        scenario_type = "rear_end_collision"
        accident_party_type = "car_vs_car"
        tags.update(["rear_end", "safe_distance", "front_vehicle_stopped", "right_turn", "crosswalk"])
    elif accident_type == "centerline_obstacle_collision":
        scenario_type = "parking_or_stopped_vehicle_accident"
        accident_party_type = "car_vs_car"
        tags.update(["centerline", "road_obstruction", "oncoming_vehicle"])
    elif accident_type == "stopped_vehicle_collision":
        scenario_type = "parking_or_stopped_vehicle_accident"
        accident_party_type = "car_vs_car"
        tags.update(["stopped_vehicle", "visibility", "rear_end"])
    elif accident_type == "non_contact_trigger":
        scenario_type = "rear_end_collision"
        accident_party_type = "car_vs_car"
        tags.update(["non_contact_trigger", "safe_distance"])
        if facts.get("trigger_actor_type") == "bicycle" or facts.get("possible_trigger_vehicle") == "bicycle":
            tags.add("bicycle")
        if facts.get("rear_vehicle_collision"):
            tags.add("rear_end")
    elif accident_type in {"intersection_collision", "intersection_signal_violation"}:
        scenario_type = "intersection_signal_violation"
        accident_party_type = "car_vs_car"
        tags.update(["intersection", "right_of_way"])
    elif accident_type == "rear_end_collision":
        scenario_type = "rear_end_collision"
        accident_party_type = "car_vs_car"
        tags.update(["rear_end", "safe_distance"])
    elif _is_lawful_signal_stop_rear_end_context(facts, haystack):
        scenario_type = "rear_end_collision"
        accident_party_type = "car_vs_car"
        tags.update(["rear_end", "safe_distance", "stopped_vehicle", "lawful_stop_reason", "stopped_at_red_light"])
    elif (
            collision_partner_type == "vehicle"
            and facts.get("front_vehicle_stopped")
            and (facts.get("ego_turn_direction") == "right" or facts.get("crosswalk_nearby"))
    ):
        scenario_type = "rear_end_collision"
        accident_party_type = "car_vs_car"
        tags.update(["rear_end", "safe_distance", "front_vehicle_stopped", "right_turn", "crosswalk"])
    elif facts.get("crosswalk_nearby") and (facts.get("stopped") or facts.get("front_vehicle_stopped") or any(w in haystack for w in ["앞차", "후방", "뒤차", "추돌", "rear"])):
        scenario_type = "rear_end_collision"
        accident_party_type = "car_vs_car"
        tags.update(["rear_end", "safe_distance", "stopped_vehicle", "crosswalk"])
    elif collision_partner_type != "vehicle" and pedestrian_context:
        scenario_type = _person_scenario_from_context(accident_type, facts, haystack) or "pedestrian_crosswalk_accident"
        accident_party_type = "car_vs_person"
        tags.update(["pedestrian", "crosswalk", "injury"])
    elif _is_non_contact_trigger_context(facts, haystack):
        scenario_type = "rear_end_collision"
        accident_party_type = "car_vs_car"
        tags.update(["non_contact_trigger", "safe_distance", "rear_end", "bicycle"])
    elif (
            fixed_party_type in {"unknown", "car_vs_bicycle"}
            and (collision_partner_type == "bicycle" or accident_type == "bicycle_collision" or ("자전거" in haystack and facts.get("non_contact_trigger") is not True))
    ):
        scenario_type = "bicycle_collision"
        accident_party_type = "car_vs_bicycle"
        tags.update(["bicycle", "vulnerable_road_user", "injury"])
    elif (
            fixed_party_type in {"unknown", "car_vs_motorcycle"}
            and (collision_partner_type == "motorcycle" or accident_type == "motorcycle_collision" or any(w in haystack for w in ["오토바이", "이륜차", "원동기장치자전거"]))
    ):
        scenario_type = "motorcycle_collision"
        accident_party_type = "car_vs_motorcycle"
        tags.update(["motorcycle", "two_wheeler", "vulnerable_road_user"])
    elif (
            fixed_party_type in {"unknown", "car_vs_object"}
            and (collision_partner_type == "object" or accident_type == "object_collision" or any(w in haystack for w in ["가드레일", "전봇대", "중앙분리대", "시설물", "기물", "기둥", "벽"]))
    ):
        scenario_type = "object_collision"
        accident_party_type = "car_vs_object"
        tags.update(["object", "property_damage", "single_vehicle"])
    elif (
            fixed_party_type in {"unknown", "single_vehicle"}
            and (accident_type == "single_vehicle_accident" or any(w in haystack for w in ["혼자", "단독", "전복", "미끄러", "빗길", "눈길", "도로 이탈"]))
    ):
        scenario_type = "single_vehicle_accident"
        accident_party_type = "single_vehicle"
        tags.update(["single_vehicle", "road_condition"])
    elif facts.get("opponent_signal_violation") or facts.get("user_signal_violation") or _has_red_light_violation_context(haystack) or "신호위반" in haystack or facts.get("signal_transition") or (facts.get("intersection") and not facts.get("stopped_due_to_signal") and (facts.get("user_signal") or facts.get("opponent_signal") or facts.get("opponent_signal_visible") is False or "신호" in haystack)):
        scenario_type = "intersection_signal_violation"
        accident_party_type = "car_vs_car"
        tags.update(["intersection", "signal_violation", "right_of_way"])
    elif facts.get("centerline_crossed") and (facts.get("road_obstruction") or facts.get("illegal_parking_obstruction") or any(w in haystack for w in ["중앙선", "황색 실선", "불법 주정차", "주차 차량", "장애물"])):
        scenario_type = "parking_or_stopped_vehicle_accident"
        accident_party_type = "car_vs_car"
        tags.update(["centerline", "road_obstruction", "oncoming_vehicle"])
    elif facts.get("lane_change") or any(w in haystack for w in ["차선변경", "진로변경", "끼어들", "방향지시등", "깜빡이"]):
        scenario_type = "lane_change_collision"
        accident_party_type = "car_vs_car"
        tags.update(["lane_change", "turn_signal", "blind_spot"])
    elif any(w in haystack for w in ["음주", "무면허"]):
        scenario_type = "drunk_or_unlicensed_accident"
        tags.update(["drunk_driving", "unlicensed", "twelve_gross_negligence"])
    elif any(w in haystack for w in ["뺑소니", "도주"]):
        scenario_type = "hit_and_run_risk"
        tags.update(["hit_and_run", "reporting_duty"])
    elif facts.get("stopped_vehicle_without_lights") or any(w in haystack for w in ["무등화", "스텔스", "등화 없이"]):
        scenario_type = "parking_or_stopped_vehicle_accident"
        accident_party_type = "car_vs_car"
        tags.update(["stopped_vehicle", "visibility", "night", "rear_end"])
    elif any(w in haystack for w in ["주차", "주정차"]):
        scenario_type = "parking_or_stopped_vehicle_accident"
        accident_party_type = "car_vs_car"
        tags.update(["stopped_vehicle", "parking"])
    elif facts.get("stopped") or any(w in haystack for w in ["후미", "뒤차", "후방", "안전거리", "정차"]) or ("앞차" in haystack and "추돌" in haystack):
        scenario_type = "rear_end_collision"
        accident_party_type = "car_vs_car"
        tags.update(["rear_end", "safe_distance", "stopped_vehicle"])

    if fixed_party_type != "unknown":
        accident_party_type = fixed_party_type
        scenario_type = _coerce_scenario_to_party(scenario_type, accident_party_type, facts, haystack)

    if facts.get("injury"):
        tags.add("injury")
    if facts.get("signal_state") in ("red", "적색"):
        tags.add("signal")
    if facts.get("signal_transition"):
        tags.add("signal_transition")
    if facts.get("opponent_signal_visible") is False:
        tags.add("opponent_signal_not_visible")
    if facts.get("intersection"):
        tags.add("intersection")
    if facts.get("secondary_collision"):
        tags.add("secondary_collision")
    if facts.get("centerline_crossed"):
        tags.add("centerline")
    if facts.get("crosswalk_nearby"):
        tags.add("crosswalk")
    if facts.get("front_vehicle_stopped"):
        tags.add("front_vehicle_stopped")
    if facts.get("ego_turn_direction"):
        tags.add(f"ego_turn_{facts.get('ego_turn_direction')}")
    if facts.get("is_stealth_parked_vehicle_collision"):
        tags.add("stealth_illegal_parked_vehicle")
    if facts.get("abnormal_parking"):
        tags.add("abnormal_parking_position")
    if facts.get("opponent_drunk_or_abnormal_operation"):
        tags.add("drunk_driving")
        tags.add("twelve_gross_negligence")
    if facts.get("stopped_vehicle_without_lights"):
        tags.add("unlit_stopped_vehicle")
    if facts.get("highway_or_expressway"):
        tags.add("highway")
    if facts.get("road_obstruction") or facts.get("illegal_parking_obstruction"):
        tags.add("road_obstruction")
    if facts.get("opposing_vehicle_present"):
        tags.add("oncoming_vehicle")
    if facts.get("bicycle_involved") or facts.get("possible_trigger_vehicle") == "bicycle":
        tags.add("bicycle")
        tags.add("non_contact_trigger")
    if facts.get("trigger_actor_type") == "bicycle":
        tags.add("bicycle")
        if facts.get("non_contact_trigger"):
            tags.add("non_contact_trigger")
    if facts.get("rear_vehicle_collision"):
        tags.add("rear_end")
    if facts.get("lawful_stop_reason") or facts.get("stopped_due_to_signal"):
        tags.add("lawful_stop_reason")
    if facts.get("stopped_at_red_light"):
        tags.add("stopped_at_red_light")
    if facts.get("reported_speed_kmh") or facts.get("speed_limit_kmh"):
        tags.add("speed")
    if facts.get("fatality"):
        tags.add("fatality")
    if "12대" in haystack or "중과실" in haystack:
        tags.add("twelve_gross_negligence")

    if accident_party_type == "car_vs_person":
        tags.add("pedestrian")
    elif accident_party_type == "car_vs_bicycle":
        tags.add("bicycle")
    elif accident_party_type == "car_vs_motorcycle":
        tags.add("motorcycle")
        tags.add("two_wheeler")
    elif accident_party_type == "car_vs_object":
        tags.add("object")
    elif accident_party_type == "single_vehicle":
        tags.add("single_vehicle")

    filtered_tags = filter_tags_by_party(sorted(tags), accident_party_type, facts)
    confidence = 0.86 if scenario_type != "general_collision" and accident_party_type != "unknown" else 0.48
    return {
        "scenario_type": scenario_type,
        "scenario_tags": filtered_tags,
        "accident_party_type": accident_party_type,
        "accident_party_label": party_label(accident_party_type),
        "confidence": confidence,
    }



def _is_stealth_illegal_parked_vehicle_context(facts: dict[str, Any], haystack: str) -> bool:
    accident_type = str(facts.get("accident_type") or "").strip().lower()
    if accident_type == "stealth_illegal_parked_vehicle_collision":
        return True
    if facts.get("is_stealth_parked_vehicle_collision") is True:
        return True

    collision = any(token in haystack for token in ("부딪", "충돌", "박", "들이받", "들이박", "파손", "폐차"))
    parked_vehicle = any(
        token in haystack
        for token in (
            "주차",
            "정차",
            "방치",
            "세워",
            "서있",
            "서 있",
            "트럭",
            "화물차",
            "parked",
            "stopped vehicle",
        )
    )
    stealth_or_dark = any(
        token in haystack
        for token in (
            "스텔스",
            "무등화",
            "등화 없이",
            "미등",
            "비상등",
            "차폭등",
            "야간",
            "밤",
            "늦은 밤",
            "새벽",
            "어두",
            "교량 밑",
            "교량밑",
            "교량 아래",
            "under bridge",
            "unlit",
        )
    )
    abnormal_place = any(token in haystack for token in ("화단", "중앙분리대", "갓길", "통행 공간", "flowerbed", "median"))
    drunk = any(token in haystack for token in ("음주", "음주운전", "만취", "술", "drunk"))

    fact_match = (
            facts.get("stopped_vehicle_without_lights") is True
            or facts.get("night_no_lights_or_low_visibility") is True
            or facts.get("abnormal_parking") is True
            or str(facts.get("parked_vehicle_lighting") or "") == "unlit_stealth"
            or str(facts.get("visibility_condition") or "") in {"night_dark", "under_bridge_dark"}
            or str(facts.get("opponent_impairment") or "") in {"drunk_driving_confirmed", "suspected_drunk"}
    )

    return collision and parked_vehicle and (stealth_or_dark or abnormal_place or drunk or fact_match)


def _is_road_worker_pedestrian_accident(facts: dict[str, Any], text: str) -> bool:
    if facts.get("accident_party_type") == "car_vs_person":
        if facts.get("road_worker") or facts.get("pedestrian_worker") or facts.get("work_zone_context"):
            return True
        if facts.get("accident_type") in {"pedestrian_roadway_worker_accident", "pedestrian_road_work_worker_accident"}:
            return True
    if facts.get("direct_collision_partner_type") == "person":
        return True
    if facts.get("collision_partner_type") == "person":
        return True
    if facts.get("road_worker") is True:
        return True
    return any(
        token in text
        for token in (
            "공사 담당자",
            "공사작업자",
            "공사 작업자",
            "도로 작업자",
            "작업자",
            "인부",
            "도로 폭 측정",
            "도로폭 측정",
            "차도 진입",
            "갑자기 튀어나",
            "갑자기 뛰어나",
        )
    )


def _is_one_side_traffic_sign_intersection(facts: dict[str, Any], text: str) -> bool:
    if facts.get("accident_party_type") not in {None, "", "car_vs_car"} and facts.get("knia_major_party_type") != "car_vs_car":
        return False
    return (
        ("지시표지" in text or "일시정지" in text)
        and "교차로" in text
        and "직진" in text
        and ("측면" in text or "진입" in text or "적색" in text or "녹색" in text)
    )


def _is_intersection_signal_turning_conflict(facts: dict[str, Any], accident_type: str, haystack: str) -> bool:
    if facts.get("stopped_due_to_signal") and _has_rear_end_tokens(haystack):
        return False
    if not facts.get("intersection") and "교차로" not in haystack:
        return False
    turning_text = " ".join(str(facts.get(field) or "") for field in ("turning", "ego_turn_direction", "accident_type"))
    signal_text = " ".join(str(facts.get(field) or "") for field in ("signal_state", "signal_transition", "accident_type", "analysis_uncertainty"))
    opponent_text = str(facts.get("opponent_behavior") or "")
    left_turn = any(token in turning_text.lower() for token in ("left_turn", "left")) or "좌회전" in haystack
    straight_opponent = "직진" in opponent_text or "직진" in haystack
    signal_context = (
            bool(facts.get("signal_transition"))
            or bool(facts.get("signal_timing_uncertain"))
            or bool(facts.get("cctv_needed"))
            or any(token in signal_text for token in ("황색", "적색", "빨간", "yellow", "red"))
            or "신호" in haystack
    )
    declared_intersection = accident_type in {"intersection_collision", "intersection_signal_violation"} or (
            "교차로" in haystack and ("좌회전" in haystack or "직진" in haystack)
    )
    return signal_context and (declared_intersection or (left_turn and straight_opponent))


def _is_lawful_signal_stop_rear_end_context(facts: dict[str, Any], haystack: str) -> bool:
    lawful_stop = facts.get("stopped_due_to_signal") or facts.get("stopped_at_red_light") or any(
        token in haystack for token in ("신호대기", "신호 대기", "빨간불에 정차", "적색신호 대기", "정지선에서 대기")
    )
    stopped = facts.get("stopped") is True or any(token in haystack for token in ("정차", "정지", "멈춰", "대기"))
    return bool(lawful_stop and stopped and _has_rear_end_tokens(haystack))


def _has_rear_end_tokens(text: str) -> bool:
    return any(token in text for token in ("뒷차", "뒷 차", "뒤차", "뒤 차", "후방", "후속", "후미", "추돌", "들이받", "받힘", "rear"))


def _has_red_light_violation_context(text: str) -> bool:
    red_context = any(token in text for token in ("빨간불", "적색신호", "적색 신호", "정지신호", "red light", "red signal"))
    violation_context = any(token in text for token in ("진입", "들어갔", "통과", "무시", "위반", "진행", "교차로로", "entered", "ran", "ignored", "violation"))
    lawful_wait = any(token in text for token in ("신호대기", "신호 대기", "빨간불에 정차", "적색신호 대기", "정지선에서 대기"))
    return red_context and violation_context and not lawful_wait


def _is_non_contact_trigger_context(facts: dict[str, Any], haystack: str) -> bool:
    trigger = str(facts.get("trigger_actor_type") or facts.get("possible_trigger_vehicle") or "").strip().lower()
    return (
            facts.get("non_contact_trigger") is True
            or (
                    trigger == "bicycle"
                    and (
                            facts.get("rear_vehicle_collision") is True
                            or facts.get("stopped") is True
                            or any(token in haystack for token in ("뒤에서", "후방", "뒤차", "후미", "rear", "bus"))
                    )
            )
    )
    if scenario_type == "stealth_illegal_parked_vehicle_collision":
        accident_party_type = "car_vs_car"
        tags.discard("bicycle")
        tags.discard("pedestrian")


def _coerce_scenario_to_party(scenario_type: str, party_type: str, facts: dict[str, Any], haystack: str) -> str:
    allowed = {
        "car_vs_car": {
            "general_collision",
            "general_vehicle_collision",
            "rear_end_collision",
            "lane_change_collision",
            "intersection_signal_violation",
            "intersection_collision",
            "centerline_obstacle_collision",
            "parking_or_stopped_vehicle_accident",
            "stealth_illegal_parked_vehicle_collision",
            "drunk_or_unlicensed_accident",
            "hit_and_run_risk",
        },
        "car_vs_person": {
            "general_collision",
            "pedestrian_crosswalk_accident",
            "pedestrian_near_crosswalk_accident",
            "pedestrian_no_crosswalk_road_crossing",
            "pedestrian_road_work_worker_accident",
            "pedestrian_sudden_entry_accident",
            "pedestrian_on_road_edge_accident",
            "pedestrian_construction_zone_accident",
            "school_zone_child_accident",
        },
        "car_vs_bicycle": {"general_collision", "bicycle_collision"},
        "car_vs_motorcycle": {"general_collision", "motorcycle_collision"},
        "car_vs_object": {"general_collision", "object_collision"},
        "single_vehicle": {"general_collision", "single_vehicle_accident"},
    }.get(party_type, {"general_collision"})
    if scenario_type in allowed:
        return scenario_type
    if party_type == "car_vs_car":
        if facts.get("is_stealth_parked_vehicle_collision"):
            return "stealth_illegal_parked_vehicle_collision"
        if any(w in haystack for w in ["차선변경", "진로변경", "끼어들", "방향지시등", "깜빡이"]):
            return "lane_change_collision"
        if any(w in haystack for w in ["교차로", "신호위반", "적색", "빨간불", "좌회전", "직진"]):
            return "intersection_signal_violation"
        if any(w in haystack for w in ["중앙선", "황색 실선", "장애물"]):
            return "centerline_obstacle_collision"
        if any(w in haystack for w in ["주차", "정차 차량", "주정차", "스텔스", "무등화"]):
            return "parking_or_stopped_vehicle_accident"
        if any(w in haystack for w in ["후미", "후방", "뒤차", "뒷차", "앞차", "추돌"]):
            return "rear_end_collision"
        return "general_vehicle_collision"
    if party_type == "car_vs_person":
        return _person_scenario_from_context(str(facts.get("accident_type") or scenario_type), facts, haystack) or "pedestrian_crosswalk_accident"
    return {
        "car_vs_bicycle": "bicycle_collision",
        "car_vs_motorcycle": "motorcycle_collision",
        "car_vs_object": "object_collision",
        "single_vehicle": "single_vehicle_accident",
    }.get(party_type, scenario_type)


def _person_scenario_from_context(accident_type: str, facts: dict[str, Any], haystack: str) -> str | None:
    if accident_type in {
        "pedestrian_crosswalk_accident",
        "pedestrian_near_crosswalk_accident",
        "pedestrian_no_crosswalk_road_crossing",
        "pedestrian_road_work_worker_accident",
        "pedestrian_sudden_entry_accident",
        "pedestrian_on_road_edge_accident",
        "pedestrian_construction_zone_accident",
        "school_zone_child_accident",
    }:
        return accident_type
    if facts.get("school_zone") or "어린이보호구역" in haystack or "민식이" in haystack:
        return "school_zone_child_accident"
    if facts.get("pedestrian_worker") or facts.get("road_work_context") or any(w in haystack for w in ["공사 담당자", "작업자", "도로 작업자", "도로 폭 측정", "공사구역", "측량"]):
        return "pedestrian_road_work_worker_accident"
    if facts.get("crosswalk_nearby") or "횡단보도" in haystack:
        return "pedestrian_crosswalk_accident"
    if any(w in haystack for w in ["갑자기", "튀어나", "뛰어나", "차도"]):
        return "pedestrian_sudden_entry_accident"
    if any(w in haystack for w in ["도로 가장자리", "차도 가장자리", "갓길"]):
        return "pedestrian_on_road_edge_accident"
    return None


def _pedestrian_collision_target_confirmed(facts: dict[str, Any]) -> bool:
    target_fields = (
        "direct_collision_partner_type",
        "collision_partner_type",
        "primary_collision_target",
    )
    for field in target_fields:
        value = str(facts.get(field) or "").strip().lower().replace("-", "_")
        if value == "pedestrian":
            return True
    return False
