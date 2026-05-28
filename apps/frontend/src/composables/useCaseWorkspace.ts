import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { api, formatApiError, type AccidentFacts, type CaseItem, type UploadItem } from "../api/client";

export type CaseWorkspaceBusyState = "" | "save" | "upload" | "preprocess" | "text-analysis" | "video-analysis";

type JobItem = {
    id: string;
    type: string;
    status: string;
    attempts?: number;
    attempt?: number;
};

type GuidedChoice = {
    value: string;
    label: string;
};

type GuidedQuestion = {
    question_id: string;
    title: string;
    plain_question: string;
    why_it_matters: string;
    choices: GuidedChoice[];
    fact_key: string;
};

type GuidedQuestionType =
    | "rear_end"
    | "ego_hit_front"
    | "hit_by_rear"
    | "rear_end_unknown"
    | "stealth_parked_vehicle"
    | "object_collision"
    | "pedestrian"
    | "lane_change"
    | "intersection"
    | "bicycle"
    | "single_vehicle"
    | "unknown";

const DEFAULT_KEYWORDS = ["블랙박스", "과실비율", "교통사고", "보험처리"];
const RUNNING_JOB_STATUSES = ["queued", "running", "retrying", "processing", "analyzing"];
const FINISHED_JOB_STATUSES = ["completed", "succeeded", "success", "done", "finished"];
const FAILED_JOB_STATUSES = ["failed", "error", "cancelled", "canceled"];
const REPORT_READY_RETRY_LIMIT = 30;
const REPORT_READY_RETRY_DELAY_MS = 1000;

const DEFAULT_PROGRESS_STEPS = [
    { key: "input", label: "입력 정리", percent: 15 },
    { key: "upload", label: "영상 확인", percent: 30 },
    { key: "scene", label: "사고 장면 확인", percent: 45 },
    { key: "scenario", label: "사고유형 판단", percent: 60 },
    { key: "knia", label: "KNIA 과실 기준 검색", percent: 75 },
    { key: "adjustment", label: "가감요소 계산", percent: 88 },
    { key: "result", label: "결과 정리", percent: 100 },
];

export const guidedAccidentTypeOptions = [
    {
        label: "차대차 사고",
        scenario_type: "general_vehicle_collision",
        accident_party_type: "car_vs_car",
        hint: "자동차, 트럭, 버스, 주차·정차 차량 등 차량과 차량 사이의 사고",
    },
    {
        label: "야간 스텔스 주차·정차 차량과 충돌",
        scenario_type: "stealth_illegal_parked_vehicle_collision",
        accident_party_type: "car_vs_car",
        hint: "밤, 교량 아래, 무등화, 스텔스, 화단·갓길 정차 차량과 부딪힌 경우",
    },
    {
        label: "뒤에서 들이받은 사고",
        scenario_type: "rear_end_collision",
        accident_party_type: "car_vs_car",
        hint: "내 차를 뒤차가 추돌했거나, 내 차가 앞차를 추돌한 경우",
    },
    {
        label: "교차로에서 부딪힌 사고",
        scenario_type: "intersection_collision",
        accident_party_type: "car_vs_car",
        hint: "직진, 좌회전, 우회전 중 충돌한 경우",
    },
    {
        label: "신호위반이 관련된 사고",
        scenario_type: "intersection_signal_violation",
        accident_party_type: "car_vs_car",
        hint: "빨간불 진입이나 신호 확인이 핵심인 경우",
    },
    {
        label: "차선변경 중 부딪힌 사고",
        scenario_type: "lane_change_collision",
        accident_party_type: "car_vs_car",
        hint: "끼어들기, 진로변경, 방향지시등이 쟁점인 경우",
    },
    {
        label: "차대사람 사고",
        scenario_type: "pedestrian_crosswalk_accident",
        accident_party_type: "car_vs_person",
        hint: "보행자, 횡단보도, 어린이보호구역 등이 관련된 경우",
    },
    {
        label: "차대자전거 사고",
        scenario_type: "bicycle_collision",
        accident_party_type: "car_vs_bicycle",
        hint: "자전거와 직접 충돌한 경우",
    },
    {
        label: "차대기물 사고",
        scenario_type: "object_collision",
        accident_party_type: "car_vs_object",
        hint: "가드레일, 전봇대, 벽, 낙하물, 시설물과 충돌한 경우",
    },
    {
        label: "차량단독 사고",
        scenario_type: "single_vehicle_accident",
        accident_party_type: "single_vehicle",
        hint: "다른 차량·사람·자전거 없이 내 차량만 사고가 난 경우",
    },
    {
        label: "잘 모르겠어요",
        scenario_type: "",
        accident_party_type: "unknown",
        hint: "설명과 영상으로 가장 가능성 높은 KNIA 대분류를 추정합니다.",
    },
];

export const guidedAnalysisModes = [
    { value: "quick_summary", label: "빠른 요약", hint: "핵심 결론과 과실비율만 짧게 봅니다." },
    { value: "fault_ratio_focused", label: "과실비율 중심", hint: "급정거, 제동등, 정차 위치 같은 가감요소를 자세히 확인합니다." },
    { value: "legal_precedent_focused", label: "법률/판례 근거 중심", hint: "관련 법규, KNIA 해설, 판례 부족 여부를 함께 봅니다." },
    { value: "insurance_response_focused", label: "보험 대응 중심", hint: "보험사에 말할 핵심 문장과 챙길 자료를 정리합니다." },
    { value: "full_deep_research", label: "전체 심층 리서치 분석", hint: "사실, 영상, KNIA, 법률, 보험 대응을 모두 펼쳐 봅니다." },
];

