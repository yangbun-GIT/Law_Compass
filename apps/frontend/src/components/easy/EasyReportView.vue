<template>
  <section class="easy-report" v-if="safeReport">
    <section v-if="isUserFriendlyMode" class="user-report">
      <section class="card easy-card simple-section corner-flourish">
        <p class="eyebrow">현재 상황정리</p>
        <h2>사고 상황을 간단히 정리했어요</h2>
        <p class="big-text">{{ simpleSituationSummary }}</p>
      </section>

      <section class="card easy-card simple-section corner-flourish">
        <p class="eyebrow">과실비율산정</p>
        <h2>예상 과실비율</h2>
        <div class="easy-ratio-row">
          <div>
            <p>내 과실</p>
            <span>{{ simpleFaultRatio.my ?? simpleFaultRatio.my_percent ?? simpleFaultRatio.my_fault ?? "확인 필요" }}</span>
          </div>
          <div>
            <p>상대 과실</p>
            <span class="accent">{{ simpleFaultRatio.other ?? simpleFaultRatio.other_percent ?? simpleFaultRatio.opponent_fault ?? "확인 필요" }}</span>
          </div>
        </div>
        <p class="easy-summary">
          {{ simpleFaultRatio.basis || simpleFaultRatio.summary || safeReport?.fault_ratio_summary || "입력한 사고 사실과 KNIA 기준을 함께 검토한 참고용 산정입니다." }}
        </p>
        <p v-if="simpleFaultRatio.reference_only" class="kv">확정값이 아니라 참고 범위입니다.</p>
        <ul v-if="simpleFaultRatio.key_factors?.length" class="check-list">
          <li v-for="factor in simpleFaultRatio.key_factors.slice(0, 4)" :key="String(factor)">
            {{ text(factor) }}
          </li>
        </ul>
      </section>

      <section class="card easy-card simple-section corner-flourish">
        <p class="eyebrow">관련 KNIA 근거 및 영상</p>
        <h2>가장 가까운 기준</h2>
        <div v-if="simpleKniaEvidence" class="basis-card">
          <p class="accent-text">
            {{ simpleKniaEvidence.chart_no || simpleKniaEvidence.subchart_no || "KNIA 기준 확인 중" }}
            <span v-if="simpleKniaEvidence.title"> · {{ text(simpleKniaEvidence.title) }}</span>
          </p>
          <p v-if="simpleKniaEvidence.menu_path?.length">
            {{ simpleKniaEvidence.menu_path.map(text).join(" > ") }}
          </p>
          <p v-if="simpleKniaEvidence.match_reason || simpleKniaEvidence.why_matched">
            {{ text(simpleKniaEvidence.match_reason || simpleKniaEvidence.why_matched) }}
          </p>
          <a v-if="simpleKniaEvidence.source_url" :href="simpleKniaEvidence.source_url" target="_blank" rel="noopener noreferrer">
            KNIA 원문 보기
          </a>
          <p v-if="simpleKniaEvidence.source_url_is_fallback" class="kv">
            원문 링크 형식은 차트번호 기반으로 생성되었습니다.
          </p>
        </div>
        <p v-else class="easy-summary">현재 사고와 가까운 KNIA 기준을 확인하고 있습니다.</p>
        <div v-if="simpleVideoSummary" class="soft-warning">
          <strong>영상에서 확인한 점</strong>
          <p>{{ simpleVideoSummary }}</p>
        </div>
      </section>
    </section>

    <section v-else class="expert-report">
      <TopConclusionCard :report="safeReport" />
      <AccidentPartyTypeActionCard v-if="safeReport.accident_party_type_card" :card="safeReport.accident_party_type_card" />
      <EasyFaultRatioCard :fault="safeReport.fault_explanation || {}" />
      <RelatedKniaStandardCard v-if="visibleRelatedFaultStandard" :standard="visibleRelatedFaultStandard" />

      <article v-if="safeReport.knia_fault_adjustment_card" class="card easy-card wide-card knia-adjustment-card">
        <p class="eyebrow">KNIA 기준과 가감요소</p>
        <h2>{{ text(safeReport.knia_fault_adjustment_card.title || "KNIA 기준 검토") }}</h2>
        <p class="easy-summary">
          KNIA 기준은 보험 실무 참고 기준입니다. 실제 판단은 경찰 조사, 보험사 협의, 분쟁심의, 법원 판단에 따라 달라질 수 있습니다.
        </p>
        <div class="chips">
          <span class="chip selected" v-if="safeReport.knia_fault_adjustment_card.base_fault">
            기본 A{{ safeReport.knia_fault_adjustment_card.base_fault.A }} : B{{ safeReport.knia_fault_adjustment_card.base_fault.B }}
          </span>
          <span class="chip selected" v-if="safeReport.knia_fault_adjustment_card.final_fault">
            현재 입력 기준 A{{ safeReport.knia_fault_adjustment_card.final_fault.A }} : B{{ safeReport.knia_fault_adjustment_card.final_fault.B }}
          </span>
          <span class="chip selected" v-if="safeReport.knia_fault_adjustment_card.user_fault">
            내 과실 {{ safeReport.knia_fault_adjustment_card.user_fault.my }}% / 상대 {{ safeReport.knia_fault_adjustment_card.user_fault.other }}%
          </span>
        </div>
        <p v-if="safeReport.knia_fault_adjustment_card.user_fault?.role_label" class="kv">
          {{ text(safeReport.knia_fault_adjustment_card.user_fault.role_label) }}
        </p>

        <div class="basis-grid">
          <section class="basis-card">
            <h3>적용한 가감요소</h3>
            <ul class="check-list" v-if="safeReport.knia_fault_adjustment_card.applied_adjustments?.length">
              <li v-for="item in safeReport.knia_fault_adjustment_card.applied_adjustments" :key="item.label">
                {{ text(item.label) }}
                <span v-if="item.applied_effect"> · A {{ signed(item.applied_effect?.A) }}, B {{ signed(item.applied_effect?.B) }}</span>
                <span v-if="item.matched_by?.length"> · 근거: {{ item.matched_by.map(text).join(", ") }}</span>
              </li>
            </ul>
            <p v-else class="kv">현재 입력만으로 바로 적용하는 가감요소는 확인되지 않았습니다.</p>
          </section>

          <section class="basis-card">
            <h3>아직 모르는 항목</h3>
            <ul class="check-list" v-if="safeReport.knia_fault_adjustment_card.unknown_adjustments?.length">
              <li v-for="item in safeReport.knia_fault_adjustment_card.unknown_adjustments" :key="item.label || item">
                {{ text(item.label || item.reason || item) }}
              </li>
            </ul>
            <p v-else class="kv">추가 확인이 필요한 가감요소가 따로 표시되지 않았습니다.</p>
          </section>
        </div>

        <details v-if="safeReport.knia_fault_adjustment_card.calculation_steps?.length" class="inline-details">
          <summary>계산 과정 보기</summary>
          <ul class="check-list">
            <li v-for="step in safeReport.knia_fault_adjustment_card.calculation_steps" :key="step">{{ text(step) }}</li>
          </ul>
        </details>
        <p v-if="safeReport.knia_fault_adjustment_card.notice" class="soft-warning">{{ text(safeReport.knia_fault_adjustment_card.notice) }}</p>
      </article>

      <MissingInfoCard
        v-if="hasMissingInfo"
        :missing="displayMissingInfo"
        :submitting="followupSubmitting"
        :error="followupError"
        @submit="(answers) => emit('submitFollowup', answers)"
      />

      <article v-if="safeReport.conditional_outcome_card" class="card easy-card wide-card conditional-outcome-card">
        <p class="eyebrow">조건별 결과</p>
        <h2>상황별로 달라질 수 있는 판단</h2>
        <p class="big-text">{{ text(safeReport.conditional_outcome_card.summary) }}</p>
        <div class="basis-grid">
          <div class="basis-card" v-for="item in safeReport.conditional_outcome_card.cases || []" :key="item.label">
            <h3>{{ text(item.label) }}</h3>
            <p class="accent-text">{{ text(item.likely_direction) }}</p>
            <p>{{ text(item.explanation) }}</p>
            <ul class="check-list">
              <li v-for="point in item.check_points || []" :key="point">{{ text(point) }}</li>
            </ul>
          </div>
        </div>
        <h3>먼저 확인할 자료</h3>
        <div class="chips">
          <span class="chip" v-for="item in safeReport.conditional_outcome_card.needed_evidence || []" :key="item">{{ text(item) }}</span>
        </div>
        <p class="soft-warning">{{ text(safeReport.conditional_outcome_card.notice) }}</p>
      </article>

      <ElderlyActionCard v-if="actionItems.length" :actions="actionItems" />

      <article v-if="insuranceScriptLines.length" class="card easy-card wide-card insurance-script-card">
        <p class="eyebrow">보험 대응 문장</p>
        <h2>보험사에 이렇게 말해 보세요</h2>
        <ul class="script-list">
          <li v-for="line in insuranceScriptLines" :key="line">{{ text(line) }}</li>
        </ul>
      </article>

      <article v-if="!isQuickSummary" class="card easy-card">
        <h2>{{ text(safeReport.insurance_explanation?.title || "보험 처리 안내") }}</h2>
        <p class="big-text">{{ text(safeReport.insurance_explanation?.simple_summary) }}</p>
        <h3>진행 순서</h3>
        <ul class="check-list"><li v-for="step in safeReport.insurance_explanation?.steps || []" :key="step">{{ text(step) }}</li></ul>
        <h3>챙겨두면 좋은 서류</h3>
        <div class="chips"><span class="chip" v-for="doc in safeReport.insurance_explanation?.documents || []" :key="doc">{{ text(doc) }}</span></div>
      </article>

      <article v-if="!isQuickSummary" class="card easy-card">
        <h2>{{ text(safeReport.legal_explanation?.title || "법률상 확인사항") }}</h2>
        <p class="big-text">{{ text(safeReport.legal_explanation?.simple_summary) }}</p>
        <div class="chips"><span class="chip selected">위험도 {{ text(safeReport.legal_explanation?.risk_label || "확인 필요") }}</span></div>
        <ul class="check-list"><li v-for="item in safeReport.legal_explanation?.checklist || []" :key="item">{{ text(item) }}</li></ul>
        <p class="soft-warning">{{ text(safeReport.legal_explanation?.caution) }}</p>
      </article>

      <ExpertGuidanceCard v-if="safeReport.expert_guidance_card" :card="safeReport.expert_guidance_card" />
      <VideoFactExplanationCard v-if="safeReport.video_fact_explanation_card" :card="safeReport.video_fact_explanation_card" />
      <EvidenceReliabilityCard v-if="!isQuickSummary && safeReport.evidence_reliability_card" :card="safeReport.evidence_reliability_card" />

      <article v-if="!isQuickSummary" class="card easy-card wide-card">
        <h2>법률 근거 쉽게 보기</h2>
        <p class="easy-summary">법 이름보다 이 사고와 어떤 관련이 있는지를 먼저 보시면 됩니다.</p>
        <div class="basis-grid"><EasyLegalBasisCard v-for="card in visibleBasisCards" :key="`${card.law_name}-${card.easy_title}`" :card="card" /></div>
        <p v-if="!basisCards.length" class="soft-warning">현재 표시할 수 있는 법률 근거가 부족합니다. 법률 KB 적재 상태나 외부 API 권한을 확인한 뒤 다시 분석해 주세요.</p>
        <button v-if="basisCards.length > 3" class="btn secondary" @click="showAllBasis = !showAllBasis">{{ showAllBasis ? "근거 줄이기" : `근거 ${basisCards.length - 3}개 더 보기` }}</button>
      </article>

      <RelatedVideoCard v-if="safeReport.related_video" :video="safeReport.related_video" />
      <RelatedVideoCard v-if="safeReport.related_knia_video_card" :video="safeReport.related_knia_video_card" />

      <article v-if="visibleKniaBasisCards.length" class="card easy-card wide-card">
        <h2>함께 참고할 수 있는 KNIA 기준</h2>
        <div class="basis-grid">
          <div class="basis-card" v-for="card in visibleKniaBasisCards" :key="`${card.chart_no}-${card.title}`">
            <p class="kv">기준번호 {{ text(card.chart_no) }}</p>
            <h3>{{ text(card.title) }}</h3>
            <div class="knia-paragraphs">
              <p v-for="paragraph in kniaParagraphs(card.easy_explanation)" :key="paragraph">{{ paragraph }}</p>
            </div>
            <details v-if="kniaParagraphs(card.why_similar).length" class="inline-details">
              <summary>이 기준을 함께 보는 이유</summary>
              <div class="knia-paragraphs">
                <p v-for="paragraph in kniaParagraphs(card.why_similar)" :key="paragraph">{{ paragraph }}</p>
              </div>
            </details>
            <a v-if="card.source_url" class="btn secondary" :href="card.source_url" target="_blank" rel="noopener noreferrer">원문 기준 보기</a>
            <p class="kv">{{ text(card.source_label) }}</p>
          </div>
        </div>
      </article>

      <details v-if="safeReport.agent_process_card || safeReport.analysis_change_card || safeReport.detail_sections" class="card diagnostic-panel advanced-diagnostics">
        <summary>고급 진단 보기</summary>
        <div class="advanced-diagnostics-body">
          <AnalysisChangeCard v-if="safeReport.analysis_change_card" :card="safeReport.analysis_change_card" />
          <AgentProcessCard v-if="safeReport.agent_process_card" :card="safeReport.agent_process_card" />
          <DetailToggleSection :details="safeReport.detail_sections || {}" />
        </div>
      </details>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import TopConclusionCard from "./TopConclusionCard.vue";
