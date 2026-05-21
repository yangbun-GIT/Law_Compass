export type AiRouteInput = {
  caseTitle?: string;
  caseDescription?: string;
  fileName?: string;
  uploadMetadata?: Record<string, unknown>;
};

export type AiRouteDecision = {
  aiProfile: string;
  specialistRoles: string[];
  reason: string;
};

const PROFILES: Record<string, string[]> = {
  rear_end_focus: [
    "impact-dynamics-analyst",
    "rear-end-fault-specialist",
    "braking-pattern-analyst",
    "distance-keeping-evaluator",
    "insurance-liability-planner",
    "legal-obligation-checker",
    "evidence-relevance-auditor",
    "uncertainty-calibrator"
  ],
  intersection_focus: [
    "signal-compliance-analyst",
    "right-of-way-specialist",
    "intersection-collision-analyst",
    "speed-feasibility-analyst",
    "insurance-liability-planner",
    "criminal-risk-analyst",
    "evidence-relevance-auditor",
    "uncertainty-calibrator"
  ],
  lane_change_focus: [
    "lane-change-rule-specialist",
    "blind-spot-risk-analyst",
    "turn-signal-compliance-analyst",
    "impact-dynamics-analyst",
    "insurance-liability-planner",
    "legal-obligation-checker",
    "evidence-relevance-auditor",
    "uncertainty-calibrator"
  ],
  pedestrian_focus: [
    "pedestrian-protection-analyst",
    "crosswalk-priority-specialist",
    "injury-severity-flagger",
    "speed-feasibility-analyst",
    "criminal-risk-analyst",
    "reporting-duty-specialist",
    "evidence-relevance-auditor",
    "uncertainty-calibrator"
  ],
  default_vehicle_collision: [
    "impact-dynamics-analyst",
    "fault-ratio-generalist",
    "insurance-liability-planner",
    "legal-obligation-checker",
    "evidence-relevance-auditor",
    "uncertainty-calibrator"
  ]
};

export function selectVideoAiRoute(input: AiRouteInput): AiRouteDecision {
  const text = `${input.caseTitle ?? ""} ${input.caseDescription ?? ""} ${input.fileName ?? ""}`.toLowerCase();

  if (text.includes("후미") || text.includes("추돌") || text.includes("rear")) {
    return {
      aiProfile: "rear_end_focus",
      specialistRoles: PROFILES.rear_end_focus,
      reason: "후미추돌 키워드 감지"
    };
  }

  if (text.includes("교차로") || text.includes("신호") || text.includes("좌회전")) {
    return {
      aiProfile: "intersection_focus",
      specialistRoles: PROFILES.intersection_focus,
      reason: "교차로/신호 키워드 감지"
    };
  }

  if (text.includes("차선") || text.includes("끼어들") || text.includes("변경")) {
    return {
      aiProfile: "lane_change_focus",
      specialistRoles: PROFILES.lane_change_focus,
      reason: "차선변경 키워드 감지"
    };
  }

  if (text.includes("보행") || text.includes("횡단") || text.includes("자전거")) {
    return {
      aiProfile: "pedestrian_focus",
      specialistRoles: PROFILES.pedestrian_focus,
      reason: "보행자/약자 관련 키워드 감지"
    };
  }

  return {
    aiProfile: "default_vehicle_collision",
    specialistRoles: PROFILES.default_vehicle_collision,
    reason: "일반 차량 충돌 기본 라우트"
  };
}
