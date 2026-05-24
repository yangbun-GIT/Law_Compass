type AnyRecord = Record<string, any>;

const UNKNOWN_VALUES = ["확인 중", "영상으로 확인 필요", "표지 확인 필요", "이유 불명"];

export function normalizeFollowupAnswers(answers: AnyRecord = {}, previousFacts: AnyRecord = {}) {
  const patch: AnyRecord = {};
  const answeredFields: string[] = [];
  const unresolvedFields: string[] = [];
  const ignoredFields: string[] = [];

  for (const [field, raw] of Object.entries(answers || {})) {
    const value = String(raw ?? "").trim();
    if (!field || !value) {
      ignoredFields.push(field);
      continue;
    }
    if (isUnknown(value)) {
      unresolvedFields.push(field);
      continue;
    }
    const before = JSON.stringify(patch);
    applyAnswer(patch, field, value);
    if (JSON.stringify(patch) === before) {
      ignoredFields.push(field);
    } else {
      answeredFields.push(field);
    }
  }

  const previousIteration = Number(previousFacts._followup_iteration || 0);
  const iteration = Math.max(0, Math.min(3, previousIteration + (answeredFields.length || unresolvedFields.length ? 1 : 0)));
  if (answeredFields.length || unresolvedFields.length) {
    patch._followup_iteration = iteration;
    patch._followup_answered_fields = unique([...(previousFacts._followup_answered_fields || []), ...answeredFields]);
    patch._followup_unresolved_fields = unique([...(previousFacts._followup_unresolved_fields || []), ...unresolvedFields]);
    patch._followup_ignored_fields = unique([...(previousFacts._followup_ignored_fields || []), ...ignoredFields]).slice(-12);
  }

  return {
    patch,
    answered_fields: answeredFields,
    unresolved_fields: unresolvedFields,
    ignored_fields: ignoredFields,
    iteration,
  };
}

