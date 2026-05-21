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
            <FaultBar :a="baseA" :b="baseB" />
            <p class="fault-caption">KNIA 원문 기본과실 A{{ baseA }} : B{{ baseB }}</p>
          </section>
          <section class="glass-box emphasis">
            <p class="eyebrow">사용자 수동 조정 결과</p>
            <FaultBar :a="manualFault.A" :b="manualFault.B" />
            <p class="fault-caption">선택한 가감요소 기준 A{{ manualFault.A }} : B{{ manualFault.B }}</p>
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
          <div v-if="adjustmentFactors.length" class="factor-table">
            <div class="factor-head"><span>적용</span><span>가감요소</span><span>A</span><span>B</span><span>근거</span></div>
            <label v-for="factor in adjustmentFactors" :key="factorKey(factor)" class="factor-row">
              <input type="checkbox" :value="factorKey(factor)" v-model="manualSelected" />
              <span class="factor-label">{{ text(factor.label) }}</span>
              <span :class="deltaClass(factor.delta_a)">{{ formatDelta(factor.delta_a) }}</span>
              <span :class="deltaClass(factor.delta_b)">{{ formatDelta(factor.delta_b) }}</span>
              <span class="factor-source">KNIA 원문</span>
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

const baseA = computed(() => numberOr(chart.value?.base_fault_a, chart.value?.applied_fault_a, 50));
const baseB = computed(() => numberOr(chart.value?.base_fault_b, chart.value?.applied_fault_b, 100 - baseA.value));
const baseFaultLabel = computed(() => `기본 A ${baseA.value}% / B ${baseB.value}%`);
const detailUrl = computed(() => chart.value?.source_detail_url || chart.value?.source_url || "");
const adjustmentFactors = computed(() => Array.isArray(chart.value?.adjustment_factors) ? chart.value.adjustment_factors : []);
const adjustmentExplanations = computed(() => Array.isArray(chart.value?.adjustment_explanations) ? chart.value.adjustment_explanations : []);
const relatedLaws = computed(() => Array.isArray(chart.value?.related_laws) ? chart.value.related_laws : []);
const caseReferences = computed(() => Array.isArray(chart.value?.case_references) ? chart.value.case_references : []);
const isAdmin = computed(() => session.user?.role === "admin");
const canCollectDetail = computed(() => Boolean(chart.value?.chart_no) && isAdmin.value && !chart.value?.detail_collected_at);
const manualFault = computed(() => {
  let a = baseA.value;
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
  title: "관련 영상 또는 원문 보기",
  source_url: chart.value?.video_url || chart.value?.source_detail_url || chart.value?.source_url,
  embed_url: chart.value?.media_embed_url,
  thumbnail_url: chart.value?.thumbnail_url,
  button_label: chart.value?.video_url ? "과실비율정보포털에서 관련 영상 보기" : "원문 기준 보기",
  notice: "영상 파일은 LawCompass 서버에 저장하지 않고, 원본 사이트 링크로만 제공합니다.",
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
    await api.adminCollectKnia({ menu: false, ranking: false, charts: true, chart_nos: [chartNo], max_charts: 1 });
    collectMessage.value = `${chartNo} 상세 기준을 수집했습니다. 화면을 다시 불러옵니다.`;
    await load();
  } catch (e) {
    collectError.value = formatApiError(e, "KNIA 상세 기준 수집에 실패했습니다.");
  } finally {
    collectingDetail.value = false;
  }
}

