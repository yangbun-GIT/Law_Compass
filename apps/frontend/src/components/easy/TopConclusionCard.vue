<template>
  <article class="card hero-card easy-hero top-conclusion-card">
    <div class="top-conclusion-copy">
      <p class="eyebrow">핵심 결론</p>
      <h1>{{ accidentTitle }}</h1>

      <p v-if="accidentSummary" class="easy-summary top-accident-summary">
        {{ accidentSummary }}
      </p>

      <div v-if="visibleLabels.length" class="chips top-conclusion-tags">
        <span v-for="label in visibleLabels" :key="label" class="chip selected">
          {{ label }}
        </span>
      </div>
    </div>

    <section class="fault-summary-card hero-fault-panel" :class="{ 'is-empty': !hasFaultRatio }">
      <p class="eyebrow">현재 입력 기준 예상</p>
      <h2>예상 과실비율</h2>
      <KniaFaultRatioBar
        v-if="hasFaultRatio"
        :a="myFault"
        :b="otherFault"
        left-label="내 과실"
        right-label="상대 과실"
        variant="user"
      />
      <p v-else class="fault-panel-empty">과실비율은 추가 확인 후 표시됩니다.</p>
      <p class="fault-panel-note">{{ faultBasis }}</p>
    </section>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import KniaFaultRatioBar from "../knia/KniaFaultRatioBar.vue";
import { cleanAccidentSummaryText, sanitizeDisplayText } from "../../utils/displaySanitizer";

type FaultValue = number | string | null | undefined;

const props = defineProps<{ report: any }>();

const faultSource = computed(() => {
  const simple = props.report?.simple_report?.fault_ratio;
  const source = simple && typeof simple === "object"
    ? simple
    : props.report?.fault_ratio || props.report?.faultRatio || props.report?.fault_explanation || {};
  const userFault = source.user_fault || source.final_fault || {};

  return {
    my: firstFaultValue(source.my, source.my_percent, source.my_fault, source.user_fault_percent, userFault.my),
    other: firstFaultValue(source.other, source.other_percent, source.opponent_fault, source.counterparty_fault, userFault.other),
    basis: source.basis || source.summary || source.simple_summary || props.report?.fault_ratio_summary,
  };
});

const myFault = computed(() => faultSource.value.my);
const otherFault = computed(() => faultSource.value.other);
const hasFaultRatio = computed(() => myFault.value !== null || otherFault.value !== null);

const accidentTitle = computed(() => (
  firstCleanTitle([
    props.report?.video_scene_summary?.title,
    props.report?.structured_facts?.video_scene_summary?.title,
    props.report?.simple_report?.situation_title,
    props.report?.accident_title,
    props.report?.situation_title,
  ]) || synthesizedAccidentTitle.value
));

const accidentSummary = computed(() => (
  firstCleanSummary([
    props.report?.accident_summary,
    props.report?.video_scene_summary?.summary_text,
    props.report?.structured_facts?.video_scene_summary?.summary_text,
    props.report?.simple_report?.situation_summary,
    props.report?.current_situation_summary,
    props.report?.situation_summary,
    props.report?.one_line_summary,
    props.report?.structured_facts?.description_text,
    props.report?.summary_for_user?.short_summary,
    props.report?.summary,
  ]) || synthesizedAccidentSummary.value
));

const facts = computed<Record<string, any>>(() => ({
  ...(props.report?.structured_facts && typeof props.report.structured_facts === "object" ? props.report.structured_facts : {}),
  ...(props.report?.simple_report?.facts && typeof props.report.simple_report.facts === "object" ? props.report.simple_report.facts : {}),
}));

const synthesizedAccidentTitle = computed(() => {
  const party = primaryPartyLabel.value;
  const scenario = scenarioLabel.value;
  if (scenario && scenario !== party) return scenario;
  if (party) return `${party} 요약`;
  return "사고 요약";
});

