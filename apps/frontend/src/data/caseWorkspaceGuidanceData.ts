export type GuidedChoice = {
    value: string;
    label: string;
};

export type GuidedQuestion = {
    question_id: string;
    title: string;
    plain_question: string;
    why_it_matters: string;
    choices: GuidedChoice[];
    fact_key: string;
};

export type GuidedQuestionType =
    | "rear_end"
    | "ego_hit_front"
    | "hit_by_rear"
    | "rear_end_unknown"
    | "stealth_parked_vehicle"
    | "object_collision"
    | "pedestrian"
    | "lane_change"
    | "intersection"
    | "highway"
    | "motorcycle"
    | "vehicle_progress"
    | "bicycle"
    | "single_vehicle"
    | "car_vs_car_subtype"
    | "unknown";

export const DEFAULT_KEYWORDS = ["블랙박스", "과실비율", "교통사고", "보험처리"];
export const RUNNING_JOB_STATUSES = ["queued", "running", "retrying", "processing", "analyzing"];
export const FINISHED_JOB_STATUSES = ["completed", "succeeded", "success", "done", "finished"];
export const FAILED_JOB_STATUSES = ["failed", "error", "cancelled", "canceled", "dead"];
export const REPORT_READY_RETRY_LIMIT = 30;
export const REPORT_READY_RETRY_DELAY_MS = 1000;

export const DEFAULT_PROGRESS_STEPS = [
    { key: "input", label: "입력 정리", percent: 15 },
    { key: "upload", label: "영상 확인", percent: 30 },
    { key: "scene", label: "사고 장면 확인", percent: 45 },
    { key: "scenario", label: "사고유형 판단", percent: 60 },
    { key: "knia", label: "KNIA 과실 기준 검색", percent: 75 },
    { key: "adjustment", label: "가감요소 계산", percent: 88 },
    { key: "result", label: "결과 정리", percent: 100 },
];

export const guidedAccidentMajorCategoryOptions = [
    {
        label: "차대차 사고",
        scenario_type: "",
        accident_party_type: "car_vs_car",
        major_category: "car_vs_car",
        hint: "자동차, 트럭, 버스, 주차·정차 차량 등 차량과 차량 사이의 사고",
    },
    {
        label: "고속도로 사고",
        scenario_type: "",
        accident_party_type: "car_vs_car",
        major_category: "highway",
        hint: "고속도로·자동차전용도로에서 합류, 차로감소, 추돌, 낙하물, 갓길 관련 사고",
    },
    {
        label: "차대사람 사고",
        scenario_type: "",
        accident_party_type: "car_vs_person",
        major_category: "car_vs_person",
        hint: "보행자, 횡단보도, 어린이보호구역 등이 관련된 경우",
    },
    {
        label: "차대자전거 사고",
        scenario_type: "",
        accident_party_type: "car_vs_bicycle",
        major_category: "car_vs_bicycle",
        hint: "자전거와 직접 충돌한 경우",
    },
    {
        label: "차대이륜차 사고",
        scenario_type: "",
        accident_party_type: "car_vs_two_wheeler",
        major_category: "car_vs_two_wheeler",
        hint: "오토바이, 이륜차, 원동기장치자전거가 관련된 경우",
    },
    {
        label: "차량단독 사고",
        scenario_type: "",
        accident_party_type: "single_vehicle",
        major_category: "single_vehicle",
        hint: "다른 차량·사람·자전거 없이 내 차량만 사고가 난 경우",
    },
    {
        label: "주차·정차 관련 사고",
        scenario_type: "",
        accident_party_type: "parking_or_stationary",
        major_category: "parking_or_stationary",
        hint: "주차·정차 차량, 야간 스텔스 정차, 갓길·통행공간 방치 차량이 관련된 경우",
    },
    {
        label: "잘 모르겠어요",
        scenario_type: "",
        accident_party_type: "unknown",
        major_category: "unknown",
        hint: "영상 분석과 후속 질문으로 가장 가능성 높은 대분류를 보정합니다.",
    },
];

