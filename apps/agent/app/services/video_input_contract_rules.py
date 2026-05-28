from __future__ import annotations

from typing import Any


VERSION = "agent-video-input-contract-v1"
MIN_FACT_CONFIDENCE = 0.75
FRAME_RICH_RECOVERY_MIN_FRAMES = 6

FIELD_CONFIDENCE_THRESHOLDS = {
    "stopped": 0.82,
    "opponent_behavior": 0.88,
    "lane_change_actor": 0.88,
    "intersection": 0.82,
    "opponent_signal_visible": 0.84,
    "opponent_signal_violation": 0.88,
    "signal_transition": 0.82,
    "crosswalk_nearby": 0.85,
    "pedestrian_visible": 0.88,
    "pedestrian_signal": 0.82,
    "school_zone": 0.85,
    "centerline_crossed": 0.86,
    "road_obstruction": 0.84,
    "illegal_parking_obstruction": 0.84,
    "opposing_vehicle_present": 0.82,
    "opposing_vehicle_did_not_stop": 0.88,
    "secondary_collision": 0.84,
    "non_contact_trigger": 0.82,
    "trigger_actor_type": 0.78,
    "trigger_actor_behavior": 0.78,
    "direct_collision_partner_type": 0.82,
    "rear_vehicle_collision": 0.84,
    "centerline_cross_reason": 0.78,
    "collision_partner_type": 0.82,
    "primary_collision_target": 0.78,
    "collision_point_visible": 0.84,
    "collision_point_location": 0.78,
    "front_vehicle_stopped": 0.84,
    "ego_turn_direction": 0.78,
    "stopped_vehicle_without_lights": 0.88,
    "highway_or_expressway": 0.82,
}

CONFIRMATION_FIELD_PRIORITIES = {
    "stopped": 10,
    "collision_partner_type": 20,
    "primary_collision_target": 30,
    "collision_point_visible": 40,
    "collision_point_location": 50,
    "front_vehicle_stopped": 60,
    "ego_turn_direction": 70,
    "opponent_behavior": 80,
    "intersection": 90,
    "user_signal": 100,
    "opponent_signal_visible": 110,
    "opponent_signal": 120,
    "signal_transition": 130,
    "opponent_signal_violation": 140,
    "centerline_crossed": 150,
    "centerline_cross_reason": 160,
    "road_obstruction": 170,
    "illegal_parking_obstruction": 180,
    "opposing_vehicle_present": 190,
    "opposing_vehicle_did_not_stop": 200,
    "secondary_collision": 210,
    "non_contact_trigger": 220,
    "trigger_actor_type": 230,
    "trigger_actor_behavior": 240,
    "direct_collision_partner_type": 250,
    "rear_vehicle_collision": 260,
    "stopped_vehicle_without_lights": 270,
    "highway_or_expressway": 280,
    "lane_change_actor": 290,
    "sudden_brake": 300,
    "turn_signal": 310,
    "crosswalk_nearby": 320,
    "pedestrian_visible": 330,
    "pedestrian_signal": 340,
    "school_zone": 350,
    "injury": 360,
    "damage_level": 370,
}

FRAME_REF_REQUIRED_FACT_FIELDS = {
    "stopped",
    "sudden_brake",
    "opponent_behavior",
    "lane_change_actor",
    "intersection",
    "opponent_signal_visible",
    "opponent_signal_violation",
    "signal_transition",
    "crosswalk_nearby",
    "pedestrian_visible",
    "pedestrian_signal",
    "school_zone",
    "damage_level",
    "centerline_crossed",
    "road_obstruction",
    "illegal_parking_obstruction",
    "opposing_vehicle_present",
    "opposing_vehicle_did_not_stop",
    "secondary_collision",
    "non_contact_trigger",
    "trigger_actor_type",
    "trigger_actor_behavior",
    "direct_collision_partner_type",
    "rear_vehicle_collision",
    "centerline_cross_reason",
    "collision_partner_type",
    "primary_collision_target",
    "collision_point_visible",
    "collision_point_location",
    "front_vehicle_stopped",
    "ego_turn_direction",
    "stopped_vehicle_without_lights",
    "highway_or_expressway",
}

FRAME_REF_REQUIRED_SOURCES = {
    "frame_analysis",
    "vision_model",
    "video_model",
    "dashcam_analysis",
    "blackbox_analysis",
}

OBSERVATION_CONTAINERS = (
    "observations",
    "video_observations",
    "analysis_observations",
    "detected_events",
    "events",
    "frame_observations",
)