const synthesizedAccidentSummary = computed(() => {
  const party = primaryPartyLabel.value || "교통사고";
  const scenario = scenarioLabel.value;
  const f = facts.value;

  if (isPersonAccident.value) {
    if (
      f.pedestrian_worker ||
      f.road_work_context ||
      String(f.direct_collision_target || "").includes("worker") ||
      /작업자|공사|도로 작업/.test(String(scenario))
    ) {
      const sudden = f.pedestrian_sudden_entry === true ? " 상대가 차도 쪽으로 갑자기 들어온 정황이 함께 보입니다." : "";
      return `이 사고는 도로 작업자 또는 공사 담당자와 충돌한 차대사람 사고로 보입니다.${sudden || " 작업자 위치, 안전조치, 운전자 시야를 추가로 확인해야 합니다."}`;
    }
    if (f.pedestrian_sudden_entry === true || String(scenario).includes("갑작")) {
      return "이 사고는 차대사람 사고로 보이며, 주행 중 보행자가 차도 쪽으로 갑자기 진입해 충돌한 상황으로 정리됩니다.";
    }
    return "이 사고는 차대사람 사고로 보이며, 보행자의 위치와 운전자가 사전에 볼 수 있었는지가 핵심 확인 사항입니다.";
  }

  if (isBicycleAccident.value) {
    return "이 사고는 차대자전거 사고로 보이며, 자전거의 진행 위치와 차량의 회피 가능성을 함께 확인해야 합니다.";
  }

  if (isMotorcycleAccident.value) {
    return "이 사고는 차대오토바이 사고로 보이며, 서로의 진행 방향과 충돌 지점을 기준으로 과실을 검토해야 합니다.";
  }

  if (isObjectAccident.value) {
    return "이 사고는 물체 또는 시설물과의 충돌 사고로 보이며, 충돌 대상과 회피 가능성, 도로 환경을 함께 확인해야 합니다.";
  }

  if (isVehicleAccident.value && !String(props.report?.scenario_type || f.scenario_type || "").trim()) {
    return "이 사고는 차량과 차량이 직접 충돌한 차대차 사고로 보이며, 충돌 지점과 각 차량의 진행 방향을 기준으로 사고 경위를 정리했습니다.";
  }

  if (String(props.report?.scenario_type || f.scenario_type || "").includes("lane_change")) {
    return "이 사고는 차대차 차선변경 사고로 보이며, 차선변경 주체와 방향지시등, 충돌 부위가 과실 판단의 핵심입니다.";
  }

  if (String(props.report?.scenario_type || f.scenario_type || "").includes("rear_end")) {
    return "이 사고는 차대차 후방추돌 사고로 보이며, 정차 여부와 급정거 사유, 브레이크등 작동 여부를 함께 확인해야 합니다.";
  }

  if (String(props.report?.scenario_type || f.scenario_type || "").includes("intersection")) {
    return "이 사고는 교차로에서 발생한 차대차 사고로 보이며, 각 차량의 신호와 진입 순서가 과실 판단의 핵심입니다.";
  }

  return `이 사고는 ${party}${scenario && scenario !== party ? `의 ${scenario}` : ""}로 보이며, 영상 판단과 입력 답변을 기준으로 사고 경위를 정리했습니다.`;
});

const faultBasis = computed(() => {
  const cleaned = cleanAccidentSummaryText(faultSource.value.basis, "");
  if (cleaned) return cleaned;
  return "입력한 사고 사실과 KNIA 기준을 함께 검토했습니다.";
});

const primaryPartyLabel = computed(() => cleanLabel(
  props.report?.summary_for_user?.accident_type_label ||
  props.report?.accident_party_type_card?.label ||
  props.report?.accident_party_type_card?.summary ||
  props.report?.knia_major_party_type ||
  props.report?.accident_party_type ||
  facts.value?.knia_major_party_type ||
  facts.value?.accident_party_type,
));

const scenarioLabel = computed(() => cleanLabel(props.report?.scenario_type || facts.value?.scenario_type));

const partyCode = computed(() => String(
  props.report?.knia_major_party_type ||
  props.report?.accident_party_type ||
  facts.value?.knia_major_party_type ||
  facts.value?.accident_party_type ||
  "",
));

const isPersonAccident = computed(() =>
  partyCode.value === "car_vs_person" ||
  facts.value?.collision_partner_type === "pedestrian" ||
  facts.value?.direct_collision_partner_type === "pedestrian" ||
  /보행자|차대사람|작업자|공사 담당자/.test(primaryPartyLabel.value) ||
  /보행자|차대사람|작업자|공사 담당자/.test(scenarioLabel.value)
);
const isVehicleAccident = computed(() =>
  partyCode.value === "car_vs_car" ||
  facts.value?.collision_partner_type === "vehicle" ||
  facts.value?.direct_collision_partner_type === "vehicle" ||
  facts.value?.primary_collision_target === "vehicle" ||
  /차대차|차량/.test(primaryPartyLabel.value)
);
const isBicycleAccident = computed(() => partyCode.value === "car_vs_bicycle" || facts.value?.direct_collision_partner_type === "bicycle");
const isMotorcycleAccident = computed(() => partyCode.value === "car_vs_motorcycle" || facts.value?.direct_collision_partner_type === "motorcycle");
const isObjectAccident = computed(() => partyCode.value === "car_vs_object" || facts.value?.direct_collision_partner_type === "object");