export const guidedAccidentTypeOptions = guidedAccidentMajorCategoryOptions;

export const guidedAccidentSubtypeOptionsByMajorCategory: Record<string, Array<{
    value: string;
    label: string;
    scenario_type: string;
    accident_party_type?: string;
    hint: string;
}>> = {
    car_vs_car: [
        { value: "intersection_general_collision", label: "교차로(+자로, T자로 등) 사고", scenario_type: "intersection_collision", hint: "신호, 우선순위, 직진·좌회전·우회전 관계가 중요한 사고" },
        { value: "opposite_direction_vehicle_collision", label: "마주보는 방향 진행차량 사고", scenario_type: "opposite_direction_vehicle_collision", hint: "맞은편 차량, 중앙선, 회피 과정, 좌회전 관계가 중요한 사고" },
        { value: "same_direction_vehicle_collision", label: "같은 방향 진행차량 사고", scenario_type: "same_direction_vehicle_collision", hint: "추돌, 차로변경, 앞지르기, 동일차로 주행 관계가 중요한 사고" },
        { value: "vehicle_other_road_type_collision", label: "기타 유형 사고(주차장·회전교차로 등)", scenario_type: "vehicle_other_road_type_collision", hint: "주차장, 회전교차로, 좁은 도로, 기타 도로형태에서 발생한 사고" },
        { value: "car_vs_motorcycle_special", label: "자동차 대 이륜차 특수유형", scenario_type: "motorcycle_collision", accident_party_type: "car_vs_motorcycle", hint: "오토바이·이륜차와의 충돌로 별도 기준 확인이 필요한 사고" },
        { value: "rear_end_collision", label: "후미추돌", scenario_type: "rear_end_collision", hint: "앞차·뒤차 관계가 쟁점인 추돌 사고" },
        { value: "lane_change_collision", label: "차로변경 중 충돌", scenario_type: "lane_change_collision", hint: "끼어들기, 진로변경, 방향지시등이 쟁점인 경우" },
        { value: "intersection_signal_violation", label: "교차로·신호 관련 충돌", scenario_type: "intersection_signal_violation", hint: "신호, 좌회전·직진, 선진입 여부가 중요한 경우" },
        { value: "left_turn_vs_straight", label: "좌회전 대 직진", scenario_type: "intersection_collision", hint: "좌회전 차량과 직진 차량의 진행 관계가 핵심인 경우" },
        { value: "centerline_collision", label: "중앙선 침범", scenario_type: "centerline_obstacle_collision", hint: "중앙선, 회피, 맞은편 차량이 쟁점인 경우" },
        { value: "parking_lot_collision", label: "주차장 사고", scenario_type: "parking_lot_collision", hint: "주차장 내부 진행·출차 중 발생한 사고" },
        { value: "door_open_collision", label: "문 개방 사고", scenario_type: "door_open_collision", hint: "문을 열면서 충돌한 경우" },
        { value: "unknown", label: "잘 모르겠어요", scenario_type: "", hint: "영상과 확인 질문으로 세부유형을 좁힙니다." },
    ],
    highway: [
        { value: "highway_merge_collision", label: "합류도로 사고", scenario_type: "highway_merge_collision", accident_party_type: "car_vs_car", hint: "본선 차량과 합류 차량의 우선관계가 쟁점인 사고" },
        { value: "highway_lane_reduction_collision", label: "차로 감소도로 사고", scenario_type: "highway_lane_reduction_collision", accident_party_type: "car_vs_car", hint: "차로가 줄어드는 지점에서 양보와 진입 순서가 중요한 사고" },
        { value: "highway_lane_change_collision", label: "차로변경(진로변경) 사고", scenario_type: "highway_lane_change_collision", accident_party_type: "car_vs_car", hint: "고속도로 주행 중 차로변경·진로변경이 관련된 사고" },
        { value: "highway_rear_end_collision", label: "추돌 사고", scenario_type: "highway_rear_end_collision", accident_party_type: "car_vs_car", hint: "정체·감속·안전거리 확보 여부가 중요한 고속도로 추돌 사고" },
        { value: "highway_falling_object_collision", label: "낙하물 사고", scenario_type: "highway_falling_object_collision", accident_party_type: "car_vs_object", hint: "적재물·낙하물·도로 장애물과 관련된 사고" },
        { value: "highway_pedestrian_collision", label: "보행자 사고", scenario_type: "highway_pedestrian_collision", accident_party_type: "car_vs_person", hint: "고속도로 안의 보행자·작업자·사고 처리 인원과 관련된 사고" },
        { value: "highway_shoulder_lane_change", label: "갓길 진로 변경 사고", scenario_type: "highway_shoulder_lane_change", accident_party_type: "car_vs_car", hint: "갓길 정차·진입·이탈 또는 갓길에서 본선으로 들어오는 사고" },
        { value: "unknown", label: "잘 모르겠어요", scenario_type: "", accident_party_type: "car_vs_car", hint: "고속도로 위치와 차량 진행 상태를 추가 질문으로 확인합니다." },
    ],
    car_vs_person: [
        { value: "crosswalk_signalized_pedestrian", label: "횡단보도 내(신호등 있음)", scenario_type: "pedestrian_crosswalk_signalized_accident", hint: "보행자 신호와 차량 신호가 핵심인 횡단보도 사고" },
        { value: "crosswalk_unsignalized_pedestrian", label: "횡단보도 내(신호등 없음)", scenario_type: "pedestrian_crosswalk_unsignalized_accident", hint: "신호등 없는 횡단보도에서 일시정지·감속 여부가 중요한 사고" },
        { value: "near_crosswalk_signalized_pedestrian", label: "횡단보도 부근(신호등 있음)", scenario_type: "pedestrian_near_crosswalk_signalized_accident", hint: "횡단보도 바로 주변과 신호 상태를 함께 확인해야 하는 사고" },
        { value: "near_crossing_facility_unsignalized", label: "횡단시설 부근(신호등 없음)", scenario_type: "pedestrian_near_crossing_facility_accident", hint: "육교·지하도·횡단시설 주변에서 보행자 위치가 중요한 사고" },
        { value: "non_crosswalk_pedestrian", label: "횡단보도 없음", scenario_type: "pedestrian_no_crosswalk_road_crossing", hint: "무단횡단, 차도 보행 등이 관련된 경우" },
        { value: "pedestrian_other_type", label: "기타 사고유형", scenario_type: "pedestrian_other_accident", hint: "도로 작업자, 갓길 보행자, 어린이보호구역 등 별도 확인이 필요한 사고" },
        { value: "school_zone_child_accident", label: "어린이보호구역 사고", scenario_type: "school_zone_child_accident", hint: "어린이보호구역 또는 어린이 피해자가 관련된 경우" },
        { value: "sidewalk_or_shoulder", label: "인도·갓길 보행자 사고", scenario_type: "pedestrian_on_road_edge_accident", hint: "인도, 갓길, 도로 가장자리 보행자가 관련된 경우" },
        { value: "unknown", label: "잘 모르겠어요", scenario_type: "", hint: "보행자 위치와 신호를 후속 질문으로 확인합니다." },
    ],
    car_vs_bicycle: [
        { value: "intersection_collision", label: "교차로(+자로, T자로 등) 사고", scenario_type: "bicycle_intersection_collision", hint: "교차로에서 차량과 자전거의 신호·진행방향이 중요한 사고" },
        { value: "opposite_direction_collision", label: "마주보는 방향 진행 사고", scenario_type: "bicycle_opposite_direction_collision", hint: "차량과 자전거가 서로 마주보거나 대향 방향으로 진행한 사고" },
        { value: "same_direction_collision", label: "같은 방향 진행 중 충돌", scenario_type: "bicycle_collision", hint: "차량과 자전거가 같은 방향으로 움직인 경우" },
        { value: "bicycle_other_type", label: "기타 유형 사고", scenario_type: "bicycle_other_accident", hint: "자전거도로, 보도, 기타 도로형태에서 세부 확인이 필요한 사고" },
        { value: "turning_collision", label: "회전 중 충돌", scenario_type: "bicycle_collision", hint: "우회전·좌회전 과정에서 자전거와 부딪힌 경우" },
        { value: "lane_change_collision", label: "차로변경 중 충돌", scenario_type: "bicycle_collision", hint: "차로 변경 또는 진로 변경 과정에서 자전거와 부딪힌 경우" },
        { value: "unknown", label: "잘 모르겠어요", scenario_type: "", hint: "자전거 위치와 진행 방향을 후속 질문으로 확인합니다." },
    ],
    car_vs_two_wheeler: [
        { value: "straight_vs_straight", label: "직진 대(對) 직진 사고", scenario_type: "motorcycle_straight_vs_straight_collision", hint: "교차 또는 대향 직진 관계에서 차량과 이륜차가 충돌한 경우" },
        { value: "straight_vs_left_opposite", label: "직진 대(對) 좌회전 사고(맞은편)", scenario_type: "motorcycle_straight_vs_left_opposite_collision", hint: "맞은편 좌회전 차량과 직진 이륜차·차량 관계가 중요한 사고" },
        { value: "straight_vs_left_side", label: "직진 대(對) 좌회전 사고(측면)", scenario_type: "motorcycle_straight_vs_left_side_collision", hint: "측면에서 좌회전·직진 진행이 엇갈린 사고" },
        { value: "straight_vs_right", label: "직진 대(對) 우회전 사고", scenario_type: "motorcycle_straight_vs_right_collision", hint: "우회전 차량과 직진 이륜차의 위치·신호가 중요한 사고" },
        { value: "left_vs_left", label: "좌회전 대(對) 좌회전 사고", scenario_type: "motorcycle_left_vs_left_collision", hint: "양쪽 모두 좌회전하는 과정에서 발생한 사고" },
        { value: "same_lane_collision", label: "동일차로 주행 중 사고", scenario_type: "motorcycle_same_lane_collision", hint: "같은 차로에서 앞뒤·병렬 진행 중 충돌한 사고" },
        { value: "t_intersection_collision", label: "삼거리(T자형) 교차로 사고", scenario_type: "motorcycle_t_intersection_collision", hint: "T자형 교차로에서 진입·회전 우선관계가 중요한 사고" },
        { value: "motorcycle_other_road_type", label: "기타 도로유형 사고", scenario_type: "motorcycle_other_accident", hint: "갓길, 차로 사이, 기타 도로형태에서 발생한 이륜차 사고" },
        { value: "unknown", label: "잘 모르겠어요", scenario_type: "", hint: "이륜차 위치와 진행 방향을 후속 질문으로 확인합니다." },
    ],
    single_vehicle: [
        { value: "object_collision", label: "시설물·물체 충돌", scenario_type: "object_collision", accident_party_type: "car_vs_object", hint: "가드레일, 벽, 기둥, 낙하물과 부딪힌 경우" },
        { value: "guardrail_collision", label: "가드레일 충돌", scenario_type: "object_collision", accident_party_type: "car_vs_object", hint: "가드레일 또는 중앙분리대가 주된 충돌 대상인 경우" },
        { value: "rollover", label: "전도·전복", scenario_type: "single_vehicle_accident", hint: "차량이 넘어지거나 전복된 경우" },
        { value: "road_surface_or_weather", label: "노면·날씨 영향", scenario_type: "single_vehicle_accident", hint: "빗길, 눈길, 포트홀 등 도로 환경이 관련된 경우" },
        { value: "unknown", label: "잘 모르겠어요", scenario_type: "", hint: "영상과 추가 질문으로 원인을 확인합니다." },
    ],
    parking_or_stationary: [
        { value: "parking_or_stopped_vehicle_accident", label: "주차·정차 차량", scenario_type: "parking_or_stopped_vehicle_accident", accident_party_type: "car_vs_car", hint: "정차 또는 주차된 차량과 부딪힌 경우" },
        { value: "stealth_illegal_parked_vehicle_collision", label: "야간 스텔스 정차 차량", scenario_type: "stealth_illegal_parked_vehicle_collision", accident_party_type: "car_vs_car", hint: "야간, 교량 아래, 무등화, 갓길·통행공간 방치 차량이 관련된 경우" },
        { value: "parking_lot_collision", label: "주차장 내 사고", scenario_type: "parking_lot_collision", accident_party_type: "car_vs_car", hint: "주차장 안에서 출차·후진·진행 중 발생한 사고" },
        { value: "unknown", label: "잘 모르겠어요", scenario_type: "", accident_party_type: "car_vs_car", hint: "정차 위치와 등화 여부를 후속 질문으로 확인합니다." },
    ],
    unknown: [
        { value: "unknown", label: "잘 모르겠어요", scenario_type: "", accident_party_type: "unknown", hint: "영상 분석과 후속 질문으로 사고유형을 추정합니다." },
    ],
};

