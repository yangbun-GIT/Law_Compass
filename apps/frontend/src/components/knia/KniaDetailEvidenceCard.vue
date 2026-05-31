<template>
  <article v-if="chart || fallbackStandard" class="card easy-card wide-card knia-detail-evidence-card">
    <div class="knia-detail-head">
      <div>
        <p class="eyebrow">KNIA 원문 기준</p>
        <h2>{{ text(displayTitle) }}</h2>
      </div>
      <RouterLink
        v-if="chartNoText"
        class="btn secondary"
        :to="`/knia/charts/${encodeURIComponent(chartNoText)}?chartType=${encodeURIComponent(chartTypeText)}`"
      >
        상세 기준 보기
      </RouterLink>
    </div>

    <div class="chips">
      <span v-if="chartNoText" class="chip selected">기준번호 {{ chartNoText }}</span>
      <span v-if="partyLabel" class="chip">대분류: {{ partyLabel }}</span>
      <span v-if="baseFaultLabel" class="chip">{{ baseFaultLabel }}</span>
      <span v-if="chart?.detail_collected_at" class="chip detail-ok">상세 수집 완료</span>
    </div>

    <p v-if="menuPath.length" class="kv">{{ menuPath.join(" > ") }}</p>
    <p v-if="summaryText" class="easy-summary">{{ summaryText }}</p>

    <div v-if="hasBaseFault || situationLines.length" class="knia-detail-grid">
      <section v-if="situationLines.length" class="basis-card">
        <p class="eyebrow">사고상황</p>
        <ul class="plain-list">
          <li v-for="line in situationLines" :key="line">{{ line }}</li>
        </ul>
      </section>

      <section v-if="hasBaseFault" class="basis-card">
        <p class="eyebrow">기본과실</p>
        <KniaFaultRatioBar
          :a="baseFaultA"
          :b="baseFaultB"
          left-label="A"
          right-label="B"
          :caption="baseFaultLabel"
          variant="compact"
        />
      </section>
    </div>

    <section v-if="adjustmentFactors.length" class="basis-card knia-detail-adjustments">
      <div class="knia-detail-subhead">
        <p class="eyebrow">가감요소</p>
        <span class="chip">{{ adjustmentFactors.length }}개 수집</span>
      </div>
      <div class="knia-detail-factor-list">
        <div v-for="factor in adjustmentFactors" :key="factorKey(factor)" class="knia-detail-factor">
          <strong>{{ text(factor.label || factor.title) }}</strong>
          <span v-if="deltaText(factor)" class="factor-delta">{{ deltaText(factor) }}</span>
        </div>
      </div>
    </section>

    <div class="btn-row">
      <a v-if="safeKniaUrl(chart?.video_url || fallbackStandard?.video_url)" class="btn secondary" :href="safeKniaUrl(chart?.video_url || fallbackStandard?.video_url)" target="_blank" rel="noopener noreferrer">
        KNIA 관련 영상 보기
      </a>
      <a v-if="sourceUrl" class="btn secondary" :href="sourceUrl" target="_blank" rel="noopener noreferrer">
        KNIA 원문 기준 보기
      </a>
    </div>

    <p v-if="loading" class="kv">KNIA 상세 기준을 불러오는 중입니다.</p>
    <p v-else-if="error" class="kv">{{ error }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { api, formatApiError } from "../../api/client";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";
import KniaFaultRatioBar from "./KniaFaultRatioBar.vue";

const props = withDefaults(
  defineProps<{
    chartNo?: string | null;
    chartType?: string | null;
    fallbackStandard?: any;
  }>(),
  {
    chartNo: "",
    chartType: "1",
    fallbackStandard: null,
  },
);

const chart = ref<any>(null);
const loading = ref(false);
const error = ref("");

const chartNoText = computed(() => text(props.chartNo || props.fallbackStandard?.chart_no || props.fallbackStandard?.subchart_no));
const chartTypeText = computed(() => text(props.chartType || props.fallbackStandard?.chart_type || "1") || "1");
const displayTitle = computed(() =>
  chart.value?.title ||
  props.fallbackStandard?.title ||
  props.fallbackStandard?.chart_title ||
  (chartNoText.value ? `KNIA 과실비율 인정기준 ${chartNoText.value}` : "KNIA 과실비율 인정기준"),
);
const partyLabel = computed(() => resolveAccidentPartyLabel({
  accident_party_label: chart.value?.accident_party_label || props.fallbackStandard?.accident_party_label,
  accident_party_type: chart.value?.accident_party_type || props.fallbackStandard?.accident_party_type || props.fallbackStandard?.major_party_type,
  chart_no: chartNoText.value,
}));
const menuPath = computed(() => {
  const source = Array.isArray(chart.value?.category_path)
    ? chart.value.category_path
    : Array.isArray(props.fallbackStandard?.menu_path)
      ? props.fallbackStandard.menu_path
      : [];
  return source.map((item: unknown) => text(item)).filter(Boolean);
});
const summaryText = computed(() => text(
  chart.value?.accident_explanation ||
  chart.value?.scenario_summary_easy ||
  chart.value?.accident_summary ||
  props.fallbackStandard?.summary ||
  props.fallbackStandard?.match_reason ||
  "",
));
const situationLines = computed(() => {
  const lines = Array.isArray(chart.value?.accident_situation_lines) ? chart.value.accident_situation_lines : [];
  return dedupeSituationLines(lines.map((line: unknown) => text(line)).filter(Boolean));
});
const baseFaultA = computed(() => numberOr(chart.value?.base_fault_a, chart.value?.applied_fault_a, props.fallbackStandard?.base_fault?.A, props.fallbackStandard?.base_fault?.a, props.fallbackStandard?.base_fault?.my));
const baseFaultB = computed(() => numberOr(chart.value?.base_fault_b, chart.value?.applied_fault_b, props.fallbackStandard?.base_fault?.B, props.fallbackStandard?.base_fault?.b, props.fallbackStandard?.base_fault?.other));
const hasBaseFault = computed(() => baseFaultA.value !== null && baseFaultB.value !== null);
const baseFaultLabel = computed(() => hasBaseFault.value ? `기본 A ${baseFaultA.value}% / B ${baseFaultB.value}%` : "");
const adjustmentFactors = computed(() => Array.isArray(chart.value?.adjustment_factors) ? chart.value.adjustment_factors : []);
const sourceUrl = computed(() => safeKniaUrl(chart.value?.source_detail_url || chart.value?.source_url || props.fallbackStandard?.source_url || props.fallbackStandard?.button_url));

watch(
  () => [chartNoText.value, chartTypeText.value],
  async ([nextChartNo, nextChartType]) => {
    chart.value = null;
    error.value = "";
    if (!nextChartNo) return;
    loading.value = true;
    try {
      const response = await api.getKniaChart(nextChartNo, nextChartType || "1");
      chart.value = response?.chart || null;
    } catch (err) {
      error.value = formatApiError(err, "KNIA 상세 기준을 불러오지 못했습니다.");
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);

function text(value: unknown) {
  return sanitizeDisplayText(value, "");
}

function numberOr(...values: unknown[]) {
  for (const value of values) {
    if (value === null || value === undefined || value === "") continue;
    const n = Number(value);
    if (Number.isFinite(n)) return Math.max(0, Math.min(100, Math.round(n)));
  }
  return null;
}

function dedupeSituationLines(lines: string[]) {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const line of lines) {
    const normalized = line.replace(/\s+/g, " ").trim();
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    out.push(normalized);
  }
  if (out.length >= 3) {
    const first = out[0];
    const rest = out.slice(1).join(" ");
    if (rest && first.replace(/\s+/g, "") === rest.replace(/\s+/g, "")) return out.slice(1);
  }
  return out;
}

function factorKey(factor: any) {
  return `${factor?.factor_order ?? ""}-${factor?.label ?? factor?.title ?? ""}-${factor?.delta_a ?? ""}-${factor?.delta_b ?? ""}`;
}

function deltaText(factor: any) {
  const a = Number(factor?.delta_a || 0);
  const b = Number(factor?.delta_b || 0);
  const parts = [];
  if (Number.isFinite(a) && a) parts.push(`A ${a > 0 ? "+" : ""}${a}`);
  if (Number.isFinite(b) && b) parts.push(`B ${b > 0 ? "+" : ""}${b}`);
  return parts.join(" / ");
}

function safeKniaUrl(value: unknown) {
  const raw = String(value || "").trim();
  if (!raw || /\s/.test(raw)) return "";
  try {
    const url = new URL(raw);
    return ["http:", "https:"].includes(url.protocol) && url.hostname.toLowerCase() === "accident.knia.or.kr" ? url.toString() : "";
  } catch {
    return "";
  }
}

function resolveAccidentPartyLabel(input: { accident_party_label?: unknown; accident_party_type?: unknown; chart_no?: unknown }) {
  const existing = text(input.accident_party_label);
  if (existing && existing !== "확인이 필요합니다.") return existing;
  const type = String(input.accident_party_type || "").trim();
  const byType: Record<string, string> = {
    car_vs_car: "차대차 사고",
    vehicle_vs_vehicle: "차대차 사고",
    car_vs_person: "차대보행자 사고",
    pedestrian_crosswalk_accident: "차대보행자 사고",
    car_vs_bicycle: "차대자전거 사고",
    bicycle_collision: "차대자전거 사고",
    single_vehicle: "단독 사고",
    single_vehicle_accident: "단독 사고",
    object_collision: "물체/시설물 사고",
    car_vs_object: "물체/시설물 사고",
  };
  if (byType[type]) return byType[type];
  const chartNo = text(input.chart_no);
  if (chartNo.startsWith("차")) return "차대차 사고";
  if (chartNo.startsWith("보")) return "차대보행자 사고";
  if (chartNo.startsWith("자") || chartNo.startsWith("거")) return "차대자전거 사고";
  if (chartNo.startsWith("단")) return "단독 사고";
  if (chartNo.startsWith("기") || chartNo.startsWith("물")) return "물체/시설물 사고";
  return "확인이 필요합니다.";
}
</script>

<style scoped>
.knia-detail-evidence-card {
  display: grid;
  gap: 14px;
}

.knia-detail-head,
.knia-detail-subhead {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  min-width: 0;
}

.knia-detail-head h2 {
  margin: 0;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.knia-detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 0.9fr);
  gap: 12px;
}

.plain-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
  color: var(--text-sub);
  line-height: 1.65;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.knia-detail-adjustments {
  gap: 12px;
}

.knia-detail-factor-list {
  display: grid;
  gap: 8px;
}

.knia-detail-factor {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 11px 12px;
  border-radius: 12px;
  border: 1px solid rgba(201, 169, 98, 0.18);
  background: rgba(28, 23, 20, 0.34);
}

.knia-detail-factor strong {
  min-width: 0;
  color: var(--text-main);
  line-height: 1.4;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.factor-delta {
  display: inline-flex;
  justify-content: center;
  min-width: 5ch;
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(201, 169, 98, 0.13);
  border: 1px solid rgba(201, 169, 98, 0.28);
  color: var(--accent-strong);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.detail-ok {
  background: rgba(127, 231, 200, 0.12);
  border-color: rgba(127, 231, 200, 0.28);
  color: #9ff4da;
}

@media (max-width: 760px) {
  .knia-detail-head,
  .knia-detail-subhead {
    display: grid;
  }

  .knia-detail-grid {
    grid-template-columns: 1fr;
  }

  .knia-detail-factor {
    grid-template-columns: 1fr;
  }
}
</style>
