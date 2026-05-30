<template>
  <section class="knia-chart-page">
    <div class="btn-row top-actions">
      <RouterLink class="btn secondary" to="/knia/ranking">검색순위로 돌아가기</RouterLink>
      <button v-if="canCollectDetail" class="btn" :disabled="collectingDetail" @click="collectDetail">
        {{ collectingDetail ? '상세 기준 수집 중...' : '상세 기준 수집' }}
      </button>
      <a v-if="detailUrl" class="btn secondary" :href="detailUrl" target="_blank" rel="noopener noreferrer">KNIA 원문 보기</a>
    </div>
    <p v-if="collectMessage" class="notice success">{{ collectMessage }}</p>
    <p v-if="collectError" class="notice error">{{ collectError }}</p>

    <article v-if="chart" class="card hero-card detail-hero">
      <div>
        <p class="eyebrow">KNIA 과실비율 인정기준</p>
        <h2>{{ text(chart.title) }}</h2>
        <div class="chips">
          <span class="chip selected">기준번호 {{ text(chart.chart_no) }}</span>
          <span class="chip selected">{{ text(chart.accident_party_label || '사고유형 확인 필요') }}</span>
          <span v-if="baseFaultLabel" class="chip">{{ baseFaultLabel }}</span>
          <span v-if="chart.detail_collected_at" class="chip detail-ok">상세 수집 완료</span>
          <span v-else class="chip detail-needed">상세 기준 수집 필요</span>
        </div>
        <p v-if="chart.category_path?.length" class="kv">메뉴 경로: {{ chart.category_path.map(text).join(' > ') }}</p>
        <p v-if="chart.is_ranking_placeholder" class="soft-warning">
          이 항목은 검색순위에만 저장되어 있어 상세 기준 본문 수집이 필요합니다.
        </p>
        <p class="big-text">{{ text(chart.accident_explanation || chart.scenario_summary_easy || chart.accident_summary) }}</p>
      </div>
    </article>

    <article v-if="chart" class="card tab-card">
      <div class="knia-tabs" role="tablist" aria-label="KNIA 상세 정보 탭">
        <button v-for="tab in tabs" :key="tab.value" class="tab-button" :class="{ active: activeTab === tab.value }" @click="activeTab = tab.value">
          {{ tab.label }}
        </button>
      </div>

      <div v-if="activeTab === 'fault'" class="tab-panel fault-panel">
        <div class="fault-grid">
          <section class="glass-box">
            <p class="eyebrow">사고상황</p>
            <ul v-if="chart.accident_situation_lines?.length" class="plain-list">
              <li v-for="line in chart.accident_situation_lines" :key="line">{{ text(line) }}</li>
            </ul>
            <p v-else>{{ text(chart.accident_explanation || chart.accident_summary || '수집된 사고상황 설명이 없습니다.') }}</p>
          </section>
          <section class="glass-box">
            <p class="eyebrow">기본과실</p>
            <template v-if="hasBaseFault">
              <FaultBar :a="baseAForBar" :b="baseBForBar" />
              <p class="fault-caption">KNIA 원문 기본과실 A {{ baseAForBar }}% : B {{ baseBForBar }}%</p>
            </template>
            <p v-else class="empty-note compact-note">기본과실은 상세 기준 수집 후 표시됩니다.</p>
          </section>
          <section class="glass-box emphasis">
            <p class="eyebrow">사용자 수동 조정 결과</p>
            <template v-if="hasBaseFault">
              <FaultBar :a="manualFault.A" :b="manualFault.B" />
              <p class="fault-caption">선택한 가감요소 기준 A {{ manualFault.A }}% : B {{ manualFault.B }}%</p>
            </template>
            <p v-else class="empty-note compact-note">수동 조정 결과는 기본과실 수집 후 계산됩니다.</p>
          </section>
        </div>

        <div class="glass-box factor-box">
          <div class="section-heading compact">
            <div>
              <p class="eyebrow">가감요소</p>
              <h3>KNIA 원문 가감요소 표</h3>
            </div>
            <span class="kv">{{ adjustmentFactors.length }}개 수집</span>
          </div>
          <div v-if="adjustmentFactors.length" class="factor-table" role="list">
            <div class="factor-head"><span>적용</span><span>가감요소</span><span>A</span><span>B</span><span>근거</span></div>
            <label
              v-for="factor in adjustmentFactors"
              :key="factorKey(factor)"
              class="factor-row"
              :class="{ selected: isFactorSelected(factor) }"
              role="listitem"
            >
              <span class="factor-check">
                <input type="checkbox" :value="factorKey(factor)" v-model="manualSelected" />
              </span>
              <span class="factor-main">
                <span class="factor-label">{{ text(factor.label) }}</span>
                <span v-if="factor.description || factor.condition_text" class="factor-description">
                  {{ text(factor.description || factor.condition_text) }}
                </span>
                <span class="factor-mobile-meta">
                  <span :class="deltaClass(factor.delta_a)">A {{ formatDelta(factor.delta_a) }}</span>
                  <span :class="deltaClass(factor.delta_b)">B {{ formatDelta(factor.delta_b) }}</span>
                  <span class="factor-state" :class="{ selected: isFactorSelected(factor) }">
                    {{ isFactorSelected(factor) ? '선택됨' : '미선택' }}
                  </span>
                </span>
              </span>
              <span :class="deltaClass(factor.delta_a)">{{ formatDelta(factor.delta_a) }}</span>
              <span :class="deltaClass(factor.delta_b)">{{ formatDelta(factor.delta_b) }}</span>
              <span class="factor-source">{{ isFactorSelected(factor) ? '선택됨' : '미선택' }}</span>
            </label>
          </div>
          <p v-else class="empty-note">{{ missingDetailText('가감요소') }}</p>
        </div>

        <div class="glass-box">
          <p class="eyebrow">적용 조건</p>
          <p>{{ text(chart.applicable_text || '원문 기준에서 상세 조건을 확인해 주세요.') }}</p>
          <p class="eyebrow spacer">주의할 점</p>
          <p>{{ text(chart.non_applicable_text || '사고 세부 상황에 따라 다른 기준이 적용될 수 있습니다.') }}</p>
        </div>
      </div>

      <div v-else-if="activeTab === 'adjustment'" class="tab-panel cards-panel">
        <article v-for="item in adjustmentExplanations" :key="item.title + item.body" class="reference-card">
          <span class="mini-badge">KNIA 원문 수정요소해설</span>
          <h3>{{ text(item.title || '수정요소해설') }}</h3>
          <p>{{ text(item.body) }}</p>
        </article>
        <p v-if="!adjustmentExplanations.length" class="empty-note">{{ missingDetailText('수정요소해설') }}</p>
      </div>

      <div v-else-if="activeTab === 'laws'" class="tab-panel cards-panel">
        <article v-for="item in relatedLaws" :key="item.law_title + item.law_text" class="reference-card law-card">
          <span class="mini-badge">KNIA 원문 관련법규</span>
          <h3>{{ text(item.law_title || '관련 법규') }}</h3>
          <p>{{ text(item.law_text) }}</p>
        </article>
        <p v-if="!relatedLaws.length" class="empty-note">{{ missingDetailText('관련법규') }}</p>
      </div>

      <div v-else class="tab-panel cards-panel">
        <article v-for="item in caseReferences" :key="item.case_title + item.case_body" class="reference-card case-card">
          <span class="mini-badge">KNIA 원문 판례·조정사례</span>
          <h3>{{ text(item.case_title || '판례·조정사례') }}</h3>
          <p>{{ text(item.case_body) }}</p>
          <p v-if="item.decision_summary" class="decision">요약: {{ text(item.decision_summary) }}</p>
        </article>
        <p v-if="!caseReferences.length" class="empty-note">{{ missingDetailText('판례·조정사례') }}</p>
      </div>
    </article>

    <article v-if="chart" class="card source-card">
      <KniaVideoLinkCard :video="videoCard" />
      <p class="kv">{{ text(chart.attribution || '자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털') }}</p>
      <p class="soft-warning">위 계산과 법규 및 사례는 KNIA 과실비율정보포털 원문 기준에서 수집한 참고 근거입니다. 최종 과실비율과 법적 판단은 보험사·분쟁심의위·수사기관·법원의 판단에 따라 달라질 수 있습니다.</p>
    </article>

    <article v-if="loading" class="card"><h2>불러오는 중입니다</h2><p>KNIA 상세 기준을 확인하고 있습니다.</p></article>
    <article v-else-if="error" class="card state-card error-state">
      <h2>KNIA 기준을 불러오지 못했습니다</h2>
      <p>{{ error }}</p>
      <RouterLink class="btn secondary" to="/knia/ranking">검색순위로 돌아가기</RouterLink>
    </article>
    <article v-else-if="!chart" class="card state-card">
      <h2>기준을 찾을 수 없습니다</h2>
      <p>저장된 KNIA 기준에 해당 기준번호가 없습니다. 검색순위 화면에서 기준번호를 다시 선택하거나 관리자 수집 작업을 먼저 실행해야 합니다.</p>
      <RouterLink class="btn secondary" to="/knia/ranking">검색순위로 돌아가기</RouterLink>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, formatApiError } from "../api/client";