function applyAnswer(patch: AnyRecord, field: string, value: string) {
  if (field === "injury") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.injury = parsed;
      return;
    }
    patch.injury = !includesAny(value, ["없음", "아님"]);
    return;
  }
  if (field === "stopped") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.stopped = parsed;
      if (parsed) patch.sudden_brake = false;
      return;
    }
    patch.stopped = includesAny(value, ["정차", "멈춰"]);
    if (includesAny(value, ["급정거"])) patch.sudden_brake = true;
    else if (patch.stopped) patch.sudden_brake = false;
    return;
  }
  if (field === "collision_partner_type") {
    patch.collision_partner_type = normalizeCollisionPartnerType(value);
    return;
  }
  if (field === "primary_collision_target") {
    patch.primary_collision_target = value;
    return;
  }
  if (field === "collision_point_visible") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.collision_point_visible = parsed;
      return;
    }
    patch.collision_point_visible = !includesAny(value, ["불명확", "안 보", "없음"]);
    return;
  }
  if (field === "collision_point_location") {
    patch.collision_point_location = value;
    return;
  }
  if (field === "sudden_brake") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.sudden_brake = parsed;
      return;
    }
    patch.sudden_brake = !includesAny(value, ["없음"]);
    return;
  }
  if (field === "school_zone") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.school_zone = parsed;
      return;
    }
    patch.school_zone = includesAny(value, ["맞음", "어린이보호구역"]);
    return;
  }
  if (field === "victim_is_child") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.victim_is_child = parsed;
      return;
    }
    patch.victim_is_child = includesAny(value, ["미만", "어린이"]);
    return;
  }
  if (field === "crosswalk_nearby") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.crosswalk_nearby = parsed;
      return;
    }
    patch.crosswalk_nearby = !includesAny(value, ["아님"]);
    return;
  }
  if (field === "pedestrian_visible") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.pedestrian_visible = parsed;
      return;
    }
    patch.pedestrian_visible = includesAny(value, ["보행자", "사람", "보임", "있음"]);
    return;
  }
  if (field === "centerline_crossed") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.centerline_crossed = parsed;
      return;
    }
    patch.centerline_crossed = includesAny(value, ["중앙선", "황색", "넘", "침범", "물고"]);
    return;
  }
  if (field === "centerline_cross_reason") {
    patch.centerline_cross_reason = normalizeCenterlineReason(value);
    if (patch.centerline_cross_reason) patch.centerline_crossed = true;
    return;
  }
  if (field === "road_obstruction") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.road_obstruction = parsed;
      return;
    }
    patch.road_obstruction = includesAny(value, ["장애", "사물", "차선 침범", "막고"]);
    return;
  }
  if (field === "illegal_parking_obstruction") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.illegal_parking_obstruction = parsed;
      return;
    }
    patch.illegal_parking_obstruction = includesAny(value, ["불법", "주정차", "주차"]);
    return;
  }
  if (field === "opposing_vehicle_present") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.opposing_vehicle_present = parsed;
      return;
    }
    patch.opposing_vehicle_present = includesAny(value, ["마주", "대향", "반대편", "상대 차량"]);
    return;
  }
  if (field === "opposing_vehicle_did_not_stop") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.opposing_vehicle_did_not_stop = parsed;
      return;
    }
    patch.opposing_vehicle_did_not_stop = includesAny(value, ["멈추지", "감속 안", "그대로", "정지 안"]);
    return;
  }
  if (field === "secondary_collision") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.secondary_collision = parsed;
      return;
    }
    patch.secondary_collision = includesAny(value, ["2차", "후속", "뒤차", "추가 충돌"]);
    return;
  }
  if (field === "turn_signal") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.turn_signal = parsed;
      return;
    }
    patch.turn_signal = includesAny(value, ["켰음", "켰"]);
    return;
  }
  if (field === "signal_state") {
    patch.signal_state = normalizeSignal(value);
    if (includesAny(value, ["상대 신호위반"])) patch.opponent_signal_violation = true;
    return;
  }
  if (field === "user_signal") {
    patch.user_signal = normalizeSignal(value);
    if (patch.user_signal === "red") patch.user_signal_violation = true;
    if (patch.user_signal === "green") patch.user_signal_violation = false;
    return;
  }
  if (field === "opponent_signal") {
    patch.opponent_signal = normalizeSignal(value);
    if (patch.opponent_signal === "red") patch.opponent_signal_violation = true;
    if (patch.opponent_signal === "green") patch.opponent_signal_violation = false;
    return;
  }
  if (field === "pedestrian_signal") {
    patch.pedestrian_signal = normalizeSignal(value);
    return;
  }
  if (field === "lane_change_actor") {
    patch.lane_change_actor = value;
    patch.lane_change = true;
    if (value.trim().toLowerCase() === "user") {
      patch.my_lane_change = true;
      patch.opponent_lane_change = false;
      return;
    }
    if (["opponent", "other", "target", "other_vehicle"].includes(value.trim().toLowerCase())) {
      patch.opponent_lane_change = true;
      patch.my_lane_change = false;
      return;
    }
    if (includesAny(value, ["내 차량"])) {
      patch.my_lane_change = true;
      patch.opponent_lane_change = false;
    } else if (includesAny(value, ["상대 차량"])) {
      patch.opponent_lane_change = true;
      patch.my_lane_change = false;
    }
    return;
  }
  if (field === "opponent_behavior") {
    patch.opponent_behavior = normalizeOpponentBehavior(value);
    return;
  }
  if (field === "opponent_signal_violation") {
    const parsed = parseBooleanLike(value);
    if (parsed !== undefined) {
      patch.opponent_signal_violation = parsed;
      return;
    }
    patch.opponent_signal_violation = includesAny(value, ["예", "맞음", "위반"]);
    return;
  }
  if (field === "accident_type") {
    patch.accident_type = mapAccidentType(value);
    return;
  }
  patch[field] = value;
}

function normalizeSignal(value: string) {
  const lowered = value.trim().toLowerCase();
  if (["green", "go"].includes(lowered)) return "green";
  if (["yellow", "amber"].includes(lowered)) return "yellow";
  if (["red", "stop"].includes(lowered)) return "red";
  if (["flashing", "blink"].includes(lowered)) return "flashing";
  if (["none", "no_signal", "no signal"].includes(lowered)) return "none";
  if (includesAny(value, ["녹색", "초록"])) return "green";
  if (includesAny(value, ["황색"])) return "yellow";
  if (includesAny(value, ["적색", "빨간불"])) return "red";
  if (includesAny(value, ["비보호", "점멸"])) return "flashing";
  if (includesAny(value, ["신호등 없음"])) return "none";
  return value;
}