import AnalysisChangeCard from "./AnalysisChangeCard.vue";
import AgentProcessCard from "./AgentProcessCard.vue";
import ElderlyActionCard from "./ElderlyActionCard.vue";
import EvidenceReliabilityCard from "./EvidenceReliabilityCard.vue";
import EasyFaultRatioCard from "./EasyFaultRatioCard.vue";
import ExpertGuidanceCard from "./ExpertGuidanceCard.vue";
import EasyLegalBasisCard from "./EasyLegalBasisCard.vue";
import VideoFactExplanationCard from "./VideoFactExplanationCard.vue";
import MissingInfoCard from "./MissingInfoCard.vue";
import DetailToggleSection from "./DetailToggleSection.vue";
import RelatedKniaStandardCard from "../knia/RelatedKniaStandardCard.vue";
import RelatedVideoCard from "../knia/RelatedVideoCard.vue";
import AccidentPartyTypeActionCard from "../result/AccidentPartyTypeActionCard.vue";
import { formatKniaBody, removeTechnicalFields, sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ report: any; analysisMode?: string; followupSubmitting?: boolean; followupError?: string }>();
const emit = defineEmits<{ submitFollowup: [answers: Record<string, string>] }>();
const showAllBasis = ref(false);

const safeReport = computed<any>(() => removeTechnicalFields(props.report || {}));
const displayMode = computed(() => {
  const mode = String(
    props.analysisMode ||
    props.report?.display_mode ||
    props.report?.analysis_mode ||
    props.report?.analysis_mode_contract?.mode ||
    ""
  ).trim();

  if (
    mode === "expert" ||
    mode === "legal_precedent_focused" ||
    mode === "full_deep_research" ||
    mode === "deep_research" ||
    mode === "debug"
  ) {
    return "expert";
  }

  return "user_friendly";
});
const isExpertMode = computed(() => displayMode.value === "expert");
const isUserFriendlyMode = computed(() => displayMode.value === "user_friendly");
const isQuickSummary = computed(() => !isExpertMode.value);
const basisCards = computed<any[]>(() => safeReport.value?.legal_basis_cards || []);
const visibleBasisCards = computed(() => (showAllBasis.value ? basisCards.value : basisCards.value.slice(0, 3)));
const actionItems = computed(() => Array.isArray(safeReport.value?.top_actions) ? safeReport.value.top_actions : []);
const displayMissingInfo = computed(() => safeReport.value?.missing_info || {});
const partyText = computed(() => [
  safeReport.value?.summary_for_user?.accident_type_label,
  safeReport.value?.accident_party_type_card?.label,
  safeReport.value?.accident_party_type_card?.summary,
  safeReport.value?.knia_major_party_type,
  safeReport.value?.accident_party_type,
].map((value) => sanitizeDisplayText(value)).join(" "));
const visibleRelatedFaultStandard = computed(() => isAllowedKniaCard(safeReport.value?.related_fault_standard) ? safeReport.value.related_fault_standard : null);
const visibleKniaBasisCards = computed(() => {
  const cards = Array.isArray(safeReport.value?.knia_basis_cards) ? safeReport.value.knia_basis_cards : [];
  return cards.filter(isAllowedKniaCard);
});
const insuranceScriptLines = computed(() => {
  const card = safeReport.value?.insurance_script_card || safeReport.value?.insurance_explanation || {};
  const candidates = [
    ...(Array.isArray(card.sentences) ? card.sentences : []),
    ...(Array.isArray(card.talking_points) ? card.talking_points : []),
    ...(Array.isArray(card.say_to_insurer) ? card.say_to_insurer : []),
    ...(Array.isArray(card.key_messages) ? card.key_messages : []),
  ];
  if (candidates.length) return candidates.slice(0, 4);
  const summary = safeReport.value?.insurance_explanation?.simple_summary;
  return summary ? [summary] : [];
});
const hasMissingInfo = computed(() => {
  const missing = displayMissingInfo.value || {};
  return Boolean(
    (Array.isArray(missing.questions) && missing.questions.length) ||
    (Array.isArray(missing.items) && missing.items.length) ||
    (Array.isArray(missing.priority_items) && missing.priority_items.length)
  );
});