import KniaVideoLinkCard from "../components/knia/KniaVideoLinkCard.vue";
import { useSessionStore } from "../stores/session";
import { sanitizeDisplayText } from "../utils/displaySanitizer";

const route = useRoute();
const session = useSessionStore();
const chart = ref<any>(null);
const loading = ref(false);
const error = ref("");
const collectingDetail = ref(false);
const collectMessage = ref("");
const collectError = ref("");
const activeTab = ref("fault");
const manualSelected = ref<string[]>([]);
const tabs = [
  { value: "fault", label: "과실비율" },
  { value: "adjustment", label: "수정요소해설" },
  { value: "laws", label: "관련법규" },
  { value: "cases", label: "판례·조정사례" },
];

const baseA = computed(() => numberOr(chart.value?.base_fault_a, chart.value?.applied_fault_a));
const baseB = computed(() => numberOr(chart.value?.base_fault_b, chart.value?.applied_fault_b));
const hasBaseFault = computed(() => baseA.value !== null && baseB.value !== null);
const baseAForBar = computed(() => baseA.value ?? 0);
const baseBForBar = computed(() => baseB.value ?? 0);
const baseFaultLabel = computed(() => hasBaseFault.value ? `기본 A ${baseAForBar.value}% / B ${baseBForBar.value}%` : "");
const detailUrl = computed(() => safeKniaUrl(chart.value?.source_detail_url || chart.value?.source_url));
const adjustmentFactors = computed(() => Array.isArray(chart.value?.adjustment_factors) ? chart.value.adjustment_factors : []);
const adjustmentExplanations = computed(() => Array.isArray(chart.value?.adjustment_explanations) ? chart.value.adjustment_explanations : []);
const relatedLaws = computed(() => Array.isArray(chart.value?.related_laws) ? chart.value.related_laws : []);
const caseReferences = computed(() => Array.isArray(chart.value?.case_references) ? chart.value.case_references : []);
const isAdmin = computed(() => session.user?.role === "admin");
const canCollectDetail = computed(() => Boolean(chart.value?.chart_no) && isAdmin.value && !chart.value?.detail_collected_at);
const manualFault = computed(() => {
  if (!hasBaseFault.value) return { A: 0, B: 0 };
  let a = baseAForBar.value;
  for (const factor of adjustmentFactors.value) {
    if (!manualSelected.value.includes(factorKey(factor))) continue;
    const da = Number(factor.delta_a || 0);
    const db = Number(factor.delta_b || 0);
    if (da) a += da;
    if (db) a -= db;
  }
  a = Math.max(0, Math.min(100, Math.round(a)));
  return { A: a, B: 100 - a };
});
const videoCard = computed(() => ({
  title: "KNIA 원문 기준 및 관련 영상",
  description: "과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다.",
  source_url: safeKniaUrl(chart.value?.video_url || chart.value?.source_detail_url || chart.value?.source_url),
  video_url: safeKniaUrl(chart.value?.video_url) || undefined,
  source_detail_url: safeKniaUrl(chart.value?.source_detail_url) || undefined,
  source_page_url: safeKniaUrl(chart.value?.source_url) || undefined,
  embed_url: null,
  media_embed_url: chart.value?.media_embed_url,
  thumbnail_url: safeThumbnail(chart.value?.thumbnail_url),
  display_mode: "external_link",
  button_label: chart.value?.video_url ? "KNIA 관련 영상 보기" : "KNIA 원문 기준 보기",
  notice: "영상 파일은 LawCompass 서버에 저장하지 않고, 과실비율정보포털 원본 링크로만 제공합니다.",
  has_knia_candidate: Boolean(chart.value?.chart_no),
  missing_source_notice: "수집된 KNIA 원문 링크가 없습니다. 관리자 KNIA 상세 수집을 먼저 실행해 주세요.",
  source_label: "자료 출처: 과실비율정보포털"
}));