function numberOr(...values: any[]) {
  for (const value of values) {
    const n = Number(value);
    if (Number.isFinite(n)) return n;
  }
  return 0;
}
function text(value: unknown) { return sanitizeDisplayText(value); }
function factorKey(factor: any) { return `${factor.factor_order ?? factor.label}-${factor.label}-${factor.delta_a}-${factor.delta_b}`; }
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
    return () => h("div", { class: "fault-bar" }, [
      h("div", { class: "fault-a", style: { width: `${props.a}%` } }, `A ${props.a}%`),
      h("div", { class: "fault-b", style: { width: `${props.b}%` } }, `B ${props.b}%`),
    ]);
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
.notice.success { background: rgba(53, 211, 154, 0.13); border: 1px solid rgba(53, 211, 154, 0.35); color: #9ff5d4; }
.notice.error { background: rgba(255, 112, 132, 0.13); border: 1px solid rgba(255, 112, 132, 0.35); color: #ffb7c3; white-space: pre-line; }
.detail-hero { border-color: rgba(76, 216, 255, 0.28); }
.detail-ok { background: rgba(57, 255, 194, 0.14); color: #9ff5d4; }
.detail-needed { background: rgba(251, 191, 36, 0.13); color: #fde68a; }
.tab-card { display: grid; gap: 18px; }
.knia-tabs { display: flex; flex-wrap: wrap; gap: 10px; padding: 8px; border-radius: 20px; background: rgba(5, 12, 24, 0.45); border: 1px solid rgba(255,255,255,0.09); }
.tab-button { border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.05); color: #dbeafe; border-radius: 999px; padding: 11px 16px; font-weight: 800; cursor: pointer; }
.tab-button.active { background: linear-gradient(135deg, rgba(45, 212, 191, 0.28), rgba(59, 130, 246, 0.26)); border-color: rgba(96, 239, 255, 0.45); color: white; box-shadow: 0 10px 30px rgba(37, 99, 235, 0.18); }
.tab-panel { display: grid; gap: 16px; }
.fault-grid { display: grid; grid-template-columns: 1.1fr 1fr 1fr; gap: 14px; }
.glass-box, .reference-card { border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.055); border-radius: 22px; padding: 18px; box-shadow: 0 18px 48px rgba(0,0,0,0.18); }
.glass-box.emphasis { border-color: rgba(45, 212, 191, 0.32); }
.plain-list { margin: 0; padding-left: 18px; display: grid; gap: 8px; }
.fault-bar { display: flex; height: 42px; overflow: hidden; border-radius: 999px; border: 1px solid rgba(255,255,255,0.16); background: rgba(0,0,0,0.18); }
.fault-a, .fault-b { display: grid; place-items: center; min-width: 42px; font-weight: 900; font-size: 0.9rem; transition: width 0.2s ease; }
.fault-a { background: linear-gradient(135deg, #fb7185, #f97316); color: white; }
.fault-b { background: linear-gradient(135deg, #f59e0b, #facc15); color: #2b1700; }
.fault-caption { margin: 10px 0 0; color: #cbd5e1; font-weight: 700; }
.factor-box { display: grid; gap: 12px; }
.factor-table { display: grid; gap: 8px; }
.factor-head, .factor-row { display: grid; grid-template-columns: 54px minmax(220px, 1fr) 64px 64px 110px; gap: 10px; align-items: center; }
.factor-head { color: #9fb1ca; font-size: 0.82rem; font-weight: 900; padding: 0 10px; }
.factor-row { padding: 12px 10px; border-radius: 16px; background: rgba(10, 22, 40, 0.55); border: 1px solid rgba(255,255,255,0.08); cursor: pointer; }
.factor-row input { width: 18px; height: 18px; }
.factor-label { font-weight: 800; color: #f8fafc; }
.delta { font-weight: 900; }
.delta.plus { color: #ffb4a8; }
.delta.minus { color: #8dd7ff; }
.factor-source, .mini-badge { color: #9ff5d4; font-weight: 800; font-size: 0.82rem; }
.cards-panel { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.reference-card h3 { margin: 10px 0 8px; font-size: 1.08rem; }
.reference-card p { white-space: pre-line; line-height: 1.75; }
.law-card { border-color: rgba(96, 165, 250, 0.24); }
.case-card { border-color: rgba(251, 191, 36, 0.24); }
.decision { color: #fde68a; }
.empty-note { color: #cbd5e1; padding: 16px; border-radius: 16px; border: 1px dashed rgba(255,255,255,0.16); }
.spacer { margin-top: 16px; }
.source-card { display: grid; gap: 12px; }
.state-card { display: grid; gap: 12px; justify-items: start; }
.error-state { border-color: rgba(255, 112, 132, 0.35); }
@media (max-width: 900px) {
  .fault-grid { grid-template-columns: 1fr; }
  .factor-head { display: none; }
  .factor-row { grid-template-columns: 36px 1fr; }
  .factor-row .delta, .factor-row .factor-source { grid-column: 2; }
}
</style>