function textOrFallback(...values: any[]) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return sanitizeDisplayText(value);
  }
  return "";
}
const simpleSituationSummary = computed(() => textOrFallback(
  safeReport.value?.simple_report?.situation_summary,
  safeReport.value?.current_situation_summary,
  safeReport.value?.situation_summary,
  safeReport.value?.one_line_summary,
  safeReport.value?.summary,
  "입력한 사고 설명과 영상 자료를 바탕으로 사고 상황을 정리했습니다."
));
const simpleFaultRatio = computed<any>(() => {
  const simple = safeReport.value?.simple_report?.fault_ratio;
  if (simple && typeof simple === "object") return simple;

  const source = safeReport.value?.fault_ratio || safeReport.value?.faultRatio || safeReport.value?.fault_explanation || {};
  const userFault = source.user_fault || source.final_fault || {};
  const keyFactors = Array.isArray(source.key_factors)
    ? source.key_factors
    : Array.isArray(source.applied_adjustments)
      ? source.applied_adjustments.map((item: any) => item?.label || item?.reason).filter(Boolean)
      : [];

  return {
    ...source,
    my: source.my ?? source.my_percent ?? source.my_fault ?? userFault.my ?? null,
    other: source.other ?? source.other_percent ?? source.opponent_fault ?? userFault.other ?? null,
    basis: source.basis || source.summary || source.simple_summary || "",
    key_factors: keyFactors,
    reference_only: source.reference_only === true,
  };
});
const simpleKniaEvidence = computed<any>(() => (
  safeReport.value?.simple_report?.knia_video_evidence ||
  safeReport.value?.knia_match_summary ||
  safeReport.value?.knia_primary_match ||
  safeReport.value?.knia_reference ||
  null
));
const simpleVideoSummary = computed(() => textOrFallback(
  safeReport.value?.simple_report?.video_summary,
  safeReport.value?.video_summary,
  safeReport.value?.video_context_summary,
  safeReport.value?.video_observation_summary,
  ""
));

function text(value: unknown) { return sanitizeDisplayText(value); }
function kniaParagraphs(value: unknown) { return formatKniaBody(value); }

function isAllowedKniaCard(card: any) {
  if (!card) return false;
  const chartNo = sanitizeDisplayText(card.chart_no || card.chartNo || "");
  const title = sanitizeDisplayText(card.title || card.chart_title || "");
  const party = partyText.value;
  if (!chartNo) return true;
  if (party.includes("차대사람") || party.includes("car vs person")) return chartNo.startsWith("보");
  if (party.includes("차대자전거") || party.includes("bicycle")) return chartNo.startsWith("거");
  if (party.includes("차대차")) return chartNo.startsWith("차");
  if (party.includes("차대오토바이") || party.includes("motorcycle") || party.includes("이륜")) {
    return chartNo.startsWith("차") && /이륜|오토바이|자동이륜|motorcycle/i.test(`${title} ${JSON.stringify(card)}`);
  }
  return !chartNo.startsWith("보") && !chartNo.startsWith("거");
}

function signed(value: unknown) {
  const n = Number(value || 0);
  return n > 0 ? `+${n}` : String(n);
}
</script>