async function load() {
  loading.value = true;
  error.value = "";
  collectError.value = "";
  try {
    const chartType = String(route.query.chartType || "1");
    const data = await api.getKniaChart(route.params.chartNo as string, chartType);
    chart.value = data.chart;
    manualSelected.value = [];
  } catch (e) {
    chart.value = null;
    manualSelected.value = [];
    error.value = formatApiError(e, "KNIA 상세 기준 조회에 실패했습니다.");
  } finally {
    loading.value = false;
  }
}

async function collectDetail() {
  if (!chart.value?.chart_no) return;
  collectingDetail.value = true;
  collectMessage.value = "";
  collectError.value = "";
  try {
    const chartNo = String(chart.value.chart_no);
    const result = await api.adminCollectKnia({ menu: false, ranking: false, charts: true, chart_nos: [chartNo], max_charts: 1 });
    await load();
    const chartResult = result?.result?.charts ?? {};
    const errors = Array.isArray(chartResult?.errors) ? chartResult.errors.filter(Boolean) : [];
    if (chart.value?.detail_collected_at) {
      collectMessage.value = `${chartNo} 상세 기준을 수집했습니다.`;
    } else {
      collectError.value = errors.length
        ? `상세 기준 본문이 아직 저장되지 않았습니다.\n${errors.join("\n")}`
        : "수집 요청은 완료됐지만 상세 기준 본문이 저장되지 않았습니다. KNIA 원문 응답 또는 파서 결과를 확인해야 합니다.";
    }
  } catch (e) {
    collectError.value = formatApiError(e, "KNIA 상세 기준 수집에 실패했습니다.");
  } finally {
    collectingDetail.value = false;
  }
}