function mapAccidentType(value: string) {
  const lowered = value.trim().toLowerCase();
  if ([
    "rear_end_collision",
    "lane_change_collision",
    "intersection_signal_violation",
    "pedestrian_crosswalk_accident",
    "bicycle_collision",
    "object_collision",
    "single_vehicle_accident",
  ].includes(lowered)) return lowered;
  if (includesAny(value, ["후미"])) return "rear_end_collision";
  if (includesAny(value, ["차선"])) return "lane_change_collision";
  if (includesAny(value, ["교차"])) return "intersection_signal_violation";
  if (includesAny(value, ["보행"])) return "pedestrian_crosswalk_accident";
  if (includesAny(value, ["자전거"])) return "bicycle_collision";
  if (includesAny(value, ["시설물"])) return "object_collision";
  if (includesAny(value, ["단독"])) return "single_vehicle_accident";
  return value;
}

function normalizeOpponentBehavior(value: string) {
  const lowered = value.trim().toLowerCase();
  if (["rear_collision", "rear_vehicle_collision", "rear_end", "rear_end_collision"].includes(lowered)) return "rear_collision";
  if (["lane_change", "cut_in", "opponent_lane_change"].includes(lowered)) return "lane_change";
  if (["signal_violation", "red_light_violation"].includes(lowered)) return "signal_violation";
  if (includesAny(value, ["뒤에서 추돌", "후미", "후방", "추돌"])) return "rear_collision";
  if (includesAny(value, ["차선 변경", "차선변경", "끼어들기"])) return "lane_change";
  if (includesAny(value, ["신호 위반", "신호위반"])) return "signal_violation";
  return value;
}

function normalizeCollisionPartnerType(value: string) {
  const lowered = value.trim().toLowerCase();
  if (["vehicle", "car", "truck", "bus", "van", "motor_vehicle", "other_vehicle"].includes(lowered)) return "vehicle";
  if (["pedestrian", "person"].includes(lowered)) return "pedestrian";
  if (["bicycle", "bike", "cyclist"].includes(lowered)) return "bicycle";
  if (["motorcycle", "two_wheeler", "two-wheeler"].includes(lowered)) return "motorcycle";
  if (["object", "fixed_object", "road_object", "obstacle"].includes(lowered)) return "object";
  if (includesAny(value, ["차량", "승용", "트럭", "버스"])) return "vehicle";
  if (includesAny(value, ["보행자", "사람"])) return "pedestrian";
  if (includesAny(value, ["자전거"])) return "bicycle";
  if (includesAny(value, ["오토바이", "이륜"])) return "motorcycle";
  if (includesAny(value, ["물체", "시설물", "장애물"])) return "object";
  return value;
}

function normalizeCenterlineReason(value: string) {
  const lowered = value.trim().toLowerCase();
  if (["parked_vehicle_obstruction", "illegal_parking_obstruction"].includes(lowered)) return "parked_vehicle_obstruction";
  if (["road_obstruction", "obstacle"].includes(lowered)) return "road_obstruction";
  if (lowered === "lane_departure") return "lane_departure";
  if (includesAny(value, ["불법", "주정차", "주차"])) return "parked_vehicle_obstruction";
  if (includesAny(value, ["장애", "사물", "막고", "침범"])) return "road_obstruction";
  if (includesAny(value, ["이탈"])) return "lane_departure";
  return value;
}

function isUnknown(value: string) {
  const lowered = value.trim().toLowerCase();
  if (["unknown", "unclear", "not_sure", "not sure"].includes(lowered)) return true;
  return UNKNOWN_VALUES.some((item) => value.includes(item));
}

function includesAny(value: string, words: string[]) {
  return words.some((word) => value.includes(word));
}

function parseBooleanLike(value: string): boolean | undefined {
  const lowered = value.trim().toLowerCase();
  if (["true", "yes", "y", "1", "observed", "detected"].includes(lowered)) return true;
  if (["false", "no", "n", "0", "not_observed", "not observed", "none"].includes(lowered)) return false;
  return undefined;
}

function unique(values: any[]) {
  return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)));
}
