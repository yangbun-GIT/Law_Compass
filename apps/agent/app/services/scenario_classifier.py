from __future__ import annotations

from typing import Any

from app.services.knia.taxonomy import infer_party_type_from_text, party_label


def classify_scenario(text: str, facts: dict[str, Any] | None = None, keywords: list[str] | None = None) -> dict[str, Any]:
    facts = facts or {}
    keywords = keywords or []
    haystack = " ".join([text or "", str(facts), " ".join(keywords)]).lower()

    scenario_type = "general_collision"
    tags: set[str] = set()
    accident_party_type = infer_party_type_from_text(haystack, facts)

    collision_partner_type = str(facts.get("collision_partner_type") or "").strip().lower()

    if facts.get("school_zone") or "어린이보호구역" in haystack or "민식이" in haystack:
        scenario_type = "school_zone_child_accident"
        accident_party_type = "car_vs_person"
        tags.update(["school_zone", "child_protection", "injury", "speed_limit", "pedestrian"])
    elif facts.get("crosswalk_nearby") and (facts.get("stopped") or any(w in haystack for w in ["앞차", "후방", "뒤차", "추돌", "rear"])):
        scenario_type = "rear_end_collision"
        accident_party_type = "car_vs_car"
        tags.update(["rear_end", "safe_distance", "stopped_vehicle", "crosswalk"])
    elif collision_partner_type == "pedestrian" or facts.get("victim_is_child") or facts.get("pedestrian") or facts.get("pedestrian_visible") or any(w in haystack for w in ["보행자", "사람을", "사람과", "무단횡단"]):
        scenario_type = "pedestrian_crosswalk_accident"
        accident_party_type = "car_vs_person"
        tags.update(["pedestrian", "crosswalk", "injury"])
    elif collision_partner_type in {"bicycle", "motorcycle"} or facts.get("accident_type") == "bicycle_collision" or "자전거" in haystack:
        scenario_type = "bicycle_collision"
        accident_party_type = "car_vs_bicycle"
        tags.update(["bicycle", "vulnerable_road_user", "injury"])
    elif collision_partner_type == "object" or facts.get("accident_type") == "object_collision" or any(w in haystack for w in ["가드레일", "전봇대", "중앙분리대", "시설물", "기물", "기둥", "벽"]):
        scenario_type = "object_collision"
        accident_party_type = "car_vs_object"
        tags.update(["object", "property_damage", "single_vehicle"])
    elif facts.get("accident_type") == "single_vehicle_accident" or any(w in haystack for w in ["혼자", "단독", "전복", "미끄러", "빗길", "눈길", "도로 이탈"]):
        scenario_type = "single_vehicle_accident"
        accident_party_type = "single_vehicle"
        tags.update(["single_vehicle", "road_condition"])
    elif facts.get("opponent_signal_violation") or "신호위반" in haystack or (facts.get("intersection") and "신호" in haystack):
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

    if facts.get("injury"):
        tags.add("injury")
    if facts.get("signal_state") in ("red", "적색"):
        tags.add("signal")
    if facts.get("secondary_collision"):
        tags.add("secondary_collision")
    if facts.get("centerline_crossed"):
        tags.add("centerline")
    if facts.get("crosswalk_nearby"):
        tags.add("crosswalk")
    if facts.get("road_obstruction") or facts.get("illegal_parking_obstruction"):
        tags.add("road_obstruction")
    if facts.get("opposing_vehicle_present"):
        tags.add("oncoming_vehicle")
    if facts.get("bicycle_involved") or facts.get("possible_trigger_vehicle") == "bicycle":
        tags.add("bicycle")
        tags.add("non_contact_trigger")
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
    elif accident_party_type == "car_vs_object":
        tags.add("object")
    elif accident_party_type == "single_vehicle":
        tags.add("single_vehicle")

    confidence = 0.86 if scenario_type != "general_collision" and accident_party_type != "unknown" else 0.48
    return {
        "scenario_type": scenario_type,
        "scenario_tags": sorted(tags),
        "accident_party_type": accident_party_type,
        "accident_party_label": party_label(accident_party_type),
        "confidence": confidence,
    }