export const rearEndGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "rear_end.stopped",
        title: "정차 여부",
        plain_question: "내 차가 사고 직전에 완전히 멈춰 있었나요?",
        why_it_matters: "정상적으로 멈춰 있던 앞차를 뒤차가 들이받은 사고라면 뒤차 책임을 크게 봅니다.",
        choices: [
            { value: "yes", label: "예" },
            { value: "no", label: "아니오" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "stopped",
    },
    {
        question_id: "rear_end.stop_reason",
        title: "정차한 이유",
        plain_question: "왜 멈춰 있었나요?",
        why_it_matters: "빨간불 신호대기, 정체, 보행자 회피처럼 정당한 이유가 있으면 내 과실을 올리지 않는 쪽으로 봅니다.",
        choices: [
            { value: "red_light", label: "빨간불 신호대기" },
            { value: "traffic", label: "앞차 정체" },
            { value: "pedestrian_or_obstacle", label: "보행자/장애물 때문에 정지" },
            { value: "no_reason", label: "이유 없이 갑자기 정지" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "stop_reason",
    },
    {
        question_id: "rear_end.brake_light",
        title: "브레이크등",
        plain_question: "브레이크등이 정상적으로 켜졌나요?",
        why_it_matters: "브레이크등 고장은 내 과실이 일부 생길 수 있는 요소입니다.",
        choices: [
            { value: "normal", label: "정상 작동" },
            { value: "failed", label: "고장 또는 미점등" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "brake_light",
    },
];

export const rearHitByOtherGuidedQuestions: GuidedQuestion[] = rearEndGuidedQuestions;

export const egoHitFrontVehicleGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "ego_rear_end.front_vehicle_status",
        title: "앞차 상태",
        plain_question: "앞차가 사고 직전에 어떤 상태였나요?",
        why_it_matters: "내 차가 앞차를 들이받은 사고에서는 앞차가 정상 정차였는지, 급정거였는지가 과실비율에 중요합니다.",
        choices: [
            { value: "normal_stop", label: "신호대기·정체 등 정상 정차" },
            { value: "sudden_stop", label: "갑자기 급정거" },
            { value: "moving_slowly", label: "서행 중" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "front_vehicle_status",
    },
    {
        question_id: "ego_rear_end.stop_reason",
        title: "앞차 정차 이유",
        plain_question: "앞차가 멈춘 이유가 확인되나요?",
        why_it_matters: "빨간불, 정체, 보행자 회피처럼 정당한 이유가 있으면 앞차 과실을 크게 보지 않습니다.",
        choices: [
            { value: "red_light", label: "빨간불 신호대기" },
            { value: "traffic", label: "앞차 정체" },
            { value: "pedestrian_or_obstacle", label: "보행자·장애물 때문에 정지" },
            { value: "no_reason", label: "이유 없이 갑자기 정지" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "front_stop_reason",
    },
    {
        question_id: "ego_rear_end.brake_light",
        title: "앞차 브레이크등",
        plain_question: "앞차 브레이크등이 정상적으로 켜졌나요?",
        why_it_matters: "앞차 브레이크등이 고장 또는 미점등이면 앞차 과실이 일부 검토될 수 있습니다.",
        choices: [
            { value: "normal", label: "정상 작동" },
            { value: "failed", label: "고장 또는 미점등" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "front_brake_light",
    },
    {
        question_id: "ego_rear_end.following_distance",
        title: "안전거리",
        plain_question: "앞차와의 거리가 충분했나요?",
        why_it_matters: "내 차가 앞차를 들이받은 사고에서는 안전거리 미확보가 기본 과실 판단에 크게 반영됩니다.",
        choices: [
            { value: "enough", label: "충분했습니다" },
            { value: "not_enough", label: "가까웠습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "following_distance",
    },
    {
        question_id: "ego_rear_end.avoidance",
        title: "회피 가능성",
        plain_question: "앞차를 발견한 뒤 브레이크를 밟거나 피할 시간이 있었나요?",
        why_it_matters: "회피 가능성이 있었는지는 내 과실과 가감요소 판단에 중요합니다.",
        choices: [
            { value: "no_time", label: "발견하자마자 바로 충돌했습니다" },
            { value: "some_time", label: "조금은 시간이 있었습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "rear_end_avoidance_time",
    },
];

const rearEndUnknownGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "rear_end.role",
        title: "추돌 방향",
        plain_question: "이번 사고는 어느 쪽에 더 가까운가요?",
        why_it_matters: "내가 앞차를 들이받은 사고인지, 정차 중인 내 차를 뒤차가 들이받은 사고인지에 따라 질문과 과실 판단이 달라집니다.",
        choices: [
            { value: "ego_hit_front", label: "내 차가 앞차를 들이받았습니다" },
            { value: "hit_by_rear", label: "내 차를 뒤차가 들이받았습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "rear_end_role",
    },
];

export const stealthParkedVehicleGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "stealth_parked_vehicle.target",
        title: "충돌 대상",
        plain_question: "충돌한 대상은 주차 또는 정차된 차량이었나요?",
        why_it_matters: "야간에 정차·방치된 차량과의 충돌은 단순 시설물 충돌과 과실 판단 축이 다릅니다.",
        choices: [
            { value: "parked_truck", label: "주차·정차된 트럭 또는 화물차" },
            { value: "parked_vehicle", label: "주차·정차된 일반 차량" },
            { value: "fixed_object", label: "화단·기둥·벽 같은 시설물" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "stealth_collision_target",
    },
    {
        question_id: "stealth_parked_vehicle.position",
        title: "상대 차량 위치",
        plain_question: "상대 차량은 정상 주차구역이 아닌 위험한 위치에 있었나요?",
        why_it_matters: "화단, 교량 아래, 통행 공간 침범, 갓길 방치 여부는 상대 과실을 올리는 핵심 요소입니다.",
        choices: [
            { value: "under_bridge_flowerbed", label: "교량 아래 화단 또는 구조물 부근" },
            { value: "traffic_space", label: "통행 공간에 걸쳐 있었습니다" },
            { value: "roadside_or_shoulder", label: "도로 가장자리 또는 갓길" },
            { value: "normal_parking", label: "정상 주차구역" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "stealth_parked_position",
    },
    {
        question_id: "stealth_parked_vehicle.lighting",
        title: "등화와 식별 가능성",
        plain_question: "상대 차량의 미등, 비상등, 차폭등 등 식별 조치가 있었나요?",
        why_it_matters: "야간 스텔스 상태는 후속 차량의 발견 가능성을 낮추고 상대 과실을 크게 올릴 수 있습니다.",
        choices: [
            { value: "unlit_stealth", label: "등화 없이 스텔스 상태였습니다" },
            { value: "hazard_only", label: "비상등만 켜져 있었습니다" },
            { value: "lights_on", label: "식별 가능한 등화가 있었습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "stealth_lighting",
    },
    {
        question_id: "stealth_parked_vehicle.visibility",
        title: "시야와 조도",
        plain_question: "사고 장소가 야간 또는 교량 아래처럼 발견하기 어려운 환경이었나요?",
        why_it_matters: "교량 아래 조도 불량, 야간, 그림자 구간은 내 차량의 회피 가능성을 낮추는 요소입니다.",
        choices: [
            { value: "under_bridge_dark", label: "교량 아래라 매우 어두웠습니다" },
            { value: "night_dark", label: "야간이고 주변이 어두웠습니다" },
            { value: "night_lit", label: "야간이지만 조명이 있었습니다" },
            { value: "daylight", label: "주간이었습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "stealth_visibility",
    },
    {
        question_id: "stealth_parked_vehicle.impairment",
        title: "상대 음주운전",
        plain_question: "상대 차량이 음주운전으로 인해 비정상 정차 또는 방치된 상태였나요?",
        why_it_matters: "음주운전 자체는 민사 100:0 자동 확정은 아니지만, 위험 상태를 만든 강한 가산 요소입니다.",
        choices: [
            { value: "drunk_confirmed", label: "음주운전이 확인되었습니다" },
            { value: "drunk_suspected", label: "음주운전이 의심됩니다" },
            { value: "not_drunk", label: "음주운전은 아닙니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "opponent_drunk_driving",
    },
    {
        question_id: "stealth_parked_vehicle.avoidability",
        title: "회피 가능성",
        plain_question: "상대 차량을 발견한 뒤 피하거나 감속할 시간이 있었나요?",
        why_it_matters: "발견 즉시 충돌한 수준이면 내 차량 과실을 낮추는 핵심 근거가 됩니다.",
        choices: [
            { value: "nearly_impossible", label: "발견하자마자 거의 바로 충돌했습니다" },
            { value: "limited", label: "조금 보였지만 피하기 어려웠습니다" },
            { value: "avoidable", label: "피할 시간이 어느 정도 있었습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "stealth_avoidability",
    },
];

export const objectCollisionGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "object.collision_object_type",
        title: "충돌 대상",
        plain_question: "부딪힌 대상은 무엇이었나요?",
        why_it_matters: "상대가 주차 차량인지, 고정 시설물인지, 떨어진 물체인지에 따라 과실 산정 기준이 달라집니다.",
        choices: [
            { value: "parked_vehicle", label: "주차 또는 정차된 차량" },
            { value: "fixed_object", label: "가드레일, 전봇대, 화단, 구조물 같은 고정 시설물" },
            { value: "fallen_or_movable_object", label: "낙하물, 적재물, 이동 가능한 물체" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "collision_object_type",
    },
    {
        question_id: "object.abnormal_parking",
        title: "비정상 주차 또는 정차 여부",
        plain_question: "상대 차량이나 물체가 정상적으로 예상하기 어려운 위치에 있었나요?",
        why_it_matters: "화단, 교량 아래, 통행 공간, 갓길, 어두운 곳에 비정상적으로 있었는지는 상대 과실을 높이는 핵심 요소입니다.",
        choices: [
            { value: "yes", label: "예, 정상 위치가 아니었습니다" },
            { value: "no", label: "아니요, 정상적으로 보이는 위치였습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "abnormal_parking",
    },
    {
        question_id: "object.visibility_issue",
        title: "시야와 등화 상태",
        plain_question: "사고 당시 충돌 대상을 미리 발견하기 어려웠나요?",
        why_it_matters: "야간 스텔스 상태, 미등·비상등 미점등, 교량 아래 조도 불량은 내 차의 회피 가능성을 낮추고 상대 과실을 높일 수 있습니다.",
        choices: [
            { value: "stealth_no_lights", label: "야간에 미등·비상등 없이 스텔스 상태였습니다" },
            { value: "hard_to_see", label: "교량 아래, 어두운 도로 등으로 보기 어려웠습니다" },
            { value: "visible", label: "충돌 대상은 비교적 잘 보였습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "visibility_issue",
    },
    {
        question_id: "object.road_environment",
        title: "도로 환경",
        plain_question: "사고 장소는 어떤 환경이었나요?",
        why_it_matters: "교량 아래, 화단 주변, 갓길, 어두운 도로 등은 통상적인 운전자가 장애물을 발견하기 어려운지 판단하는 데 중요합니다.",
        choices: [
            { value: "under_bridge", label: "교량 아래 또는 구조물 아래" },
            { value: "flowerbed_or_median", label: "화단, 중앙분리대, 구조물 주변" },
            { value: "roadside_or_shoulder", label: "도로 가장자리 또는 갓길" },
            { value: "normal_road", label: "일반 도로" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "road_environment",
    },
    {
        question_id: "object.avoidance_time",
        title: "회피 가능성",
        plain_question: "충돌 직전에 피하거나 멈출 시간이 있었나요?",
        why_it_matters: "발견 즉시 충돌했거나 피할 시간이 거의 없었다면 내 차 과실을 낮추는 중요한 근거가 됩니다.",
        choices: [
            { value: "avoidable", label: "피하거나 멈출 시간이 있었습니다" },
            { value: "limited", label: "발견했지만 피하기 어려웠습니다" },
            { value: "nearly_impossible", label: "거의 발견 즉시 충돌했습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "avoidance_time",
    },
];

export const pedestrianGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "pedestrian.crosswalk",
        title: "횡단보도 여부",
        plain_question: "보행자가 횡단보도나 보행자 신호 근처에 있었나요?",
        why_it_matters: "횡단보도와 보행자 신호는 보행자 사고 과실 판단에서 가장 중요한 요소입니다.",
        choices: [
            { value: "crosswalk", label: "횡단보도 위 또는 근처" },
            { value: "near_crosswalk", label: "횡단보도 근처" },
            { value: "not_crosswalk", label: "횡단보도 아님" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "crosswalk_context",
    },
    {
        question_id: "pedestrian.signal",
        title: "보행자 신호",
        plain_question: "보행자 신호나 차량 신호가 어떻게 되어 있었나요?",
        why_it_matters: "보행자 신호와 차량 신호는 보행자 사고의 기본 과실 판단에 직접 영향을 줍니다.",
        choices: [
            { value: "pedestrian_green", label: "보행자 신호가 초록불" },
            { value: "pedestrian_red", label: "보행자 신호가 빨간불" },
            { value: "no_signal", label: "신호등이 없었습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "pedestrian_signal",
    },
    {
        question_id: "pedestrian.visibility",
        title: "보행자 발견 가능성",
        plain_question: "보행자를 미리 볼 수 있었나요?",
        why_it_matters: "야간, 사각지대, 갑작스러운 진입은 운전자와 보행자 책임 판단에 영향을 줍니다.",
        choices: [
            { value: "visible", label: "미리 볼 수 있었습니다" },
            { value: "sudden", label: "갑자기 나타났습니다" },
            { value: "blocked_view", label: "차량이나 시설물 때문에 가려졌습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "pedestrian_visibility",
    },
];

export const laneChangeGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "lane_change.signal",
        title: "방향지시등",
        plain_question: "차선변경 차량이 방향지시등을 켰나요?",
        why_it_matters: "방향지시등 사용 여부는 차선변경 사고의 주요 가감요소입니다.",
        choices: [
            { value: "yes", label: "예" },
            { value: "no", label: "아니오" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "turn_signal",
    },
    {
        question_id: "lane_change.position",
        title: "충돌 위치",
        plain_question: "충돌은 차선변경 중인 차량의 어느 부분과 발생했나요?",
        why_it_matters: "앞부분, 옆부분, 뒷부분 충돌 위치는 선진입과 회피 가능성을 판단하는 데 중요합니다.",
        choices: [
            { value: "front_side", label: "앞쪽 또는 앞문 부근" },
            { value: "middle_side", label: "옆면 중앙" },
            { value: "rear_side", label: "뒷쪽 또는 뒷문 부근" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "impact_position",
    },
    {
        question_id: "lane_change.speed_difference",
        title: "속도 차이",
        plain_question: "상대 차량이 갑자기 끼어들었나요, 아니면 천천히 차선변경 중이었나요?",
        why_it_matters: "급차선변경인지, 충분히 예측 가능한 차선변경이었는지에 따라 과실 판단이 달라집니다.",
        choices: [
            { value: "sudden_cut_in", label: "갑자기 끼어들었습니다" },
            { value: "gradual", label: "천천히 변경 중이었습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "lane_change_manner",
    },
];

export const intersectionGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "intersection.signal",
        title: "신호 상태",
        plain_question: "내 차량과 상대 차량의 신호가 확인되나요?",
        why_it_matters: "교차로 사고는 신호 확인 여부가 과실비율을 크게 좌우합니다.",
        choices: [
            { value: "my_green", label: "내 신호가 초록불" },
            { value: "opponent_violation", label: "상대 신호위반으로 보임" },
            { value: "both_unknown", label: "둘 다 확실하지 않음" },
            { value: "no_signal", label: "신호등 없는 교차로" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "signal_context",
    },
    {
        question_id: "intersection.direction",
        title: "진행 방향",
        plain_question: "각 차량은 어떤 방향으로 움직이고 있었나요?",
        why_it_matters: "직진, 좌회전, 우회전 관계에 따라 적용되는 KNIA 기준이 달라집니다.",
        choices: [
            { value: "straight_vs_left", label: "직진 대 좌회전" },
            { value: "straight_vs_right", label: "직진 대 우회전" },
            { value: "crossing", label: "서로 교차 진행" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "intersection_movement",
    },
    {
        question_id: "intersection.priority",
        title: "진입 순서",
        plain_question: "누가 교차로에 먼저 진입했나요?",
        why_it_matters: "동시 진입인지 선진입인지에 따라 기본 과실과 가감요소가 달라질 수 있습니다.",
        choices: [
            { value: "me_first", label: "내 차가 먼저 진입" },
            { value: "opponent_first", label: "상대가 먼저 진입" },
            { value: "same_time", label: "거의 동시에 진입" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "intersection_entry_order",
    },
];

export const bicycleGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "bicycle.location",
        title: "자전거 위치",
        plain_question: "자전거는 어디로 이동하고 있었나요?",
        why_it_matters: "자전거도로, 차도, 횡단보도 주행 여부에 따라 과실 판단 기준이 달라집니다.",
        choices: [
            { value: "bike_lane", label: "자전거도로" },
            { value: "roadway", label: "차도" },
            { value: "crosswalk", label: "횡단보도" },
            { value: "sidewalk", label: "보도" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "bicycle_location",
    },
    {
        question_id: "bicycle.direction",
        title: "진행 방향",
        plain_question: "자전거와 차량은 같은 방향이었나요, 서로 교차했나요?",
        why_it_matters: "같은 방향 추월인지, 교차 충돌인지에 따라 적용 기준이 달라집니다.",
        choices: [
            { value: "same_direction", label: "같은 방향" },
            { value: "crossing", label: "서로 교차" },
            { value: "opposite", label: "마주보는 방향" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "bicycle_movement",
    },
];

export const singleVehicleGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "single_vehicle.cause",
        title: "단독 사고 원인",
        plain_question: "단독 사고의 직접 원인으로 보이는 것은 무엇인가요?",
        why_it_matters: "도로 결함, 낙하물, 시야장애, 운전 조작 실수 여부에 따라 보험·손해배상 쟁점이 달라집니다.",
        choices: [
            { value: "road_defect", label: "도로 파손·결빙·포트홀" },
            { value: "fallen_object", label: "낙하물 또는 장애물" },
            { value: "visibility", label: "야간·시야장애" },
            { value: "driver_control", label: "운전 조작 문제" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "single_vehicle_cause",
    },
    {
        question_id: "single_vehicle.evidence",
        title: "현장 증거",
        plain_question: "도로 상태나 장애물을 확인할 사진·영상이 있나요?",
        why_it_matters: "단독 사고는 외부 원인 입증 자료가 있어야 보상이나 책임 검토가 쉬워집니다.",
        choices: [
            { value: "yes", label: "예, 있습니다" },
            { value: "no", label: "아니오" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "external_cause_evidence",
    },
];

export const unknownGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "unknown.parties",
        title: "사고 상대",
        plain_question: "사고 상대는 무엇이었나요?",
        why_it_matters: "상대가 차량, 보행자, 자전거, 시설물인지에 따라 적용 기준이 달라집니다.",
        choices: [
            { value: "car", label: "다른 차량" },
            { value: "parked_vehicle", label: "주차된 차량" },
            { value: "person", label: "보행자" },
            { value: "bicycle", label: "자전거" },
            { value: "object", label: "시설물·물체" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "accident_counterpart",
    },
    {
        question_id: "unknown.location",
        title: "사고 장소",
        plain_question: "사고 장소는 어디에 가까웠나요?",
        why_it_matters: "교차로, 차선변경 구간, 횡단보도, 주차장 등 장소는 사고유형 추정에 중요합니다.",
        choices: [
            { value: "intersection", label: "교차로" },
            { value: "lane", label: "차로 주행 중" },
            { value: "crosswalk", label: "횡단보도 근처" },
            { value: "parking_or_roadside", label: "주차장·도로 가장자리" },
            { value: "under_bridge", label: "교량 아래" },
            { value: "flowerbed_or_median", label: "화단·중앙분리대 주변" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "accident_location_context",
    },
    {
        question_id: "unknown.time_visibility",
        title: "시간과 시야",
        plain_question: "야간, 비, 눈, 시야장애가 있었나요?",
        why_it_matters: "시야와 노면 상태는 회피 가능성과 주의의무 판단에 영향을 줍니다.",
        choices: [
            { value: "night_or_dark", label: "야간 또는 어두운 곳" },
            { value: "rain_snow", label: "비·눈·젖은 노면" },
            { value: "clear", label: "시야가 좋았습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "visibility_or_weather",
    },
];

const GUIDED_QUESTION_SETS: Record<GuidedQuestionType, GuidedQuestion[]> = {
    rear_end: rearEndGuidedQuestions,
    ego_hit_front: egoHitFrontVehicleGuidedQuestions,
    hit_by_rear: rearHitByOtherGuidedQuestions,
    rear_end_unknown: rearEndUnknownGuidedQuestions,
    stealth_parked_vehicle: stealthParkedVehicleGuidedQuestions,
    object_collision: objectCollisionGuidedQuestions,
    pedestrian: pedestrianGuidedQuestions,
    lane_change: laneChangeGuidedQuestions,
    intersection: intersectionGuidedQuestions,
    bicycle: bicycleGuidedQuestions,
    single_vehicle: singleVehicleGuidedQuestions,
    unknown: unknownGuidedQuestions,
};

export const caseKeywordPool = [
    "후미추돌",
    "안전거리",
    "신호위반",
    "교차로",
    "차선변경",
    "방향지시등",
    "횡단보도",
    "보행자",
    "자전거",
    "주차",
    "정차",
    "스텔스",
    "무등화",
    "야간",
    "교량 아래",
    "화단",
    "음주운전",
    "시야장애",
    "시설물",
    "단독사고",
    "어린이보호구역",
    "민식이법",
    "대인접수",
    "진단서",
];

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

function getFallbackGuidedQuestions(facts: AccidentFacts, descriptionText: string): GuidedQuestion[] {
    const type = inferGuidedQuestionType(facts, descriptionText);
    return GUIDED_QUESTION_SETS[type] || unknownGuidedQuestions;
}

function normalizeProgressStepLabel(step: any) {
    const key = String(step?.key ?? step?.stage ?? "").toLowerCase();

    const labels: Record<string, string> = {
        input: "입력 정리",
        upload: "영상 확인",
        scene: "사고 장면 확인",
        scenario: "사고유형 판단",
        knia: "KNIA 과실 기준 검색",
        adjustment: "가감요소 계산",
        result: "결과 정리",
    };

    const currentLabel = String(step?.label ?? step?.message ?? "");
    if (currentLabel.includes("??") || !currentLabel.trim()) {
        return labels[key] ?? currentLabel;
    }

    return currentLabel;
}

function normalizeProgressSteps(steps: any[]) {
    return steps.map((step) => ({
        ...step,
        label: normalizeProgressStepLabel(step),
    }));
}

export function prettySize(bytes: number) {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatDate(iso: string) {
    return new Date(iso).toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" });
}

export function statusLabel(status?: string) {
    const labels: Record<string, string> = {
        draft: "작성 중",
        ready: "분석 가능",
        queued: "대기 중",
        running: "분석 중",
        retrying: "다시 확인 중",
        processing: "영상 확인 중",
        analyzing: "사고 장면 분석 중",
        completed: "완료",
        succeeded: "완료",
        ready_for_analysis: "분석 준비",
        failed: "분석 실패. 다시 시도해 주세요.",
        uploaded: "업로드 완료",
    };

    return status ? labels[status] || status : "상태 없음";
}

export function statusClass(status?: string) {
    if (status === "completed" || status === "ready" || status === "ready_for_analysis" || status === "uploaded") return "ok";
    if (status === "failed") return "fail";
    return "warn";
}

export function useCaseWorkspace(caseId: string) {
    const caseData = ref<CaseItem | null>(null);
    const descriptionText = ref("");
    const facts = ref<AccidentFacts>({ injury: null });
    const analysisMode = ref("quick_summary");
    const selectedKeywords = ref<string[]>([...DEFAULT_KEYWORDS]);
    const file = ref<File | null>(null);
    const uploads = ref<UploadItem[]>([]);
    const selectedUploadId = ref("");
    const viewUrl = ref("");
    const jobs = ref<JobItem[]>([]);
    const progress = ref<any>(null);
    const progressPercent = ref(0);
    const progressStageLabel = ref("입력 대기");
    const progressMessage = ref("사고 설명이나 영상을 입력해 주세요.");
    const progressSteps = ref<any[]>(DEFAULT_PROGRESS_STEPS);
    const resultWaitAttempt = ref(0);
    const analysisStarted = ref(false);
    const resultStreaming = ref(false);
    const report = ref<any>(null);
    const message = ref("");
    const messageOk = ref(true);
    const initialLoading = ref(false);
    const loadError = ref("");
    const followupError = ref("");
    const reanalyzing = ref(false);
    const busy = ref<CaseWorkspaceBusyState>("");
    const guidedStep = ref<"input" | "accident-type" | "purpose" | "questions" | "analyzing" | "result">("input");
    const guidedAnswers = ref<Record<string, string>>({});
    let pollTimer: number | null = null;

    const activeUploadId = computed(() => selectedUploadId.value);

    function showMessage(text: string, ok = true) {
        message.value = text;
        messageOk.value = ok;
    }

    function normalizeStatus(value: any): string {
        return String(value ?? "").trim().toLowerCase();
    }

    function isRunningJob(job: JobItem): boolean {
        return RUNNING_JOB_STATUSES.includes(normalizeStatus(job.status));
    }

    function isFinishedJob(job: JobItem): boolean {
        return FINISHED_JOB_STATUSES.includes(normalizeStatus(job.status));
    }

    function isFailedJob(job: JobItem): boolean {
        return FAILED_JOB_STATUSES.includes(normalizeStatus(job.status));
    }

    function hasReportContent(candidate: any): boolean {
        if (!candidate || typeof candidate !== "object") return false;

        return Boolean(
            candidate.one_line_summary ||
            candidate.summary ||
            candidate.summary_for_user ||
            candidate.fault_ratio ||
            candidate.faultRatio ||
            candidate.fault_explanation ||
            candidate.elderly_friendly_report ||
            candidate.elderly_report ||
            candidate.easy_report ||
            candidate.result ||
            candidate.title ||
            candidate.headline ||
            candidate.sections ||
            candidate.judgment ||
            candidate.insurance ||
            candidate.action_plan ||
            candidate.legal_basis ||
            candidate.knia_matches ||
            candidate.report_html ||
            candidate.markdown ||
            candidate.content ||
            candidate.fault_adjustment_summary_card
        );
    }

    function getReportPayload(value: any): any | null {
        if (!value) return null;

        const status = normalizeStatus(value.status);
        if (["not_ready", "pending", "running", "processing"].includes(status)) return null;

        const candidates = [
            value.report,
            value.easy_report,
            value.elderly_friendly_report,
            value.elderly_report,
            value.result,
            value.data,
            value.payload,
            value.analysis,
            value,
        ].filter(Boolean);

        for (const candidate of candidates) {
            const candidateStatus = normalizeStatus(candidate?.status);
            if (["not_ready", "pending", "running", "processing"].includes(candidateStatus)) continue;

            if (hasReportContent(candidate)) return candidate;

            const nested = [
                candidate.report,
                candidate.easy_report,
                candidate.elderly_friendly_report,
                candidate.elderly_report,
                candidate.result,
                candidate.data,
                candidate.payload,
                candidate.analysis,
            ].filter(Boolean);

            for (const item of nested) {
                if (hasReportContent(item)) return item;
            }
        }

        return null;
    }

    function isReadyReport(value: any): boolean {
        return Boolean(getReportPayload(value));
    }

    function delay(ms: number) {
        return new Promise((resolve) => window.setTimeout(resolve, ms));
    }

    function applyLocalProgress(next: { percent?: number; stage?: string; message?: string; steps?: any[] }) {
        if (typeof next.percent === "number") {
            progressPercent.value = Math.max(progressPercent.value, Math.min(100, Math.max(0, next.percent)));
        }

        if (next.stage) progressStageLabel.value = next.stage;
        if (next.message) progressMessage.value = next.message;
        if (Array.isArray(next.steps) && next.steps.length) progressSteps.value = normalizeProgressSteps(next.steps);
    }

    function applyBackendProgress(data: any) {
        if (!data) return;

        applyLocalProgress({
            percent: Number(data.progress_percent ?? data.percent ?? progressPercent.value),
            stage: data.current_stage || data.stage_label || progressStageLabel.value,
            message: data.current_message || data.message || progressMessage.value,
            steps: Array.isArray(data.steps) ? normalizeProgressSteps(data.steps) : undefined,
        });

        if (data.result_ready === true || data.can_show_result === true) {
            progressPercent.value = 100;
            progressStageLabel.value = "결과 준비 완료";
            progressMessage.value = "분석 결과가 준비되었습니다.";

            if (guidedStep.value === "analyzing") {
                guidedStep.value = "result";
            }
        }
    }

    function onFile(e: Event) {
        const nextFile = (e.target as HTMLInputElement).files?.[0] || null;

        if (nextFile && !nextFile.type.startsWith("video/")) {
            file.value = null;
            showMessage("영상 파일만 업로드할 수 있습니다.", false);
            return;
        }

        file.value = nextFile;
        viewUrl.value = "";
    }

    function toggleKeyword(kw: string) {
        selectedKeywords.value = selectedKeywords.value.includes(kw)
            ? selectedKeywords.value.filter((x) => x !== kw)
            : [...selectedKeywords.value, kw];
    }

    function payload() {
        return {
            description_text: descriptionText.value,
            structured_facts: facts.value,
            selected_keywords: selectedKeywords.value,
            analysis_mode: analysisMode.value,
        };
    }

    async function loadCase() {
        const data = await api.getCase(caseId);

        caseData.value = data.case;
        descriptionText.value = data.case.description_text || "";
        facts.value = { ...facts.value, ...(data.case.structured_facts || {}) };
        selectedKeywords.value = data.case.selected_keywords?.length ? data.case.selected_keywords : selectedKeywords.value;
        analysisMode.value = data.case.analysis_mode || analysisMode.value;
    }

    function isAnalysisReady() {
        return Boolean(descriptionText.value.trim() || activeUploadId.value || file.value);
    }

    async function saveCaseInputs() {
        if (!descriptionText.value.trim()) descriptionText.value = "영상 자료 기반 사고 분석";

        busy.value = "save";

        try {
            const data = await api.updateCase(caseId, {
                description_text: descriptionText.value,
                structured_facts: facts.value,
                selected_keywords: selectedKeywords.value,
                analysis_mode: analysisMode.value,
            });

            caseData.value = data.case;
            showMessage("입력값을 저장했습니다.");
            return true;
        } catch (e: any) {
            showMessage(formatApiError(e, "입력값 저장에 실패했습니다."), false);
            return false;
        } finally {
            busy.value = "";
        }
    }

    async function loadUploads() {
        try {
            const data = await api.getCaseUploads(caseId);
            uploads.value = data.items || [];

            if (!selectedUploadId.value && uploads.value.length) selectedUploadId.value = uploads.value[0].id;
        } catch (e: any) {
            showMessage(formatApiError(e, "업로드 목록을 불러오지 못했습니다."), false);
        }
    }

    async function uploadLocal() {
        if (!file.value) return false;
        if (!(await saveCaseInputs())) return false;

        busy.value = "upload";

        try {
            applyLocalProgress({
                percent: 20,
                stage: "영상 업로드 중",
                message: "선택한 영상을 안전하게 저장하고 있습니다.",
            });

            const data = await api.localUpload(caseId, file.value);
            selectedUploadId.value = data.upload_id;

            applyLocalProgress({
                percent: 30,
                stage: "영상 저장 완료",
                message: "영상 저장이 완료되었습니다. 추가 사고정보를 입력해 주세요.",
            });

            showMessage("영상 저장 완료. 추가 사고정보를 입력해 주세요.");
            await loadUploads();

            return true;
        } catch (e: any) {
            selectedUploadId.value = "";
            showMessage(formatApiError(e, "영상 업로드에 실패했습니다."), false);
            return false;
        } finally {
            busy.value = "";
        }
    }

    async function completeUpload(options: { autoAnalyzeAfterPreprocess?: boolean } = {}) {
        if (!activeUploadId.value) return false;

        busy.value = "preprocess";

        try {
            const autoAnalyze = options.autoAnalyzeAfterPreprocess !== false;

            await api.completeUpload(activeUploadId.value, options);
            await loadJobs();
            await loadProgress();

            if (!autoAnalyze) {
                applyLocalProgress({
                    percent: 30,
                    stage: "영상 저장 완료",
                    message: "영상은 저장되었습니다. 이제 사고유형과 추가 사고정보를 입력해 주세요.",
                });

                showMessage("영상 저장 완료. 아래 질문에 답하면 과실비율을 더 정확하게 볼 수 있습니다.");
                guidedStep.value = "accident-type";
                return true;
            }

            applyLocalProgress({
                percent: 35,
                stage: "영상 확인 중",
                message: "영상에서 사고 장면을 확인하고 있습니다.",
            });

            showMessage("영상에서 사고 장면을 확인하고 있습니다.");
            startPollingJobs();
            return true;
        } catch (e: any) {
            showMessage(formatApiError(e, "전처리 작업 등록에 실패했습니다."), false);
            return false;
        } finally {
            busy.value = "";
        }
    }

    async function fetchViewUrl() {
        if (!activeUploadId.value) return;

        try {
            viewUrl.value = (await api.getViewUrl(activeUploadId.value)).view_url;
        } catch (e: any) {
            showMessage(formatApiError(e, "영상 재생 URL을 발급하지 못했습니다."), false);
        }
    }

    async function fetchDownloadUrl() {
        if (!activeUploadId.value) return;

        try {
            window.open((await api.getDownloadUrl(activeUploadId.value)).download_url, "_blank");
        } catch (e: any) {
            showMessage(formatApiError(e, "다운로드 URL을 발급하지 못했습니다."), false);
        }
    }

    async function loadJobs() {
        try {
            jobs.value = (await api.getJobs(caseId)).items || [];
        } catch (e: any) {
            showMessage(formatApiError(e, "작업 목록을 불러오지 못했습니다."), false);
        }
    }

    async function loadProgress() {
        try {
            const data = await api.getAnalysisProgress(caseId);
            progress.value = data;
            applyBackendProgress(data);

            if (data?.result_ready === true || data?.can_show_result === true) {
                await loadReport();

                if (isReadyReport(report.value)) {
                    progressPercent.value = 100;
                    progressStageLabel.value = "결과 준비 완료";
                    progressMessage.value = "분석 결과가 준비되었습니다.";
                    resultStreaming.value = false;
                    guidedStep.value = "result";
                }
            }
        } catch {
            progress.value = null;
        }
    }

    async function loadReport() {
        try {
            const response = await api.getEasyReport(caseId);
            report.value = getReportPayload(response);
        } catch {
            report.value = null;
        }
    }

    async function waitForReadyReport(options: { retryLimit?: number; delayMs?: number } = {}) {
        const retryLimit = options.retryLimit ?? REPORT_READY_RETRY_LIMIT;
        const delayMs = options.delayMs ?? REPORT_READY_RETRY_DELAY_MS;

        for (let attempt = 0; attempt < retryLimit; attempt += 1) {
            resultWaitAttempt.value = attempt + 1;

            const percent = Math.min(99, 88 + Math.floor((attempt / retryLimit) * 11));

            applyLocalProgress({
                percent,
                stage: "결과 정리 중",
                message: `분석 결과를 화면에 맞게 정리하고 있습니다. 잠시만 기다려 주세요. (${attempt + 1}/${retryLimit})`,
            });

            await Promise.all([loadReport(), loadProgress()]);

            if (isReadyReport(report.value)) {
                progressPercent.value = 100;
                progressStageLabel.value = "결과 준비 완료";
                progressMessage.value = "분석 결과가 준비되었습니다.";
                guidedStep.value = "result";
                resultStreaming.value = false;
                showMessage("분석 결과가 준비되었습니다.");
                return true;
            }

            await delay(delayMs);
        }

        return false;
    }

    async function analyzeText() {
        if (!isAnalysisReady()) {
            showMessage("사고 설명을 쓰거나 영상을 먼저 선택해 주세요.", false);
            return;
        }

        if (!(await saveCaseInputs())) return;

        busy.value = "text-analysis";
        analysisStarted.value = true;
        resultStreaming.value = true;
        guidedStep.value = "analyzing";

        try {
            applyLocalProgress({
                percent: 45,
                stage: "분석 시작",
                message: "입력한 사고정보를 바탕으로 분석을 시작합니다.",
            });

            await api.analyzeText(caseId, payload());
            showMessage("분석 결과를 정리하고 있습니다.");

            await loadCase();

            const ready = await waitForReadyReport({ retryLimit: 20, delayMs: 1000 });

            if (!ready) {
                showMessage("분석 결과를 불러오는 데 시간이 오래 걸리고 있습니다. 결과 새로고침을 눌러 다시 확인해 주세요.", false);
                guidedStep.value = "result";
                resultStreaming.value = false;
            }
        } catch (e: any) {
            showMessage(formatApiError(e, "텍스트 분석에 실패했습니다."), false);
            resultStreaming.value = false;
        } finally {
            busy.value = "";
        }
    }

    async function analyzeVideo() {
        if (!activeUploadId.value) return false;
        if (!(await saveCaseInputs())) return false;

        busy.value = "video-analysis";
        analysisStarted.value = true;
        resultStreaming.value = true;
        guidedStep.value = "analyzing";

        try {
            applyLocalProgress({
                percent: 45,
                stage: "영상 분석 시작",
                message: "입력한 사고정보와 영상을 함께 확인하고 있습니다.",
            });

            await api.analyzeVideo(caseId, { upload_id: activeUploadId.value, ...payload() });

            applyLocalProgress({
                percent: 55,
                stage: "사고유형 확인 중",
                message: "사고유형과 충돌 상황을 확인하고 있습니다.",
            });

            await loadJobs();
            await loadProgress();
            startPollingJobs();

            return true;
        } catch (e: any) {
            showMessage(formatApiError(e, "영상 분석 작업 등록에 실패했습니다."), false);
            resultStreaming.value = false;
            return false;
        } finally {
            busy.value = "";
        }
    }

    async function submitFollowup(answers: Record<string, string>) {
        followupError.value = "";
        reanalyzing.value = true;

        try {
            await api.reanalyzeText(caseId, { ...payload(), followup_answers: answers });
            await Promise.all([loadCase(), loadReport()]);

            if (isReadyReport(report.value)) {
                guidedStep.value = "result";
            }

            showMessage("보완 답변을 반영해 재분석했습니다.");
        } catch (e: any) {
            followupError.value = formatApiError(e, "보완 답변을 반영해 재분석하지 못했습니다.");
        } finally {
            reanalyzing.value = false;
        }
    }

    async function loadAll() {
        initialLoading.value = true;
        loadError.value = "";

        try {
            await Promise.all([loadCase(), loadUploads(), loadJobs(), loadReport(), loadProgress()]);

            if (isReadyReport(report.value)) {
                guidedStep.value = "result";
                return;
            }

            if (guidedStep.value === "result") guidedStep.value = "input";
        } catch (error: any) {
            loadError.value = error?.message || "케이스 정보를 불러오지 못했습니다.";
        } finally {
            initialLoading.value = false;
        }
    }

    function startPollingJobs() {
        stopPolling();

        pollTimer = window.setInterval(async () => {
            await Promise.all([loadJobs(), loadProgress()]);

            const hasRunningJob = jobs.value.some(isRunningJob);
            const hasFailedJob = jobs.value.some(isFailedJob);
            const hasFinishedJob = jobs.value.some(isFinishedJob);

            if (hasRunningJob) {
                const runningJob = jobs.value.find(isRunningJob);

                if (runningJob?.type === "video_preprocess") {
                    applyLocalProgress({
                        percent: Math.max(progressPercent.value, 45),
                        stage: "영상 확인 중",
                        message: "영상에서 사고 장면을 찾고 있습니다.",
                    });
                } else if (runningJob?.type === "video_analyze") {
                    applyLocalProgress({
                        percent: Math.max(progressPercent.value, 65),
                        stage: "사고 분석 중",
                        message: "입력한 답변과 영상을 바탕으로 과실비율을 계산하고 있습니다.",
                    });
                } else {
                    applyLocalProgress({
                        percent: Math.max(progressPercent.value, 55),
                        stage: "분석 중",
                        message: "사고 내용을 분석하고 있습니다.",
                    });
                }

                return;
            }

            stopPolling();
            await Promise.all([loadUploads(), loadCase(), loadProgress()]);

            if (hasFailedJob) {
                resultStreaming.value = false;
                showMessage("영상 분석 중 일부 작업이 실패했습니다. 고급 진단 보기에서 작업 상태를 확인해 주세요.", false);
                guidedStep.value = "questions";
                return;
            }

            if (hasFinishedJob || jobs.value.length > 0) {
                applyLocalProgress({
                    percent: 88,
                    stage: "결과 정리 중",
                    message: "분석 작업이 끝났습니다. 결과 화면을 정리하고 있습니다.",
                });

                const ready = await waitForReadyReport();
                if (ready) return;

                resultStreaming.value = false;
                showMessage("분석 결과를 불러오는 데 시간이 오래 걸리고 있습니다. 결과 새로고침을 눌러 다시 확인해 주세요.", false);

                if (guidedStep.value === "analyzing") guidedStep.value = "result";
            }
        }, 1200);
    }

    async function continueFromInput() {
        if (!isAnalysisReady()) {
            showMessage("사고 설명을 쓰거나 영상을 먼저 선택해 주세요.", false);
            return;
        }

        const saved = await saveCaseInputs();
        if (!saved) return;

        guidedAnswers.value = {};
        guidedStep.value = "accident-type";
    }

    function selectAccidentType(option: { scenario_type: string; accident_party_type: string }) {
        const scenarioType = option.scenario_type || facts.value.accident_type || "";
        const partyType = option.accident_party_type || facts.value.accident_party_type || "unknown";

        const nextFacts: AccidentFacts = {
            ...facts.value,
            accident_type: scenarioType,
            accident_party_type: partyType,
            scenario_hint: option.scenario_type ? "user_selected" : "agent_infer",
            ...(scenarioType === "rear_end_collision"
                ? { rear_end_role: (facts.value as any).rear_end_role || "unknown" }
                : {}),
        };

        (nextFacts as any).knia_major_party_type = partyType;

        if (scenarioType === "stealth_illegal_parked_vehicle_collision") {
            nextFacts.accident_type = "stealth_illegal_parked_vehicle_collision";
            nextFacts.accident_party_type = "car_vs_car";
            (nextFacts as any).knia_major_party_type = "car_vs_car";
            (nextFacts as any).collision_partner_type = "vehicle";
            (nextFacts as any).direct_collision_partner_type = "vehicle";
            (nextFacts as any).target_vehicle_status = "abnormal_parked";
            (nextFacts as any).is_parked_vehicle_collision = true;
            (nextFacts as any).is_stealth_parked_vehicle_collision = true;
            (nextFacts as any).excluded_knia_party_types = ["car_vs_bicycle", "car_vs_person"];
        }

        facts.value = nextFacts;
        guidedAnswers.value = {};
        guidedStep.value = "purpose";
    }

    function selectGuidedAnalysisMode(mode: string) {
        analysisMode.value = mode;
        guidedStep.value = "questions";
    }

    function answerGuidedQuestion(question: any, value: string) {
        const questionId = question.question_id || question.field || question.fact_key || "unknown_question";
        guidedAnswers.value = { ...guidedAnswers.value, [questionId]: value };

        const factKey = question.fact_key || question.knia_factor_key || String(question.question_id || "").split(".").pop();
        const nextFacts: AccidentFacts = { ...facts.value };

        function markStealthParkedVehicleCollision() {
            nextFacts.accident_party_type = "car_vs_car";
            nextFacts.accident_type = "stealth_illegal_parked_vehicle_collision";

            (nextFacts as any).knia_major_party_type = "car_vs_car";
            (nextFacts as any).collision_partner_type = "vehicle";
            (nextFacts as any).direct_collision_partner_type = "vehicle";
            (nextFacts as any).accident_subtype = "night_unlit_illegal_parked_vehicle_collision";
            (nextFacts as any).target_vehicle_status = "abnormal_parked";
            (nextFacts as any).is_parked_vehicle_collision = true;
            (nextFacts as any).is_stealth_parked_vehicle_collision = true;
            (nextFacts as any).requires_high_opponent_fault_review = true;
            (nextFacts as any).excluded_knia_party_types = ["car_vs_bicycle", "car_vs_person"];

            delete (nextFacts as any).bicycle_involved;
            delete (nextFacts as any).possible_trigger_vehicle;
            delete (nextFacts as any).trigger_actor_type;
            delete (nextFacts as any).bicycle_location;
            delete (nextFacts as any).bicycle_movement;

            const lighting = String((nextFacts as any).parked_vehicle_lighting || "");
            const visibility = String((nextFacts as any).visibility_condition || "");
            const position = String((nextFacts as any).parked_vehicle_position || "");
            const impairment = String((nextFacts as any).opponent_impairment || "");
            const avoidability = String((nextFacts as any).avoidability || "");

            const isUnlit = lighting === "unlit_stealth" || lighting === "no_lights" || lighting === "unknown_but_dark";
            const isDark = visibility === "night_dark" || visibility === "under_bridge_dark" || visibility === "low_visibility";
            const isAbnormalPosition =
                position === "traffic_space" ||
                position === "flowerbed_or_median" ||
                position === "under_bridge" ||
                position === "roadside" ||
                position === "under_bridge_flowerbed";
            const isDrunk = impairment === "drunk_driving_confirmed" || impairment === "suspected_drunk";
            const isHardToAvoid = avoidability === "nearly_impossible" || avoidability === "limited";

            (nextFacts as any).night_no_lights_or_low_visibility = isUnlit || isDark;
            (nextFacts as any).abnormal_parking = isAbnormalPosition;
            (nextFacts as any).opponent_drunk_or_abnormal_operation = isDrunk;
            (nextFacts as any).low_avoidability = isHardToAvoid;

            if (isUnlit && isDark && isAbnormalPosition && isDrunk && isHardToAvoid) {
                (nextFacts as any).fault_ratio_claim_target = "opponent_100_ego_0_possible";
                (nextFacts as any).fault_ratio_realistic_target = "opponent_90_ego_10";
                (nextFacts as any).fault_ratio_minimum_target = "opponent_80_ego_20";
            } else if ((isUnlit && isDark && isAbnormalPosition) || (isDrunk && isAbnormalPosition)) {
                (nextFacts as any).fault_ratio_claim_target = "opponent_90_ego_10";
                (nextFacts as any).fault_ratio_realistic_target = "opponent_80_ego_20";
                (nextFacts as any).fault_ratio_minimum_target = "opponent_70_ego_30";
            }
        }

        if (factKey === "stopped") {
            nextFacts.stopped = value === "yes" ? true : value === "no" ? false : undefined;
        } else if (factKey === "sudden_brake_without_reason" || factKey === "sudden_brake") {
            nextFacts.sudden_brake = value === "yes";
        } else if (factKey === "lawful_stop_reason" || factKey === "stop_reason") {
            nextFacts.stop_reason = value;
        } else if (factKey === "brake_light_failure" || factKey === "brake_light") {
            nextFacts.brake_light = value;
        } else if (factKey === "abnormal_stop_position") {
            nextFacts.abnormal_stop = value === "abnormal_stop";
        } else if (factKey === "collision_object_type") {
            (nextFacts as any).collision_object_type = value;

            if (value === "parked_vehicle") {
                markStealthParkedVehicleCollision();
            } else if (value === "fixed_object" || value === "fallen_or_movable_object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            }
        } else if (factKey === "stealth_collision_target") {
            (nextFacts as any).stealth_collision_target = value;
            (nextFacts as any).collision_target = value === "parked_truck" ? "truck" : value === "parked_vehicle" ? "parked_vehicle" : value;
            if (value === "parked_truck" || value === "parked_vehicle") {
                markStealthParkedVehicleCollision();
            } else if (value === "fixed_object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            }
        } else if (factKey === "stealth_parked_position") {
            (nextFacts as any).stealth_parked_position = value;
            (nextFacts as any).parked_vehicle_position = value === "under_bridge_flowerbed" ? "flowerbed_or_median" : value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "stealth_lighting") {
            (nextFacts as any).stealth_lighting = value;
            (nextFacts as any).parked_vehicle_lighting =
                value === "unlit_stealth" ? "unlit_stealth" : value === "lights_on" ? "all_lights_on" : value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "stealth_visibility") {
            (nextFacts as any).stealth_visibility = value;
            (nextFacts as any).visibility_condition = value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "opponent_drunk_driving") {
            (nextFacts as any).opponent_drunk_driving = value;
            (nextFacts as any).opponent_impairment =
                value === "drunk_confirmed" ? "drunk_driving_confirmed" : value === "drunk_suspected" ? "suspected_drunk" : value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "stealth_avoidability") {
            (nextFacts as any).stealth_avoidability = value;
            (nextFacts as any).avoidability = value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "collision_target") {
            (nextFacts as any).collision_target = value;

            if (value === "parked_vehicle" || value === "truck") {
                markStealthParkedVehicleCollision();
            } else if (value === "facility" || value === "fixed_object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            }
        } else if (factKey === "parked_vehicle_position") {
            (nextFacts as any).parked_vehicle_position = value;

            if (value === "traffic_space" || value === "flowerbed_or_median" || value === "under_bridge" || value === "roadside") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "parked_vehicle_lighting") {
            (nextFacts as any).parked_vehicle_lighting = value;

            if (value === "unlit_stealth" || value === "no_lights" || value === "unknown_but_dark") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "visibility_condition") {
            (nextFacts as any).visibility_condition = value;

            if (value === "night_dark" || value === "under_bridge_dark" || value === "low_visibility") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "opponent_impairment") {
            (nextFacts as any).opponent_impairment = value;

            if (value === "drunk_driving_confirmed" || value === "suspected_drunk") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "avoidability") {
            (nextFacts as any).avoidability = value;

            if (value === "limited" || value === "nearly_impossible") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "abnormal_parking") {
            (nextFacts as any).abnormal_parking = value === "yes" ? true : value === "no" ? false : undefined;

            if (value === "yes") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "visibility_issue") {
            (nextFacts as any).visibility_issue = value;
            (nextFacts as any).night_no_lights_or_low_visibility = value === "stealth_no_lights" || value === "hard_to_see";

            if (value === "stealth_no_lights" || value === "hard_to_see") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "road_environment") {
            (nextFacts as any).road_environment = value;

            if (value === "under_bridge" || value === "flowerbed_or_median" || value === "dark_road") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "avoidance_time") {
            (nextFacts as any).avoidance_time = value;

            if (value === "limited" || value === "nearly_impossible") {
                (nextFacts as any).avoidability = value;
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "crosswalk_context") {
            (nextFacts as any).crosswalk_context = value;
            if (value === "crosswalk" || value === "near_crosswalk") {
                nextFacts.accident_party_type = "car_vs_person";
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            }
        } else if (factKey === "pedestrian_signal") {
            (nextFacts as any).pedestrian_signal = value;
        } else if (factKey === "pedestrian_visibility") {
            (nextFacts as any).pedestrian_visibility = value;
        } else if (factKey === "turn_signal") {
            (nextFacts as any).turn_signal = value;
        } else if (factKey === "impact_position") {
            (nextFacts as any).impact_position = value;
        } else if (factKey === "lane_change_manner") {
            (nextFacts as any).lane_change_manner = value;
            nextFacts.accident_type = "lane_change_collision";
            nextFacts.accident_party_type = "car_vs_car";
            (nextFacts as any).knia_major_party_type = "car_vs_car";
        } else if (factKey === "signal_context") {
            (nextFacts as any).signal_context = value;
        } else if (factKey === "intersection_movement") {
            (nextFacts as any).intersection_movement = value;
            nextFacts.accident_type = "intersection_collision";
            nextFacts.accident_party_type = "car_vs_car";
            (nextFacts as any).knia_major_party_type = "car_vs_car";
        } else if (factKey === "intersection_entry_order") {
            (nextFacts as any).intersection_entry_order = value;
        } else if (factKey === "bicycle_location") {
            (nextFacts as any).bicycle_location = value;
            nextFacts.accident_party_type = "car_vs_bicycle";
            nextFacts.accident_type = "bicycle_collision";
            (nextFacts as any).knia_major_party_type = "car_vs_bicycle";
        } else if (factKey === "bicycle_movement") {
            (nextFacts as any).bicycle_movement = value;
        } else if (factKey === "single_vehicle_cause") {
            (nextFacts as any).single_vehicle_cause = value;
            nextFacts.accident_party_type = "single_vehicle";
            nextFacts.accident_type = "single_vehicle_accident";
            (nextFacts as any).knia_major_party_type = "single_vehicle";
        } else if (factKey === "external_cause_evidence") {
            (nextFacts as any).external_cause_evidence = value;
        } else if (factKey === "accident_counterpart") {
            (nextFacts as any).accident_counterpart = value;

            if (value === "person") {
                nextFacts.accident_party_type = "car_vs_person";
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            } else if (value === "bicycle") {
                nextFacts.accident_party_type = "car_vs_bicycle";
                nextFacts.accident_type = "bicycle_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_bicycle";
            } else if (value === "parked_vehicle") {
                markStealthParkedVehicleCollision();
            } else if (value === "object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            } else if (value === "car") {
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            }
        } else if (factKey === "accident_location_context") {
            (nextFacts as any).accident_location_context = value;

            if (value === "intersection") {
                nextFacts.accident_type = "intersection_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "lane") {
                nextFacts.accident_type = "lane_change_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "crosswalk") {
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                nextFacts.accident_party_type = "car_vs_person";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            } else if (value === "parking_or_roadside") {
                nextFacts.accident_type = "object_collision";
            } else if (value === "under_bridge" || value === "flowerbed_or_median") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "visibility_or_weather") {
            (nextFacts as any).visibility_or_weather = value;
            (nextFacts as any).night_no_lights_or_low_visibility = value === "night_or_dark";

            if (value === "night_or_dark") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "rear_end_role") {
            (nextFacts as any).rear_end_role = value;

            if (value === "ego_hit_front") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).collision_role = "ego_hit_front";
            } else if (value === "hit_by_rear") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).collision_role = "hit_by_rear";
            }
        } else if (factKey === "accident_direction") {
            (nextFacts as any).accident_direction = value;

            if (value === "ego_hit_front") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).rear_end_role = "ego_hit_front";
                (nextFacts as any).collision_role = "ego_hit_front";
            } else if (value === "hit_by_rear") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).rear_end_role = "hit_by_rear";
                (nextFacts as any).collision_role = "hit_by_rear";
            } else if (value === "object_collision") {
                nextFacts.accident_type = "object_collision";
                nextFacts.accident_party_type = "car_vs_object";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            } else if (value === "intersection") {
                nextFacts.accident_type = "intersection_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "lane_change") {
                nextFacts.accident_type = "lane_change_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "pedestrian") {
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                nextFacts.accident_party_type = "car_vs_person";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            } else if (value === "parked_vehicle" || value === "stealth_parked_vehicle") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "front_vehicle_status") {
            (nextFacts as any).front_vehicle_status = value;
            (nextFacts as any).rear_end_role = "ego_hit_front";
            (nextFacts as any).collision_role = "ego_hit_front";

            if (value === "sudden_stop") {
                nextFacts.sudden_brake = true;
            }
        } else if (factKey === "front_stop_reason") {
            (nextFacts as any).front_stop_reason = value;
            nextFacts.stop_reason = value;
        } else if (factKey === "front_brake_light") {
            (nextFacts as any).front_brake_light = value;
            nextFacts.brake_light = value;
        } else if (factKey === "following_distance") {
            (nextFacts as any).following_distance = value;
        } else if (factKey === "rear_end_avoidance_time") {
            (nextFacts as any).rear_end_avoidance_time = value;
        } else {
            (nextFacts as any)[factKey] = value;
        }

        facts.value = nextFacts;
    }

    async function startGuidedAnalysis() {
        if (!(await saveCaseInputs())) return;

        analysisStarted.value = true;
        resultStreaming.value = true;
        guidedStep.value = "analyzing";

        applyLocalProgress({
            percent: 40,
            stage: "분석 시작",
            message: "입력한 사고정보를 바탕으로 분석을 시작합니다.",
        });

        if (activeUploadId.value) {
            const started = await analyzeVideo();

            if (!started) {
                resultStreaming.value = false;
                guidedStep.value = "questions";
            }

            return;
        }

        await analyzeText();

        if (!isReadyReport(report.value) && guidedStep.value === "analyzing") {
            guidedStep.value = "result";
        }
    }

    async function onGuidedFile(e: Event) {
        onFile(e);
        if (!file.value) return;

        const uploaded = await uploadLocal();
        if (!uploaded || !activeUploadId.value) return;

        await completeUpload({ autoAnalyzeAfterPreprocess: false });
    }

    const guidedQuestions = computed(() => {
        const currentReport = getReportPayload(report.value) || report.value;

        const fromReport =
            currentReport?.guided_questionnaire?.questions ||
            currentReport?.missing_info?.questions ||
            currentReport?.report?.guided_questionnaire?.questions ||
            currentReport?.report?.missing_info?.questions ||
            [];

        if (fromReport.length) return fromReport;

        return getFallbackGuidedQuestions(facts.value, descriptionText.value);
    });

    function stopPolling() {
        if (pollTimer !== null) window.clearInterval(pollTimer);
        pollTimer = null;
    }

    onMounted(loadAll);
    onBeforeUnmount(stopPolling);

    return {
        caseData,
        descriptionText,
        facts,
        analysisMode,
        selectedKeywords,
        keywordPool: caseKeywordPool,
        file,
        uploads,
        selectedUploadId,
        activeUploadId,
        viewUrl,
        jobs,
        progress,
        progressPercent,
        progressStageLabel,
        progressMessage,
        progressSteps,
        resultWaitAttempt,
        analysisStarted,
        resultStreaming,
        report,
        message,
        messageOk,
        initialLoading,
        loadError,
        followupError,
        reanalyzing,
        busy,
        guidedStep,
        guidedAnswers,
        guidedAccidentTypeOptions,
        guidedAnalysisModes,
        guidedQuestions,
        analyzeText,
        analyzeVideo,
        completeUpload,
        fetchDownloadUrl,
        fetchViewUrl,
        formatDate,
        loadAll,
        loadJobs,
        loadProgress,
        loadReport,
        loadUploads,
        onFile,
        onGuidedFile,
        prettySize,
        saveCaseInputs,
        continueFromInput,
        selectAccidentType,
        selectGuidedAnalysisMode,
        answerGuidedQuestion,
        startGuidedAnalysis,
        statusClass,
        statusLabel,
        submitFollowup,
        toggleKeyword,
        uploadLocal,
    };
}