export function getGuidedAccidentSubtypeOptions(majorCategory?: string) {
    return guidedAccidentSubtypeOptionsByMajorCategory[majorCategory || "unknown"] || guidedAccidentSubtypeOptionsByMajorCategory.unknown;
}

export const legacyGuidedAccidentScenarioOptions = [
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
        label: "차선변경 중 부딪힌 사고",
        scenario_type: "lane_change_collision",
        accident_party_type: "car_vs_car",
        hint: "끼어들기, 진로변경, 방향지시등이 쟁점인 경우",
    },
    {
        label: "잘 모르겠어요",
        scenario_type: "",
        accident_party_type: "unknown",
        hint: "설명과 영상으로 가장 가능성 높은 KNIA 대분류를 추정합니다.",
    },
];

export const carVsCarSubtypeGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "car_vs_car.subtype",
        title: "세부 사고유형",
        plain_question: "차대차 사고 중 어떤 유형에 가장 가깝나요?",
        why_it_matters: "차대차 안에서도 후미추돌, 차선변경, 교차로, 주정차 차량 기준이 서로 다릅니다.",
        choices: [
            { value: "intersection_collision", label: "교차로(+자로, T자로 등) 사고" },
            { value: "opposite_direction_vehicle_collision", label: "마주보는 방향 진행차량 사고" },
            { value: "same_direction_vehicle_collision", label: "같은 방향 진행차량 사고" },
            { value: "vehicle_other_road_type_collision", label: "기타 유형 사고(주차장·회전교차로 등)" },
            { value: "motorcycle_collision", label: "자동차 대 이륜차 특수유형" },
            { value: "highway_collision", label: "고속도로 사고" },
            { value: "rear_end_collision", label: "후미추돌" },
            { value: "ego_hit_front", label: "내가 앞차 추돌" },
            { value: "lane_change_collision", label: "차선변경" },
            { value: "intersection_collision", label: "교차로" },
            { value: "intersection_signal_violation", label: "신호위반" },
            { value: "centerline_obstacle_collision", label: "중앙선/장애물 회피" },
            { value: "parking_or_stopped_vehicle_accident", label: "주차·정차 차량" },
            { value: "stealth_illegal_parked_vehicle_collision", label: "야간 스텔스 정차 차량" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "car_vs_car_scenario_type",
    },
];

