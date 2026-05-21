const INTERNAL_MAP = {
    rear_end_collision: "후미추돌 사고",
    school_zone_child_accident: "어린이보호구역 사고",
    intersection_signal_violation: "교차로 신호위반 사고",
    lane_change_collision: "차선변경 사고",
    pedestrian_crosswalk_accident: "보행자 사고",
    bicycle_collision: "차대자전거 사고",
    object_collision: "차대기물 사고",
    single_vehicle_accident: "차량단독 사고",
    car_vs_car: "차대차 사고",
    car_vs_person: "차대사람 사고",
    car_vs_bicycle: "차대자전거 사고",
    car_vs_object: "차대기물 사고",
    single_vehicle: "차량단독 사고",
    REAR_END_SAFE_DISTANCE: "앞차와 안전거리를 지켜야 하는 의무",
    ROAD_ACCIDENT_REPORTING_DUTY: "사고가 났을 때 정차하고 필요한 조치를 해야 하는 의무",
    SAFE_DRIVING_DUTY: "주변 상황을 살피며 안전하게 운전해야 하는 의무",
    SIGNAL_VIOLATION: "신호를 지켜야 하는 의무",
    LANE_CHANGE_CAUTION: "차선을 바꿀 때 주변 차량을 살펴야 하는 의무",
    CROSSWALK_PEDESTRIAN_PROTECTION: "횡단보도에서 보행자를 보호해야 하는 의무",
    SCHOOL_ZONE_CHILD_PROTECTION: "어린이보호구역에서 더 주의해서 운전해야 하는 의무",
    TWELVE_GROSS_NEGLIGENCE: "중대한 교통법규 위반 여부 확인",
    HIT_AND_RUN_RISK: "사고 후 필요한 조치를 하지 않았는지 확인"
};
const TECHNICAL_KEYS = new Set(["model_info", "technical_model_info", "scenario_classifier", "retrieval", "cache_key", "evidence_cache_key", "chunk_id", "score", "rag_top_k", "ai_profile", "llm_enabled", "orchestrator", "security_flags", "scenario_tags", "scenario_type", "document_id", "source_uri", "claim_evidence", "claim_id", "evidence_refs", "required_evidence_family", "support_level", "unsupported_claims"]);
const BAD_PATTERNS = [/\?\?+/g, /\b[a-z]+(?:_[a-z0-9]+)+\b/g, /\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g, /score\s*[:=]?\s*\d+(\.\d+)?/gi, /chunk[_ ]?id\s*[:=]?\s*[\w-]+/gi, /model[_ ]?info/gi];
export function shouldHideTechnicalKey(key) { return TECHNICAL_KEYS.has(key); }
export function mapInternalCodeToKorean(value) { return INTERNAL_MAP[value] || value; }
export function hasBadDebugText(value) {
    const text = typeof value === "string" ? value : JSON.stringify(value ?? "");
    return /\?\?+|chunk_id|score|model_info|cache_key|rag_top_k|ai_profile|llm_enabled|orchestrator|scenario_classifier|rear_end_collision|REAR_END_SAFE_DISTANCE|ROAD_ACCIDENT_REPORTING_DUTY|"injury"\s*:|"stopped"\s*:|"weather"\s*:/i.test(text);
}
export function sanitizeDisplayText(value) {
    if (value === null || value === undefined)
        return "";
    if (typeof value === "boolean")
        return value ? "예" : "아니오";
    let text = String(value).trim();
    if (!text || text === "null" || text === "undefined")
        return "";
    if ((text.startsWith("{") && text.endsWith("}")) || (text.startsWith("[") && text.endsWith("]")))
        return "";
    text = mapInternalCodeToKorean(text);
    text = text.replace(/\bmedium\b/gi, "보통").replace(/\bhigh\b/gi, "높음").replace(/\blow\b/gi, "낮음").replace(/unknown|모름/gi, "확인이 필요합니다");
    for (const pattern of BAD_PATTERNS)
        text = text.replace(pattern, "");
    return text.replace(/\s+/g, " ").trim() || "확인이 필요합니다";
}
export function removeTechnicalFields(obj) {
    if (Array.isArray(obj))
        return obj.map(removeTechnicalFields).filter((x) => x !== undefined);
    if (obj && typeof obj === "object") {
        const out = {};
        for (const [key, value] of Object.entries(obj)) {
            if (shouldHideTechnicalKey(key))
                continue;
            const safe = removeTechnicalFields(value);
            if (safe !== undefined && safe !== "")
                out[key] = safe;
        }
        return out;
    }
    if (typeof obj === "string")
        return sanitizeDisplayText(obj);
    if (obj === null || obj === undefined)
        return undefined;
    return obj;
}
