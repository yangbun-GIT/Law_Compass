import type { AccidentFacts } from "../api/client";
import { GUIDED_QUESTION_SETS, unknownGuidedQuestions, type GuidedQuestion, type GuidedQuestionType } from "../data/caseWorkspaceGuidanceData";

function includesAny(text: string, keywords: string[]) {
    return keywords.some((keyword) => text.includes(keyword));
}

function normalizeAccidentText(input: string) {
    return String(input || "")
        .replaceAll("눚은밤", "늦은 밤")
        .replaceAll("늦은밤", "늦은 밤")
        .replaceAll("부딛", "부딪")
        .replaceAll("부딧", "부딪")
        .replaceAll("상태였가", "상태였다")
        .replaceAll("정차중", "정차 중")
        .replaceAll("신호대기중", "신호대기 중")
        .toLowerCase()
        .trim();
}

function isStealthParkedVehicleCollision(facts: AccidentFacts, descriptionText: string) {
    const description = normalizeAccidentText(descriptionText);
    const factsText = JSON.stringify(facts || {}).toLowerCase();
    const haystack = `${description} ${factsText}`;

    const hasVehicle = includesAny(haystack, ["트럭", "화물차", "차량", "상대차", "상대 차량", "앞차", "승용차"]);
    const hasParkedOrStopped = includesAny(haystack, ["주차", "정차", "방치", "세워", "서 있", "서있", "화단", "갓길"]);
    const hasStealthOrLowVisibility = includesAny(haystack, [
        "스텔스",
        "무등화",
        "등화 없이",
        "미등",
        "비상등",
        "차폭등",
        "불빛",
        "어두",
        "야간",
        "밤",
        "새벽",
        "교량 밑",
        "교량밑",
        "교량 아래",
    ]);
    const hasImpact = includesAny(haystack, ["부딪", "충돌", "들이받", "들이박", "박", "파손", "폐차"]);
    const hasDrunk = includesAny(haystack, ["음주", "음주운전", "만취", "술"]);

    return hasVehicle && hasParkedOrStopped && hasImpact && (hasStealthOrLowVisibility || hasDrunk);
}

function inferRearEndRole(facts: AccidentFacts, descriptionText: string) {
    const description = normalizeAccidentText(descriptionText);

    const role = String(
        (facts as any).rear_end_role ||
        (facts as any).collision_role ||
        (facts as any).impact_role ||
        ""
    ).toLowerCase();

    if (
        role.includes("ego_hit_front") ||
        role.includes("i_hit_front") ||
        role.includes("striking") ||
        role.includes("following_vehicle")
    ) {
        return "ego_hit_front";
    }

    if (role.includes("hit_by_rear") || role.includes("struck") || role.includes("front_vehicle")) {
        return "hit_by_rear";
    }

    const egoHitFrontKeywords = [
        "앞차를 들이",
        "앞차 들이",
        "앞차를 박",
        "앞차 박",
        "앞차 추돌",
        "전방 차량 추돌",
        "선행 차량 추돌",
        "내가 들이",
        "내 차가 앞차",
        "내 차량이 앞차",
        "내차가 앞차",
        "들이박",
        "들이 받",
        "추돌했다",
        "추돌하였습니다",
    ];

    const hitByRearKeywords = [
        "뒤차가 들이",
        "뒤차가 박",
        "뒷차가 들이",
        "뒷차가 박",
        "뒤에서 받",
        "뒤에서 박",
        "후방에서 추돌",
        "후미를 추돌당",
        "내 차는 정차",
        "내차는 정차",
        "정차 중 뒤",
        "정차중 뒤",
        "신호대기 중 뒤",
        "신호대기중 뒤",
    ];

    if (includesAny(description, egoHitFrontKeywords)) return "ego_hit_front";
    if (includesAny(description, hitByRearKeywords)) return "hit_by_rear";
    return "unknown";
}