export const guidedAnalysisModes = [
    {
        value: "user_friendly",
        label: "일반사용자모드",
        hint: "현재 상황, 과실비율, 관련 KNIA 근거와 영상만 간단히 봅니다.",
    },
    {
        value: "expert",
        label: "전문가모드",
        hint: "KNIA 기준, 법률 근거, 가감요소, 증거, 추가 확인사항까지 자세히 봅니다.",
    },
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

export const rearEndUnknownGuidedQuestions: GuidedQuestion[] = [
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
        question_id: "pedestrian.knia_crossing_type",
        title: "보행자 사고 위치",
        plain_question: "보행자는 어디에서 또는 어느 부근에서 이동 중이었나요?",
        why_it_matters: "KNIA 차대사람 기준은 횡단보도 안, 횡단보도 부근, 횡단시설 부근, 횡단보도 없음, 기타 유형을 나누어 봅니다.",
        choices: [
            { value: "crosswalk_signalized", label: "횡단보도 내(신호등 있음)" },
            { value: "crosswalk_unsignalized", label: "횡단보도 내(신호등 없음)" },
            { value: "near_crosswalk_signalized", label: "횡단보도 부근(신호등 있음)" },
            { value: "near_crossing_facility_unsignalized", label: "횡단시설 부근(신호등 없음)" },
            { value: "no_crosswalk", label: "횡단보도 없음" },
            { value: "other", label: "기타 사고유형" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "pedestrian_knia_crossing_type",
    },
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

pedestrianGuidedQuestions.unshift(
    {
        question_id: "pedestrian.role",
        title: "상대 유형",
        plain_question: "충돌한 상대가 보행자, 도로 작업자, 공사 담당자, 신호수 또는 교통 통제원이었나요?",
        why_it_matters: "상대가 일반 보행자인지, 도로 작업자인지에 따라 필요한 확인 사항이 달라집니다.",
        choices: [
            { value: "pedestrian", label: "일반 보행자" },
            { value: "road_worker", label: "도로 작업자 또는 공사 담당자" },
            { value: "traffic_controller", label: "신호수 또는 교통 통제원" },
            { value: "unknown", label: "모르겠어요" },
        ],
        fact_key: "pedestrian_role",
    },
    {
        question_id: "pedestrian.sudden_entry",
        title: "갑작스러운 진입",
        plain_question: "상대가 차량 진행 방향을 보지 않고 갑자기 차도 안으로 들어왔나요?",
        why_it_matters: "갑작스러운 차도 진입은 운전자 회피 가능성과 보행자 측 주의의무 판단에 중요합니다.",
        choices: [
            { value: "yes", label: "예" },
            { value: "no", label: "아니요" },
            { value: "unknown", label: "모르겠어요" },
        ],
        fact_key: "pedestrian_sudden_entry",
    },
    {
        question_id: "pedestrian.safety_measures",
        title: "공사 안전조치",
        plain_question: "도로공사 표지판, 라바콘, 신호수, 조명 같은 안전조치가 있었나요?",
        why_it_matters: "공사구역 안전조치 유무는 예견 가능성과 책임 분담의 중요한 단서입니다.",
        choices: [
            { value: "adequate", label: "충분히 있었다" },
            { value: "partial", label: "일부만 있었다" },
            { value: "none", label: "없었다" },
            { value: "unknown", label: "모르겠어요" },
        ],
        fact_key: "road_work_safety_measures",
    },
);

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

export const highwayGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "highway.section",
        title: "고속도로 위치",
        plain_question: "사고가 난 지점은 어디에 가까웠나요?",
        why_it_matters: "KNIA 고속도로 기준은 합류도로, 차로감소, 갓길, 본선 주행 중 사고를 나누어 봅니다.",
        choices: [
            { value: "merge", label: "합류도로" },
            { value: "lane_reduction", label: "차로 감소 구간" },
            { value: "mainline", label: "본선 주행 차로" },
            { value: "shoulder", label: "갓길 또는 갓길 진입·이탈" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "highway_section",
    },
    {
        question_id: "highway.event_type",
        title: "고속도로 사고유형",
        plain_question: "사고 상황은 어떤 유형에 가장 가까웠나요?",
        why_it_matters: "고속도로에서는 차로변경, 추돌, 낙하물, 보행자·작업자 사고가 서로 다른 기준으로 검토됩니다.",
        choices: [
            { value: "merge_collision", label: "합류 중 충돌" },
            { value: "lane_change_collision", label: "차로변경 또는 진로변경" },
            { value: "rear_end_collision", label: "정체·감속 중 추돌" },
            { value: "falling_object", label: "낙하물 또는 적재물" },
            { value: "pedestrian_or_worker", label: "보행자·작업자 관련" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "highway_event_type",
    },
    {
        question_id: "highway.traffic_flow",
        title: "속도와 정체",
        plain_question: "사고 직전 차량 흐름은 어땠나요?",
        why_it_matters: "고속 주행인지, 정체·서행 중인지에 따라 안전거리와 회피 가능성 판단이 달라집니다.",
        choices: [
            { value: "free_flow", label: "정상 속도 또는 고속 주행" },
            { value: "slow_or_congested", label: "정체·서행 중" },
            { value: "sudden_slowdown", label: "갑작스러운 감속 또는 정지" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "highway_traffic_flow",
    },
    {
        question_id: "highway.warning",
        title: "경고와 식별 가능성",
        plain_question: "비상등, 삼각대, 낙하물 표시 등 위험을 알 수 있는 조치가 있었나요?",
        why_it_matters: "고속도로에서는 경고조치와 식별 가능성이 회피 가능성과 과실 조정에 중요합니다.",
        choices: [
            { value: "clear_warning", label: "비상등·삼각대 등으로 알 수 있었습니다" },
            { value: "partial_warning", label: "일부만 보였습니다" },
            { value: "no_warning", label: "거의 알 수 없었습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "highway_warning_measures",
    },
];

export const vehicleProgressGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "vehicle_progress.direction_relation",
        title: "차량 진행관계",
        plain_question: "두 차량은 서로 어떤 방향으로 진행 중이었나요?",
        why_it_matters: "KNIA 차대차 기준은 교차로, 마주보는 방향, 같은 방향, 기타 도로유형을 먼저 나누어 봅니다.",
        choices: [
            { value: "intersection", label: "교차로에서 서로 만남" },
            { value: "opposite_direction", label: "마주보는 방향" },
            { value: "same_direction", label: "같은 방향" },
            { value: "parking_or_roundabout", label: "주차장·회전교차로·기타 도로" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "vehicle_direction_relation",
    },
    {
        question_id: "vehicle_progress.maneuver",
        title: "충돌 직전 행동",
        plain_question: "충돌 직전 어느 행동이 가장 중요했나요?",
        why_it_matters: "직진, 좌회전, 우회전, 차로변경, 앞지르기 여부가 적용 기준을 좁히는 핵심입니다.",
        choices: [
            { value: "straight", label: "직진" },
            { value: "left_turn", label: "좌회전" },
            { value: "right_turn", label: "우회전" },
            { value: "lane_change", label: "차로변경 또는 끼어들기" },
            { value: "overtaking", label: "앞지르기 또는 추월" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "vehicle_maneuver",
    },
    {
        question_id: "vehicle_progress.road_shape",
        title: "도로 형태",
        plain_question: "사고 장소의 도로 형태는 무엇에 가까웠나요?",
        why_it_matters: "주차장, 회전교차로, 좁은 도로, T자형 교차로는 별도 기준으로 갈릴 수 있습니다.",
        choices: [
            { value: "cross_intersection", label: "+자 또는 일반 교차로" },
            { value: "t_intersection", label: "T자형 교차로" },
            { value: "roundabout", label: "회전교차로" },
            { value: "parking_lot", label: "주차장" },
            { value: "narrow_or_other", label: "좁은 도로 또는 기타" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "vehicle_road_shape",
    },
];

export const motorcycleGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "motorcycle.road_relation",
        title: "이륜차 진행관계",
        plain_question: "차량과 이륜차는 어떤 관계로 진행 중이었나요?",
        why_it_matters: "KNIA 차대이륜차 기준은 직진 대 직진, 직진 대 좌회전, 우회전, 동일차로, T자형 교차로를 나누어 봅니다.",
        choices: [
            { value: "straight_vs_straight", label: "직진 대 직진" },
            { value: "straight_vs_left_opposite", label: "직진 대 맞은편 좌회전" },
            { value: "straight_vs_left_side", label: "직진 대 측면 좌회전" },
            { value: "straight_vs_right", label: "직진 대 우회전" },
            { value: "left_vs_left", label: "좌회전 대 좌회전" },
            { value: "same_lane", label: "동일차로 주행 중" },
            { value: "t_intersection", label: "삼거리(T자형) 교차로" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "motorcycle_road_relation",
    },
    {
        question_id: "motorcycle.position",
        title: "이륜차 위치",
        plain_question: "이륜차는 사고 직전 어디에 있었나요?",
        why_it_matters: "차로 중앙, 차로 사이, 갓길, 우측 가장자리 위치는 회피 가능성과 주의의무 판단에 중요합니다.",
        choices: [
            { value: "lane_center", label: "차로 안" },
            { value: "between_lanes", label: "차로 사이 또는 옆 공간" },
            { value: "right_edge", label: "우측 가장자리" },
            { value: "shoulder", label: "갓길" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "motorcycle_position",
    },
    {
        question_id: "motorcycle.signal_and_visibility",
        title: "신호와 식별 가능성",
        plain_question: "신호, 방향지시등, 야간 등화 상태가 확인되나요?",
        why_it_matters: "이륜차 사고에서는 신호위반, 방향지시등, 야간 등화 여부가 가감요소가 될 수 있습니다.",
        choices: [
            { value: "signals_clear", label: "신호와 등화가 확인됩니다" },
            { value: "turn_signal_missing", label: "방향지시등이 불명확합니다" },
            { value: "night_unlit", label: "야간 등화가 부족했습니다" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "motorcycle_signal_visibility",
    },
];

export const bicycleGuidedQuestions: GuidedQuestion[] = [
    {
        question_id: "bicycle.knia_category",
        title: "자전거 사고유형",
        plain_question: "차량과 자전거의 관계는 어떤 유형에 가장 가까웠나요?",
        why_it_matters: "KNIA 차대자전거 기준은 교차로, 마주보는 방향, 같은 방향, 기타 유형을 먼저 나누어 봅니다.",
        choices: [
            { value: "intersection", label: "교차로(+자로, T자로 등)" },
            { value: "opposite_direction", label: "마주보는 방향 진행" },
            { value: "same_direction", label: "같은 방향 진행" },
            { value: "other", label: "기타 도로유형" },
            { value: "unknown", label: "잘 모르겠어요" },
        ],
        fact_key: "bicycle_knia_category",
    },
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

export const GUIDED_QUESTION_SETS: Record<GuidedQuestionType, GuidedQuestion[]> = {
    rear_end: rearEndGuidedQuestions,
    ego_hit_front: egoHitFrontVehicleGuidedQuestions,
    hit_by_rear: rearHitByOtherGuidedQuestions,
    rear_end_unknown: rearEndUnknownGuidedQuestions,
    stealth_parked_vehicle: stealthParkedVehicleGuidedQuestions,
    object_collision: objectCollisionGuidedQuestions,
    pedestrian: pedestrianGuidedQuestions,
    lane_change: laneChangeGuidedQuestions,
    intersection: intersectionGuidedQuestions,
    highway: highwayGuidedQuestions,
    motorcycle: motorcycleGuidedQuestions,
    vehicle_progress: vehicleProgressGuidedQuestions,
    bicycle: bicycleGuidedQuestions,
    single_vehicle: singleVehicleGuidedQuestions,
    car_vs_car_subtype: carVsCarSubtypeGuidedQuestions,
    unknown: unknownGuidedQuestions,
};

export const caseKeywordPool = [
    "후미추돌",
    "안전거리",
    "신호위반",
    "교차로",
    "T자형 교차로",
    "회전교차로",
    "차선변경",
    "방향지시등",
    "마주보는 방향",
    "같은 방향 진행",
    "고속도로",
    "합류도로",
    "차로 감소",
    "갓길",
    "낙하물",
    "횡단보도",
    "횡단시설",
    "보행자",
    "자전거",
    "이륜차",
    "오토바이",
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