FACT_FIELDS = {
    "stopped",
    "sudden_brake",
    "opponent_behavior",
    "lane_change_actor",
    "turn_signal",
    "user_signal",
    "opponent_signal",
    "opponent_signal_visible",
    "opponent_signal_violation",
    "signal_transition",
    "intersection",
    "crosswalk_nearby",
    "pedestrian_visible",
    "pedestrian_signal",
    "school_zone",
    "victim_is_child",
    "bicycle_location",
    "bicycle_direction",
    "injury",
    "damage_level",
    "centerline_crossed",
    "centerline_cross_reason",
    "road_obstruction",
    "illegal_parking_obstruction",
    "opposing_vehicle_present",
    "opposing_vehicle_did_not_stop",
    "secondary_collision",
    "non_contact_trigger",
    "trigger_actor_type",
    "trigger_actor_behavior",
    "direct_collision_partner_type",
    "rear_vehicle_collision",
    "collision_partner_type",
    "primary_collision_target",
    "collision_point_visible",
    "collision_point_location",
    "front_vehicle_stopped",
    "ego_turn_direction",
    "stopped_vehicle_without_lights",
    "highway_or_expressway",
}

SUPPORTING_OBSERVATION_FIELDS = {
    "impact_direction",
    "collision_direction",
    "recaptured_screen",
    "dashcam_screen_visible",
    "screen_glare_or_reflection",
    "accident_event_candidate",
    "visual_evidence_limited",
}

FIELD_ALIASES = {
    "ego_stopped": "stopped",
    "vehicle_stopped": "stopped",
    "is_stopped": "stopped",
    "stationary": "stopped",
    "hard_brake": "sudden_brake",
    "emergency_brake": "sudden_brake",
    "rear_impact": "opponent_behavior",
    "opponent_lane_change": "lane_change_actor",
    "my_lane_change": "lane_change_actor",
    "signal_violation": "opponent_signal_violation",
    "traffic_light_user": "user_signal",
    "traffic_light_opponent": "opponent_signal",
    "opponent_traffic_light_visible": "opponent_signal_visible",
    "traffic_signal_transition": "signal_transition",
    "signal_phase_transition": "signal_transition",
    "intersection_visible": "intersection",
    "pedestrian_crosswalk": "crosswalk_nearby",
    "pedestrian_in_crosswalk": "pedestrian_visible",
    "visible_pedestrian": "pedestrian_visible",
    "pedestrian_traffic_light": "pedestrian_signal",
    "child_victim": "victim_is_child",
    "crossed_centerline": "centerline_crossed",
    "yellow_centerline_crossed": "centerline_crossed",
    "centerline_reason": "centerline_cross_reason",
    "obstruction": "road_obstruction",
    "parked_vehicle_obstruction": "illegal_parking_obstruction",
    "oncoming_vehicle": "opposing_vehicle_present",
    "oncoming_vehicle_present": "opposing_vehicle_present",
    "oncoming_vehicle_did_not_stop": "opposing_vehicle_did_not_stop",
    "second_collision": "secondary_collision",
    "noncontact_trigger": "non_contact_trigger",
    "non_contact_cause": "non_contact_trigger",
    "trigger_actor": "trigger_actor_type",
    "trigger_object": "trigger_actor_type",
    "trigger_vehicle": "trigger_actor_type",
    "trigger_actor_motion": "trigger_actor_behavior",
    "actual_collision_partner": "direct_collision_partner_type",
    "direct_collision_partner": "direct_collision_partner_type",
    "rear_vehicle_impact": "rear_vehicle_collision",
    "rear_bus_collision": "rear_vehicle_collision",
    "collision_object_type": "collision_partner_type",
    "collision_target_type": "collision_partner_type",
    "collision_object": "primary_collision_target",
    "collision_target": "primary_collision_target",
    "impact_point_visible": "collision_point_visible",
    "impact_location": "collision_point_location",
    "lead_vehicle_stopped": "front_vehicle_stopped",
    "front_car_stopped": "front_vehicle_stopped",
    "vehicle_ahead_stopped": "front_vehicle_stopped",
    "turn_direction": "ego_turn_direction",
    "ego_turn": "ego_turn_direction",
    "ego_direction": "ego_turn_direction",
    "unlit_stopped_vehicle": "stopped_vehicle_without_lights",
    "dark_stopped_vehicle": "stopped_vehicle_without_lights",
    "expressway": "highway_or_expressway",
    "highway": "highway_or_expressway",
    "impact_window_candidate": "accident_event_candidate",
    "event_window_candidate": "accident_event_candidate",
}