function inferGuidedQuestionType(facts: AccidentFacts, descriptionText: string): GuidedQuestionType {
    const accidentType = String((facts as any).accident_type || "").toLowerCase();
    const partyType = String((facts as any).accident_party_type || "").toLowerCase();
    const kniaMajorPartyType = String((facts as any).knia_major_party_type || "").toLowerCase();
    const collisionPartnerType = String((facts as any).collision_partner_type || "").toLowerCase();
    const description = normalizeAccidentText(descriptionText);

    if (
        accidentType.includes("stealth_illegal_parked_vehicle") ||
        (facts as any).is_stealth_parked_vehicle_collision === true ||
        isStealthParkedVehicleCollision(facts, descriptionText)
    ) {
        return "stealth_parked_vehicle";
    }

    const hasObjectCollisionText =
        includesAny(description, [
            "스텔스",
            "무등화",
            "미등",
            "비상등",
            "차폭등",
            "교량 밑",
            "교량밑",
            "교량 아래",
            "화단",
            "주차",
            "정차",
            "트럭",
            "화물차",
            "시설물",
            "가드레일",
            "전봇대",
            "중앙분리대",
            "낙하물",
            "적재물",
        ]) && includesAny(description, ["부딪", "충돌", "박", "들이받", "들이박", "파손", "폐차"]);

    if (
        accidentType.includes("parked_vehicle_collision") ||
        accidentType.includes("object_collision") ||
        partyType.includes("car_vs_parked_vehicle") ||
        partyType.includes("car_vs_object") ||
        collisionPartnerType === "object" ||
        hasObjectCollisionText
    ) {
        return "object_collision";
    }

    if (
        accidentType.includes("pedestrian") ||
        partyType.includes("car_vs_person") ||
        kniaMajorPartyType.includes("car_vs_person") ||
        collisionPartnerType === "pedestrian" ||
        description.includes("보행자") ||
        description.includes("사람") ||
        description.includes("횡단보도")
    ) {
        return "pedestrian";
    }

    if (
        accidentType.includes("bicycle") ||
        partyType.includes("car_vs_bicycle") ||
        kniaMajorPartyType.includes("car_vs_bicycle") ||
        collisionPartnerType === "bicycle" ||
        description.includes("자전거")
    ) {
        return "bicycle";
    }

    if (
        accidentType.includes("single_vehicle") ||
        partyType.includes("single_vehicle") ||
        kniaMajorPartyType.includes("single_vehicle") ||
        description.includes("단독사고") ||
        description.includes("혼자") ||
        description.includes("전복") ||
        description.includes("도로 이탈") ||
        description.includes("미끄러")
    ) {
        return "single_vehicle";
    }

    if (
        accidentType.includes("lane_change") ||
        description.includes("차선변경") ||
        description.includes("진로변경") ||
        description.includes("끼어들") ||
        description.includes("방향지시등") ||
        description.includes("깜빡이")
    ) {
        return "lane_change";
    }

    if (
        accidentType.includes("intersection") ||
        description.includes("교차로") ||
        description.includes("신호위반") ||
        description.includes("좌회전") ||
        description.includes("우회전")
    ) {
        return "intersection";
    }

    if (
        accidentType.includes("rear_end") ||
        description.includes("후미추돌") ||
        description.includes("추돌") ||
        description.includes("앞차") ||
        description.includes("뒤차") ||
        description.includes("뒷차")
    ) {
        const rearEndRole = inferRearEndRole(facts, descriptionText);
        if (rearEndRole === "ego_hit_front") return "ego_hit_front";
        if (rearEndRole === "hit_by_rear") return "hit_by_rear";
        return "rear_end_unknown";
    }

    return "unknown";
}

export function getFallbackGuidedQuestions(facts: AccidentFacts, descriptionText: string): GuidedQuestion[] {
    const type = inferGuidedQuestionType(facts, descriptionText);
    return GUIDED_QUESTION_SETS[type] || unknownGuidedQuestions;
}
