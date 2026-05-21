from __future__ import annotations

TRAFFIC_RULES = [
    ("ROAD_ACCIDENT_REPORTING_DUTY", "교통사고 발생 시 조치 및 신고 의무", "reporting", "사고 발생 시 사상자 구호, 위험 방지, 필요 시 신고 의무를 점검합니다.", ["reporting_duty", "injury"], ["injury", "damage_level"], ["reporting_review"]),
    ("SAFE_DRIVING_DUTY", "안전운전 의무", "duty", "도로 상황에 맞춰 안전하게 운전할 주의의무를 점검합니다.", ["safe_driving"], ["weather", "light_condition"], ["duty_of_care"]),
    ("SIGNAL_VIOLATION", "신호위반", "gross_negligence", "교차로 및 신호 준수 여부는 과실과 형사 리스크의 핵심 요소입니다.", ["signal_violation", "intersection"], ["signal_state"], ["twelve_gross_negligence"]),
    ("CENTER_LINE_VIOLATION", "중앙선 침범", "gross_negligence", "중앙선 침범은 중대 과실 검토 대상입니다.", ["center_line"], ["lane_position"], ["twelve_gross_negligence"]),
    ("CROSSWALK_PEDESTRIAN_PROTECTION", "횡단보도 보행자 보호의무", "pedestrian", "횡단보도 주변 보행자 보호의무 위반 가능성을 점검합니다.", ["crosswalk", "pedestrian"], ["pedestrian", "crosswalk_nearby"], ["pedestrian_injury"]),
    ("SCHOOL_ZONE_CHILD_PROTECTION", "어린이보호구역 어린이 보호의무", "school_zone", "어린이보호구역 내 어린이 사고는 특정범죄 가중처벌법상 리스크 검토가 필요합니다.", ["school_zone", "child_protection", "speed_limit"], ["school_zone", "victim_is_child", "injury"], ["school_zone_criminal_review"]),
    ("TWELVE_GROSS_NEGLIGENCE", "12대 중과실", "gross_negligence", "신호위반, 중앙선 침범, 보행자 보호의무 위반 등 중대 과실 여부를 점검합니다.", ["twelve_gross_negligence"], ["signal_state", "injury"], ["criminal_review"]),
    ("DRUNK_DRIVING_RISK", "음주운전 사고 리스크", "criminal", "음주운전은 형사책임과 보험 처리에 중대한 영향을 줍니다.", ["drunk_driving"], ["drunk_driving"], ["criminal_high"]),
    ("UNLICENSED_DRIVING_RISK", "무면허운전 사고 리스크", "criminal", "무면허운전 여부는 형사책임 및 보험 면책 쟁점이 될 수 있습니다.", ["unlicensed"], ["unlicensed"], ["criminal_high"]),
    ("HIT_AND_RUN_RISK", "뺑소니/사고 후 미조치 리스크", "criminal", "사고 후 구호 및 조치 없이 이탈한 경우 중대한 형사 리스크가 있습니다.", ["hit_and_run"], ["left_scene"], ["criminal_high"]),
    ("REAR_END_SAFE_DISTANCE", "후미추돌 안전거리", "fault", "후방 차량의 안전거리 확보 및 전방주시 의무를 점검합니다.", ["rear_end", "safe_distance"], ["stopped", "sudden_brake"], ["rear_vehicle_fault"]),
    ("LANE_CHANGE_CAUTION", "차선변경 주의의무", "fault", "진로변경 시 방향지시등, 안전거리, 사각지대 확인 여부를 점검합니다.", ["lane_change", "turn_signal"], ["lane_change", "turn_signal"], ["lane_change_fault"]),
]


SCENARIO_MAPPINGS = {
    "rear_end_collision": [("REAR_END_SAFE_DISTANCE", 1.0), ("SAFE_DRIVING_DUTY", 0.7), ("ROAD_ACCIDENT_REPORTING_DUTY", 0.5)],
    "school_zone_child_accident": [("SCHOOL_ZONE_CHILD_PROTECTION", 1.0), ("CROSSWALK_PEDESTRIAN_PROTECTION", 0.8), ("TWELVE_GROSS_NEGLIGENCE", 0.7), ("ROAD_ACCIDENT_REPORTING_DUTY", 0.7)],
    "intersection_signal_violation": [("SIGNAL_VIOLATION", 1.0), ("TWELVE_GROSS_NEGLIGENCE", 0.8), ("SAFE_DRIVING_DUTY", 0.5)],
    "lane_change_collision": [("LANE_CHANGE_CAUTION", 1.0), ("SAFE_DRIVING_DUTY", 0.6)],
    "pedestrian_crosswalk_accident": [("CROSSWALK_PEDESTRIAN_PROTECTION", 1.0), ("ROAD_ACCIDENT_REPORTING_DUTY", 0.8), ("TWELVE_GROSS_NEGLIGENCE", 0.6)],
    "drunk_or_unlicensed_accident": [("DRUNK_DRIVING_RISK", 1.0), ("UNLICENSED_DRIVING_RISK", 0.9), ("TWELVE_GROSS_NEGLIGENCE", 0.7)],
    "hit_and_run_risk": [("HIT_AND_RUN_RISK", 1.0), ("ROAD_ACCIDENT_REPORTING_DUTY", 0.9)],
}
