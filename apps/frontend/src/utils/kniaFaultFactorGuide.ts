export type KniaFaultFactorGuide = {
  kind: "remarkable_fault" | "gross_fault";
  label: string;
  summary: string;
  examples: string[];
  note: string;
  sourceLabel: string;
  sourceUrl: string;
};

const KNIA_FACTOR_SOURCE_URL = "https://accident.knia.or.kr/myaccident-content?chartNo=205&chartType=1";

const REMARKABLE_FAULT_GUIDE: KniaFaultFactorGuide = {
  kind: "remarkable_fault",
  label: "현저한 과실",
  summary:
    "기본과실에 더해 주의의무 위반 정도가 큰 경우입니다. 중대한 과실보다는 낮은 단계이며, 중대한 과실과 함께 적용하지 않습니다.",
  examples: [
    "한눈팔기 등 전방주시의무 위반이 현저한 경우",
    "음주 영향이 있으나 혈중알코올농도 0.03% 미만인 경우",
    "제한속도 10km/h 이상 20km/h 미만 초과",
    "핸들 또는 브레이크 조작이 현저히 부적절한 경우",
    "차량 유리의 암도가 높은 경우",
    "운전 중 휴대전화 사용",
    "운전 중 영상표시장치 시청·조작",
  ],
  note:
    "사고 형태와 관계없이 나타날 수 있는 공통 가감요소입니다. 블랙박스, 경찰자료, 속도, 음주측정 등으로 확인될 때 적용하세요.",
  sourceLabel: "KNIA 수정요소해설 기준",
  sourceUrl: KNIA_FACTOR_SOURCE_URL,
};

const GROSS_FAULT_GUIDE: KniaFaultFactorGuide = {
  kind: "gross_fault",
  label: "중대한 과실",
  summary:
    "현저한 과실보다 주의의무 위반 정도가 더 크고 고의에 가까울 만큼 위험한 운전행위입니다. 현저한 과실과 함께 적용하지 않습니다.",
  examples: [
    "혈중알코올농도 0.03% 이상 음주운전",
    "무면허 운전",
    "졸음운전",
    "제한속도 20km/h 초과",
    "마약 등 약물 영향 운전",
    "공동위험행위 등 매우 위험한 운전",
  ],
  note:
    "증거가 명확하고 사고 발생과 관련될 때 적용하세요. 애매하면 바로 체크하지 말고 추가 확인 항목으로 남기는 것이 안전합니다.",
  sourceLabel: "KNIA 수정요소해설 기준",
  sourceUrl: KNIA_FACTOR_SOURCE_URL,
};

function normalizeFactorLabel(value: unknown) {
  return String(value ?? "")
    .replace(/\s+/g, "")
    .trim();
}

export function getKniaFaultFactorGuide(value: unknown): KniaFaultFactorGuide | null {
  const label = normalizeFactorLabel(value);
  if (!label) return null;
  if (label.includes("현저한과실")) return REMARKABLE_FAULT_GUIDE;
  if (label.includes("중대한과실") || label.includes("중대과실") || label.includes("중과실")) {
    return GROSS_FAULT_GUIDE;
  }
  return null;
}