function numberOr(...values: any[]) {
  for (const value of values) {
    if (value === null || value === undefined || value === "") continue;
    const n = Number(value);
    if (Number.isFinite(n)) return n;
  }
  return null;
}
function text(value: unknown) { return sanitizeDisplayText(value); }
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
function safeThumbnail(value: unknown) {
  const url = safeKniaUrl(value);
  return url.includes("logo_test.jpg") ? "" : url;
}
function factorKey(factor: any) { return `${factor.factor_order ?? factor.label}-${factor.label}-${factor.delta_a}-${factor.delta_b}`; }
function isFactorSelected(factor: any) {
  return manualSelected.value.includes(factorKey(factor));
}
function formatDelta(value: any) {
  const n = Number(value || 0);
  return n > 0 ? `+${n}` : String(n);
}
function deltaClass(value: any) {
  const n = Number(value || 0);
  return { delta: true, plus: n > 0, minus: n < 0 };
}
function missingDetailText(label: string) {
  return chart.value?.detail_collected_at
    ? `수집된 ${label}가 없습니다. KNIA 원문에 해당 항목이 없거나 파싱 가능한 표/문단이 없을 수 있습니다.`
    : `${label}는 상세 기준 수집 후 표시됩니다. 현재는 ranking 또는 기본 기준 정보만 저장된 상태입니다.`;
}

