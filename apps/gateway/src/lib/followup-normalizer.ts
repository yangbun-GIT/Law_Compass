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
    patch.injury = !includesAny(value, ["없음", "아님"]);
    return;
  }
  if (field === "stopped") {
    patch.stopped = includesAny(value, ["정차", "멈춰"]);
    if (includesAny(value, ["급정거"])) patch.sudden_brake = true;
    else if (patch.stopped) patch.sudden_brake = false;
    return;
  }
  if (field === "sudden_brake") {
    patch.sudden_brake = !includesAny(value, ["없음"]);
    return;
  }
  if (field === "school_zone") {
    patch.school_zone = includesAny(value, ["맞음", "어린이보호구역"]);
    return;
  }
  if (field === "victim_is_child") {
    patch.victim_is_child = includesAny(value, ["미만", "어린이"]);
    return;
  }
  if (field === "crosswalk_nearby") {
    patch.crosswalk_nearby = !includesAny(value, ["아님"]);
    return;
  }
  if (field === "turn_signal") {
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
    if (includesAny(value, ["내 차량"])) {
      patch.my_lane_change = true;
      patch.opponent_lane_change = false;
    } else if (includesAny(value, ["상대 차량"])) {
      patch.opponent_lane_change = true;
      patch.my_lane_change = false;
    }
    return;
  }
  if (field === "accident_type") {
    patch.accident_type = mapAccidentType(value);
    return;
  }
  patch[field] = value;
}

function normalizeSignal(value: string) {
  if (includesAny(value, ["녹색", "초록"])) return "green";
  if (includesAny(value, ["황색"])) return "yellow";
  if (includesAny(value, ["적색", "빨간불"])) return "red";
  if (includesAny(value, ["비보호", "점멸"])) return "flashing";
  if (includesAny(value, ["신호등 없음"])) return "none";
  return value;
}

function mapAccidentType(value: string) {
  if (includesAny(value, ["후미"])) return "rear_end_collision";
  if (includesAny(value, ["차선"])) return "lane_change_collision";
  if (includesAny(value, ["교차"])) return "intersection_signal_violation";
  if (includesAny(value, ["보행"])) return "pedestrian_crosswalk_accident";
  if (includesAny(value, ["자전거"])) return "bicycle_collision";
  if (includesAny(value, ["시설물"])) return "object_collision";
  if (includesAny(value, ["단독"])) return "single_vehicle_accident";
  return value;
}

function isUnknown(value: string) {
  return UNKNOWN_VALUES.some((item) => value.includes(item));
}

function includesAny(value: string, words: string[]) {
  return words.some((word) => value.includes(word));
}

function unique(values: any[]) {
  return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)));
}
