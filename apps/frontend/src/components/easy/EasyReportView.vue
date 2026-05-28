<template>
  <section class="easy-report" v-if="safeReport">
    <TopConclusionCard :report="safeReport" />
    <AccidentPartyTypeActionCard v-if="safeReport.accident_party_type_card" :card="safeReport.accident_party_type_card" />
    <EasyFaultRatioCard :fault="safeReport.fault_explanation || {}" />
    <RelatedKniaStandardCard v-if="safeReport.related_fault_standard" :standard="safeReport.related_fault_standard" />

    <article v-if="safeReport.knia_fault_adjustment_card" class="card easy-card wide-card knia-adjustment-card">
      <p class="eyebrow">KNIA 기준과 가감요소</p>
      <h2>{{ text(safeReport.knia_fault_adjustment_card.title || "KNIA 기준 검토") }}</h2>
      <p class="easy-summary">
        KNIA 기준은 보험 실무상 참고 기준입니다. 실제 판단은 경찰 조사, 보험사 협의, 분쟁심의, 법원 판단에 따라 달라질 수 있습니다.
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
          <h3>적용된 가감요소</h3>
          <ul class="check-list" v-if="safeReport.knia_fault_adjustment_card.applied_adjustments?.length">
            <li v-for="item in safeReport.knia_fault_adjustment_card.applied_adjustments" :key="item.label">
              {{ text(item.label) }}
              <span v-if="item.applied_effect"> · A {{ signed(item.applied_effect?.A) }}, B {{ signed(item.applied_effect?.B) }}</span>
              <span v-if="item.matched_by?.length"> · 근거: {{ item.matched_by.map(text).join(", ") }}</span>
            </li>
          </ul>
          <p v-else class="kv">현재 답변만으로 바로 적용되는 가감요소는 확인되지 않았습니다.</p>
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
      <h3>먼저 확보할 자료</h3>
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
      <h2>{{ text(safeReport.legal_explanation?.title || "법률상 확인할 점") }}</h2>
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
      <p class="easy-summary">법 이름보다 “이 사고와 어떤 관련이 있는지”를 먼저 보시면 됩니다.</p>
      <div class="basis-grid"><EasyLegalBasisCard v-for="card in visibleBasisCards" :key="`${card.law_name}-${card.easy_title}`" :card="card" /></div>
      <p v-if="!basisCards.length" class="soft-warning">현재 표시할 수 있는 법률 근거가 부족합니다. 법률 KB 적재 상태나 외부 API 권한을 확인한 뒤 다시 분석해 주세요.</p>
      <button v-if="basisCards.length > 3" class="btn secondary" @click="showAllBasis = !showAllBasis">{{ showAllBasis ? "근거 줄이기" : `근거 ${basisCards.length - 3}개 더 보기` }}</button>
    </article>

    <RelatedVideoCard v-if="safeReport.related_video" :video="safeReport.related_video" />
    <RelatedVideoCard v-if="safeReport.related_knia_video_card" :video="safeReport.related_knia_video_card" />

    <article v-if="safeReport.knia_basis_cards?.length" class="card easy-card wide-card">
      <h2>함께 참고할 수 있는 KNIA 기준</h2>
      <div class="basis-grid">
        <div class="basis-card" v-for="card in safeReport.knia_basis_cards" :key="`${card.chart_no}-${card.title}`">
          <p class="kv">기준번호 {{ text(card.chart_no) }}</p>
          <h3>{{ text(card.title) }}</h3>
          <p>{{ text(card.easy_explanation) }}</p>
          <p class="soft-warning">{{ text(card.why_similar) }}</p>
          <a v-if="card.source_url" class="btn secondary" :href="card.source_url" target="_blank" rel="noopener noreferrer">원문 기준 보기</a>
          <p class="kv">{{ text(card.source_label) }}</p>
        </div>
      </div>
    </article>

    <details v-if="!isQuickSummary && (safeReport.agent_process_card || safeReport.analysis_change_card || safeReport.detail_sections)" class="card diagnostic-panel advanced-diagnostics">
      <summary>고급 진단 보기</summary>
      <div class="advanced-diagnostics-body">
        <AnalysisChangeCard v-if="safeReport.analysis_change_card" :card="safeReport.analysis_change_card" />
        <AgentProcessCard v-if="safeReport.agent_process_card" :card="safeReport.agent_process_card" />
        <DetailToggleSection :details="safeReport.detail_sections || {}" />
      </div>
    </details>
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
import { removeTechnicalFields, sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ report: any; followupSubmitting?: boolean; followupError?: string }>();
const emit = defineEmits<{ submitFollowup: [answers: Record<string, string>] }>();
const showAllBasis = ref(false);

const safeReport = computed(() => removeTechnicalFields(props.report || {}));
const isQuickSummary = computed(() => props.report?.analysis_mode_contract?.mode === "quick_summary");
const basisCards = computed(() => safeReport.value?.legal_basis_cards || []);
const visibleBasisCards = computed(() => (showAllBasis.value ? basisCards.value : basisCards.value.slice(0, 3)));
const actionItems = computed(() => Array.isArray(safeReport.value?.top_actions) ? safeReport.value.top_actions : []);
const displayMissingInfo = computed(() => safeReport.value?.missing_info || {});
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

function text(value: unknown) { return sanitizeDisplayText(value); }

function signed(value: unknown) {
  const n = Number(value || 0);
  return n > 0 ? `+${n}` : String(n);
}
</script>