const FaultBar = defineComponent({
  props: { a: { type: Number, required: true }, b: { type: Number, required: true } },
  setup(props) {
    function normalizeFaultPair(a: unknown, b: unknown) {
      const aRaw = toPercent(a, 0);
      const bRaw = toPercent(b, 0);
      const total = aRaw + bRaw;
      if (total <= 0) return { a: 50, b: 50, isUnknown: true };
      if (total === 100) return { a: aRaw, b: bRaw, isUnknown: false };
      const nextA = Math.round((aRaw / total) * 100);
      return { a: nextA, b: 100 - nextA, isUnknown: false };
    }

    function toPercent(value: unknown, fallback = 0) {
      const n = Number(value);
      if (!Number.isFinite(n)) return fallback;
      return Math.max(0, Math.min(100, Math.round(n)));
    }

    return () => {
      const normalized = normalizeFaultPair(props.a, props.b);
      const aTiny = normalized.a > 0 && normalized.a < 14;
      const bTiny = normalized.b > 0 && normalized.b < 14;
      const splitLeft = normalized.a <= 0
        ? "38px"
        : normalized.a >= 100
          ? "calc(100% - 38px)"
          : `clamp(38px, ${normalized.a}%, calc(100% - 38px))`;

      return h("div", { class: "fault-bar-wrap fault-ratio-visual" }, [
        h(
          "div",
          { class: "fault-party-labels", "aria-hidden": "true" },
          [
            h("span", { class: "fault-party-label fault-party-a" }, "왼쪽 A"),
            h("span", { class: "fault-party-label fault-party-b" }, "오른쪽 B"),
          ]
        ),
        h(
          "div",
          { class: "fault-track-shell" },
          [
            h(
              "div",
              {
                class: ["fault-bar", { "is-unknown": normalized.isUnknown }],
                role: "img",
                "aria-label": normalized.isUnknown ? "기준 과실 수집 필요" : `A ${normalized.a}%, B ${normalized.b}%`,
              },
              [
                h(
                  "div",
                  {
                    class: [
                      "fault-segment",
                      "fault-a",
                      {
                        "is-zero": normalized.a <= 0,
                        "is-full": normalized.a >= 100,
                        "is-tiny": aTiny,
                      },
                    ],
                    style: { flexBasis: `${normalized.a}%` },
                  },
                  normalized.a > 0 ? [h("span", { class: "fault-percent" }, `A ${normalized.a}%`)] : []
                ),
                h(
                  "div",
                  {
                    class: [
                      "fault-segment",
                      "fault-b",
                      {
                        "is-zero": normalized.b <= 0,
                        "is-full": normalized.b >= 100,
                        "is-tiny": bTiny,
                      },
                    ],
                    style: { flexBasis: `${normalized.b}%` },
                  },
                  normalized.b > 0 ? [h("span", { class: "fault-percent" }, `B ${normalized.b}%`)] : []
                ),
              ]
            ),
            h(
              "div",
              {
                class: "fault-split-marker",
                style: { left: splitLeft },
                "aria-hidden": "true",
              },
              [h("span", {}, `${normalized.a}:${normalized.b}`)]
            ),
          ]
        ),
        h(
          "div",
          { class: "fault-ratio-readout", "aria-hidden": "true" },
          [h("span", {}, `A ${normalized.a}%`), h("span", {}, `B ${normalized.b}%`)]
        ),
      ]);
    };
  }
});