TECHNICAL_FIELDS = (
    "duration_sec",
    "width",
    "height",
    "fps",
    "codec",
    "extension",
    "file_size_bytes",
    "upload_status",
)


def normalize_fact_value(field: str, value: Any, raw: dict[str, Any]) -> Any:
    if field == "opponent_behavior":
        text = " ".join(str(item).lower() for item in (value, raw.get("raw_field"), raw.get("label")) if item is not None)
        if str(value).lower() in {"rear_collision", "lane_change", "signal_violation"}:
            return str(value).lower()
        if any(token in text for token in ("rear", "back", "behind", "rear_end")):
            return "rear_collision"
        if any(token in text for token in ("lane_change", "cut_in")):
            return "lane_change"
        if any(token in text for token in ("signal", "red_light")):
            return "signal_violation"
        return None
    if field == "lane_change_actor":
        text = str(value).lower()
        if text in {"opponent", "other", "target", "other_vehicle"}:
            return "opponent"
        if text in {"user", "ego", "self", "my_vehicle"}:
            return "user"
        return value if isinstance(value, str) and value.strip() else None
    if field == "collision_partner_type":
        return normalize_actor_type(value)
    if field in {"trigger_actor_type", "direct_collision_partner_type"}:
        return normalize_actor_type(value)
    if field == "trigger_actor_behavior":
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if text in {"wrong_way", "reverse_direction", "opposite_direction", "sudden_entry", "sudden_appearance", "cut_in", "obstacle_avoidance", "stopped_obstruction"}:
            return text
        if any(token in text for token in ("wrong", "reverse", "opposite", "역주행", "역방향")):
            return "wrong_way"
        if any(token in text for token in ("sudden", "갑자기", "튀어나", "진입")):
            return "sudden_entry"
        if text and text != "unknown":
            return text
        return None
    if field in {"ego_turn_direction"}:
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if text in {"right", "right_turn", "turn_right"}:
            return "right"
        if text in {"left", "left_turn", "turn_left"}:
            return "left"
        if text in {"straight", "go_straight", "forward"}:
            return "straight"
        if text in {"u_turn", "uturn"}:
            return "u_turn"
        return None
    if field in {"user_signal", "opponent_signal", "pedestrian_signal"}:
        return normalize_signal(value)
    if field == "signal_transition":
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if text in {"green_to_yellow", "yellow_to_red", "red_to_green", "green_to_red", "flashing", "none"}:
            return text
        return text if text and text != "unknown" else None
    if field in {"stopped", "sudden_brake", "opponent_signal_visible", "opponent_signal_violation", "intersection", "crosswalk_nearby", "pedestrian_visible", "school_zone", "victim_is_child", "injury", "centerline_crossed", "road_obstruction", "illegal_parking_obstruction", "opposing_vehicle_present", "opposing_vehicle_did_not_stop", "secondary_collision", "non_contact_trigger", "rear_vehicle_collision", "collision_point_visible", "front_vehicle_stopped", "stopped_vehicle_without_lights", "highway_or_expressway"}:
        return as_bool(value)
    if isinstance(value, str):
        return value.strip() or None
    return value


def normalize_signal(value: Any) -> str | None:
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"green", "go", "blue", "green_light", "blue_light"}:
        return "green"
    if text in {"yellow", "amber", "yellow_light"}:
        return "yellow"
    if text in {"red", "stop", "red_light"}:
        return "red"
    if text in {"flashing", "blink", "blinking"}:
        return "flashing"
    if text in {"none", "no_signal", "not_visible"}:
        return "none"
    return text if text and text != "unknown" else None


def normalize_actor_type(value: Any) -> str | None:
    text = str(value).strip().lower()
    if text in {"vehicle", "car", "truck", "bus", "van", "motor_vehicle", "other_vehicle"}:
        return "vehicle"
    if text in {"pedestrian", "person"}:
        return "pedestrian"
    if text in {"bicycle", "bike", "cyclist"}:
        return "bicycle"
    if text in {"motorcycle", "two_wheeler", "two-wheeler", "motorbike"}:
        return "motorcycle"
    if text in {"object", "fixed_object", "road_object", "obstacle"}:
        return "object"
    return None


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y", "1", "observed", "detected"}:
            return True
        if lowered in {"false", "no", "n", "0", "not_observed", "none"}:
            return False
    return None


def as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