const visibleLabels = computed(() => {
  const labels = [primaryPartyLabel.value, scenarioLabel.value]
    .filter((label): label is string => Boolean(label));
  return [...new Set(labels)].slice(0, 2);
});

function firstFaultValue(...values: FaultValue[]) {
  for (const value of values) {
    const parsed = parseFaultValue(value);
    if (parsed !== null) return parsed;
  }
  return null;
}

function parseFaultValue(value: FaultValue) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? clampPercent(value) : null;
  const match = String(value).match(/-?\d+(?:\.\d+)?/);
  if (!match) return null;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? clampPercent(parsed) : null;
}

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function firstCleanSummary(values: unknown[]) {
  for (const value of values) {
    const cleaned = cleanAccidentSummaryText(value, "");
    if (isDefaultCaseNoise(cleaned)) continue;
    if (cleaned && cleaned !== accidentTitle.value) return cleaned;
  }
  return "";
}

function firstCleanTitle(values: unknown[]) {
  for (const value of values) {
    const cleaned = cleanAccidentSummaryText(value, "");
    if (!cleaned) continue;
    if (isDefaultCaseNoise(cleaned)) continue;
    if (/^(영상에서 확인된 사고 개요|입력한 사고 상황)$/.test(cleaned)) continue;
    return cleaned.length > 44 ? "사고 요약" : cleaned;
  }
  return "";
}

function cleanLabel(value: unknown) {
  const label = sanitizeDisplayText(value, "");
  if (!label || /^(교통사고|사고|unknown|추가 확인 필요)$/i.test(label)) return "";
  return label;
}

function isDefaultCaseNoise(value: string) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return false;
  return /^(영상 사고 분석 케이스|영상 자료 기반 사고 분석|블랙박스 과실비율|영상 사고 분석 케이스 영상 자료 기반 사고 분석 블랙박스 과실비율|입력한 영상과 답변을 바탕으로 사고 상황을 정리했습니다\.?|입력한 사고 설명과 영상 자료를 바탕으로 사고 상황을 정리했습니다\.?|입력하신 사고 내용을 바탕으로 대응 방향을 정리했습니다\.?)$/i.test(text) ||
    /^Local video verified\./i.test(text) ||
    /duration=\d/i.test(text) ||
    /frame_observations=\d/i.test(text) ||
    /입력하신 사고는 .*과실.*신고 필요 여부/.test(text);
}
</script>

<style scoped>
.top-conclusion-card {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  align-items: start;
}

.top-conclusion-copy {
  min-width: 0;
}

.top-conclusion-card h1 {
  max-width: 920px;
  margin-bottom: 14px;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.top-accident-summary {
  max-width: 980px;
  margin: 0;
  color: var(--text-main);
  word-break: keep-all;
}

.top-conclusion-tags {
  margin-top: 16px;
  margin-bottom: 0;
}

.top-conclusion-card .fault-summary-card.hero-fault-panel {
  display: grid;
  align-content: start;
  gap: 12px;
  min-width: 0;
  width: 100%;
  margin: 0;
  padding: 18px 18px 20px;
  border-radius: 18px;
  border: 1px solid rgba(201, 169, 98, 0.36);
  background:
    linear-gradient(145deg, rgba(201, 169, 98, 0.16), rgba(28, 23, 20, 0.76)),
    rgba(37, 30, 25, 0.84);
  color: var(--text-main);
  box-shadow: inset 0 1px 0 rgba(232, 223, 212, 0.08);
}

.hero-fault-panel h2 {
  margin: 0;
  color: var(--text-main);
  font-size: clamp(1.3rem, 2.4vw, 1.85rem);
  line-height: 1.2;
}

.fault-panel-note,
.fault-panel-empty {
  margin: 0;
  color: var(--text-sub);
  font-size: 0.98rem;
  line-height: 1.6;
  word-break: keep-all;
}

.fault-panel-empty {
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px dashed rgba(201, 169, 98, 0.34);
  background: rgba(28, 23, 20, 0.46);
}

@media (max-width: 640px) {
  .top-conclusion-card .fault-summary-card.hero-fault-panel {
    padding: 16px 14px;
  }
}
</style>