watch(() => route.fullPath, () => {
  collectMessage.value = "";
  load();
});
onMounted(load);
</script>

<style scoped>
.knia-chart-page { display: grid; gap: 18px; }
.top-actions { justify-content: space-between; }
.notice { padding: 12px 14px; border-radius: 16px; font-weight: 800; }
.notice.success { background: rgba(167, 193, 122, 0.13); border: 1px solid rgba(167, 193, 122, 0.35); color: #d7e7b7; }
.notice.error { background: rgba(255, 112, 132, 0.13); border: 1px solid rgba(255, 112, 132, 0.35); color: #ffb7c3; white-space: pre-line; }
.detail-hero { border-color: rgba(201, 169, 98, 0.34); }
.detail-ok { background: rgba(167, 193, 122, 0.14); color: #d7e7b7; }
.detail-needed { background: rgba(251, 191, 36, 0.13); color: #fde68a; }
.tab-card { display: grid; gap: 18px; overflow: hidden; }
.knia-tabs { display: flex; flex-wrap: wrap; gap: 10px; padding: 8px; border-radius: 18px; background: rgba(28, 23, 20, 0.58); border: 1px solid rgba(201, 169, 98, 0.28); box-shadow: inset 0 1px 0 rgba(232, 223, 212, 0.06); }
.tab-button { box-sizing: border-box; min-height: 44px; border: 1px solid rgba(201, 169, 98, 0.28); background: rgba(232, 223, 212, 0.08); color: var(--text-sub); border-radius: 999px; padding: 11px 16px; font-weight: 900; font-size: 0.96rem; cursor: pointer; transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease; }
.tab-button:hover { transform: translateY(-1px); border-color: rgba(201, 169, 98, 0.48); color: var(--text-main); }
.tab-button.active { background: linear-gradient(135deg, var(--accent), var(--accent-strong)); border-color: rgba(201, 169, 98, 0.78); color: var(--accent-foreground); box-shadow: 0 10px 24px rgba(201, 169, 98, 0.20); }
.tab-panel { display: grid; gap: 16px; }
.fault-grid { display: grid; grid-template-columns: 1.1fr 1fr 1fr; gap: 14px; }
.glass-box, .reference-card { border: 1px solid rgba(201, 169, 98, 0.28); background: linear-gradient(145deg, rgba(61, 51, 43, 0.84), rgba(37, 30, 25, 0.92)); border-radius: 18px; padding: 18px; box-shadow: 0 18px 42px rgba(0,0,0,0.22); }
.glass-box.emphasis { border-color: rgba(201, 169, 98, 0.48); background: linear-gradient(145deg, rgba(201, 169, 98, 0.15), rgba(37, 30, 25, 0.92)); }
.plain-list { margin: 0; padding-left: 18px; display: grid; gap: 8px; }
.fault-bar-wrap { display: grid; gap: 10px; min-width: 0; }
.fault-party-labels,
.fault-ratio-readout { display: flex; justify-content: space-between; gap: 10px; }
.fault-party-label { display: inline-flex; align-items: center; min-height: 26px; padding: 4px 9px; border-radius: 999px; border: 1px solid rgba(201, 169, 98, 0.28); background: rgba(28, 23, 20, 0.44); color: var(--text-sub); font-size: 0.82rem; font-weight: 900; }
.fault-party-a { color: #ffe4e7; border-color: rgba(213, 137, 137, 0.34); }
.fault-party-b { color: var(--accent-strong); }
.fault-track-shell { position: relative; min-width: 0; padding: 10px 0; }
.fault-bar { display: flex; width: 100%; height: 58px; overflow: hidden; border-radius: 16px; border: 1px solid rgba(201, 169, 98, 0.38); background: rgba(28, 23, 20, 0.62); box-shadow: inset 0 1px 0 rgba(232, 223, 212, 0.08), 0 14px 28px rgba(0,0,0,0.22); clip-path: polygon(14px 0, calc(100% - 14px) 0, 100% 50%, calc(100% - 14px) 100%, 14px 100%, 0 50%); }
.fault-segment { position: relative; display: grid; place-items: center; min-width: 0; flex-grow: 0; flex-shrink: 0; height: 100%; overflow: hidden; font-weight: 950; font-size: 0.95rem; line-height: 1; white-space: nowrap; transition: flex-basis 0.2s ease, opacity 0.18s ease; }
.fault-segment::after { content: ""; position: absolute; inset: 0; pointer-events: none; background: linear-gradient(180deg, rgba(255,255,255,0.18), transparent 45%, rgba(0,0,0,0.14)); }
.fault-percent { position: relative; z-index: 1; display: inline-flex; align-items: center; justify-content: center; min-width: 5ch; padding: 0 8px; font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; text-shadow: 0 1px 10px rgba(0,0,0,0.32); }
.fault-a { background: linear-gradient(135deg, #8B2635, #B84B55); color: #FFF2F2; }
.fault-b { background: linear-gradient(135deg, var(--accent-dark), var(--accent-strong)); color: var(--accent-foreground); }
.fault-segment.is-zero { min-width: 0; flex-basis: 0% !important; width: 0 !important; padding: 0; opacity: 0; overflow: hidden; }
.fault-segment.is-zero span { display: none; }
.fault-segment.is-full { flex-basis: 100% !important; }
.fault-segment.is-tiny .fault-percent { display: none; }
.fault-split-marker { position: absolute; top: 50%; z-index: 2; transform: translate(-50%, -50%); display: grid; place-items: center; min-width: 52px; height: 34px; padding: 0 9px; clip-path: polygon(12px 0, calc(100% - 12px) 0, 100% 50%, calc(100% - 12px) 100%, 12px 100%, 0 50%); border: 1px solid rgba(255,255,255,0.18); background: linear-gradient(135deg, #251E19, #C9A962 52%, #251E19); color: #1C1714; box-shadow: 0 10px 22px rgba(0,0,0,0.34); font-size: 0.82rem; font-weight: 950; font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
.fault-split-marker span { position: relative; z-index: 1; min-width: 4.8ch; text-align: center; }
.fault-ratio-readout { color: var(--text-sub); font-weight: 850; }
.fault-ratio-readout span { min-width: 5ch; font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
.fault-caption { margin: 10px 0 0; color: var(--text-sub); font-weight: 800; line-height: 1.5; }
.factor-box { display: grid; gap: 14px; }
.factor-table { display: grid; gap: 10px; width: 100%; overflow: hidden; }
.factor-head, .factor-row { display: grid; grid-template-columns: 56px minmax(220px, 1fr) 74px 74px 112px; gap: 10px; align-items: center; }
.factor-head { color: var(--text-faint); font-size: 0.84rem; font-weight: 950; padding: 0 12px; }
.factor-row { box-sizing: border-box; min-width: 0; padding: 14px 12px; border-radius: 16px; background: rgba(37, 30, 25, 0.72); border: 1px solid rgba(201, 169, 98, 0.20); cursor: pointer; transition: border-color 0.16s ease, background-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease; }
.factor-row:hover { transform: translateY(-1px); border-color: rgba(201, 169, 98, 0.42); background: rgba(61, 51, 43, 0.86); }
.factor-row.selected { border-color: rgba(201, 169, 98, 0.64); background: linear-gradient(145deg, rgba(201, 169, 98, 0.18), rgba(61, 51, 43, 0.90)); box-shadow: 0 12px 28px rgba(201, 169, 98, 0.12); }
.factor-check { display: grid; place-items: center; min-width: 44px; min-height: 44px; }
.factor-row input[type="checkbox"] { width: 22px; height: 22px; accent-color: var(--accent); cursor: pointer; }
.factor-main { display: grid; gap: 5px; min-width: 0; }
.factor-label { color: var(--text-main); font-size: 0.98rem; font-weight: 900; line-height: 1.4; word-break: keep-all; overflow-wrap: anywhere; }
.factor-description { color: var(--text-sub); font-size: 0.9rem; line-height: 1.45; }
.factor-mobile-meta { display: none; flex-wrap: wrap; gap: 7px; margin-top: 4px; }
.delta { display: inline-flex; align-items: center; justify-content: center; min-height: 30px; width: fit-content; min-width: 5ch; padding: 5px 10px; border-radius: 999px; font-weight: 950; font-size: 0.92rem; border: 1px solid rgba(232, 223, 212, 0.12); font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
.delta.plus { color: #FFD3C9; background: rgba(139, 38, 53, 0.28); border-color: rgba(213, 137, 137, 0.32); }
.delta.minus { color: #BDEEDB; background: rgba(127, 231, 200, 0.12); border-color: rgba(127, 231, 200, 0.28); }
.factor-source, .mini-badge, .factor-state { display: inline-flex; align-items: center; justify-content: center; width: fit-content; min-height: 30px; padding: 5px 10px; border-radius: 999px; background: rgba(232, 223, 212, 0.08); border: 1px solid rgba(201, 169, 98, 0.24); color: var(--text-sub); font-size: 0.84rem; font-weight: 900; }
.factor-row.selected .factor-source, .factor-state.selected { background: var(--accent-soft); border-color: rgba(201, 169, 98, 0.48); color: var(--accent-strong); }
.cards-panel { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.reference-card h3 { margin: 10px 0 8px; font-size: 1.08rem; }
.reference-card p { white-space: pre-line; line-height: 1.75; }
.law-card { border-color: rgba(96, 165, 250, 0.24); }
.case-card { border-color: rgba(251, 191, 36, 0.24); }
.decision { color: #fde68a; }
.empty-note { color: var(--text-sub); padding: 16px; border-radius: 16px; border: 1px dashed rgba(201, 169, 98, 0.28); background: rgba(28, 23, 20, 0.34); }
.compact-note { margin: 0; padding: 12px; }
.spacer { margin-top: 16px; }
.source-card { display: grid; gap: 12px; }
.state-card { display: grid; gap: 12px; justify-items: start; }
.error-state { border-color: rgba(255, 112, 132, 0.35); }
@media (max-width: 900px) {
  .fault-grid { grid-template-columns: 1fr; }
  .factor-head { display: none; }
  .factor-table { gap: 12px; }
  .factor-row { grid-template-columns: 48px minmax(0, 1fr); gap: 12px; align-items: flex-start; padding: 16px; }
  .factor-row > .delta, .factor-row > .factor-source { display: none; }
  .factor-mobile-meta { display: flex; }
  .factor-label { font-size: 1rem; }
  .factor-description { font-size: 0.92rem; }
}
@media (max-width: 640px) {
  .knia-tabs { flex-wrap: nowrap; overflow-x: auto; padding: 8px; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; }
  .tab-button { flex: 0 0 auto; scroll-snap-align: start; min-height: 46px; padding: 12px 15px; font-size: 0.95rem; white-space: nowrap; }
  .fault-bar { height: 50px; border-radius: 14px; clip-path: polygon(11px 0, calc(100% - 11px) 0, 100% 50%, calc(100% - 11px) 100%, 11px 100%, 0 50%); }
  .fault-segment { font-size: 0.86rem; min-width: 0; }
  .fault-split-marker { min-width: 46px; height: 30px; font-size: 0.76rem; }
  .fault-party-label { font-size: 0.76rem; }
}
@media (max-width: 480px) {
  .factor-row { padding: 15px 14px; border-radius: 15px; }
  .factor-check { min-width: 42px; min-height: 42px; }
}
</style>
