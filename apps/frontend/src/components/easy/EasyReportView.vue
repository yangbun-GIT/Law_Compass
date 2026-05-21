<template>
  <section class="easy-report" v-if="safeReport">
    <TopConclusionCard :report="safeReport" />
    <AccidentPartyTypeActionCard v-if="safeReport.accident_party_type_card" :card="safeReport.accident_party_type_card" />
    <ElderlyActionCard :actions="safeReport.top_actions || []" />
    <EvidenceReliabilityCard v-if="safeReport.evidence_reliability_card" :card="safeReport.evidence_reliability_card" />
    <EasyFaultRatioCard :fault="safeReport.fault_explanation || {}" />
    <article class="card easy-card">
      <h2>{{ text(safeReport.insurance_explanation?.title || "보험 처리 안내") }}</h2>
      <p class="big-text">{{ text(safeReport.insurance_explanation?.simple_summary) }}</p>
      <h3>진행 순서</h3>
      <ul class="check-list"><li v-for="step in safeReport.insurance_explanation?.steps || []" :key="step">{{ text(step) }}</li></ul>
      <h3>챙겨두면 좋은 서류</h3>
      <div class="chips"><span class="chip" v-for="doc in safeReport.insurance_explanation?.documents || []" :key="doc">{{ text(doc) }}</span></div>
    </article>
    <article class="card easy-card">
      <h2>{{ text(safeReport.legal_explanation?.title || "법률상 확인할 점") }}</h2>
      <p class="big-text">{{ text(safeReport.legal_explanation?.simple_summary) }}</p>
      <div class="chips"><span class="chip selected">위험도 {{ text(safeReport.legal_explanation?.risk_label || "확인 필요") }}</span></div>
      <ul class="check-list"><li v-for="item in safeReport.legal_explanation?.checklist || []" :key="item">{{ text(item) }}</li></ul>
      <p class="soft-warning">{{ text(safeReport.legal_explanation?.caution) }}</p>
    </article>
    <article class="card easy-card wide-card">
      <h2>법률 근거 쉽게 보기</h2>
      <p class="easy-summary">법 이름보다 “이 사고와 어떤 관련이 있는지”를 먼저 보시면 됩니다.</p>
      <div class="basis-grid"><EasyLegalBasisCard v-for="card in visibleBasisCards" :key="`${card.law_name}-${card.easy_title}`" :card="card" /></div>
      <p v-if="!basisCards.length" class="soft-warning">현재 표시할 수 있는 법률 근거가 부족합니다. 법률 KB 적재 상태나 외부 API 권한을 확인한 뒤 다시 분석해 주세요.</p>
      <button v-if="basisCards.length > 3" class="btn secondary" @click="showAllBasis = !showAllBasis">{{ showAllBasis ? "근거 줄이기" : `근거 ${basisCards.length - 3}개 더 보기` }}</button>
    </article>
    <RelatedKniaStandardCard v-if="safeReport.related_fault_standard" :standard="safeReport.related_fault_standard" />
    <article v-if="safeReport.knia_fault_adjustment_card" class="card easy-card wide-card knia-adjustment-card">
      <h2>{{ text(safeReport.knia_fault_adjustment_card.title || "KNIA 원문 근거 및 가감요소 적용") }}</h2>
      <div class="chips">
        <span class="chip selected" v-if="safeReport.knia_fault_adjustment_card.base_fault">
          기본 A{{ safeReport.knia_fault_adjustment_card.base_fault.A }} : B{{ safeReport.knia_fault_adjustment_card.base_fault.B }}
        </span>
        <span class="chip selected" v-if="safeReport.knia_fault_adjustment_card.final_fault">
          참고 산정 A{{ safeReport.knia_fault_adjustment_card.final_fault.A }} : B{{ safeReport.knia_fault_adjustment_card.final_fault.B }}
        </span>
        <span class="chip selected" v-if="safeReport.knia_fault_adjustment_card.user_fault">
          사용자 기준 내 책임 {{ safeReport.knia_fault_adjustment_card.user_fault.my }}% / 상대 {{ safeReport.knia_fault_adjustment_card.user_fault.other }}%
        </span>
      </div>
      <p v-if="safeReport.knia_fault_adjustment_card.user_fault?.role_label" class="kv">
        {{ text(safeReport.knia_fault_adjustment_card.user_fault.role_label) }}
      </p>
      <h3>적용된 가감요소</h3>
      <ul class="check-list" v-if="safeReport.knia_fault_adjustment_card.applied_adjustments?.length">
        <li v-for="item in safeReport.knia_fault_adjustment_card.applied_adjustments" :key="item.label">
          {{ text(item.label) }}: A {{ signed(item.applied_effect?.A) }}, B {{ signed(item.applied_effect?.B) }}
          <span v-if="item.matched_by?.length"> · 근거: {{ item.matched_by.map(text).join(", ") }}</span>
        </li>
      </ul>
      <p v-else class="kv">입력 내용만으로 적용할 수 있는 KNIA 원문 가감요소가 확인되지 않았습니다.</p>
      <h3>계산 과정</h3>
      <ul class="check-list"><li v-for="step in safeReport.knia_fault_adjustment_card.calculation_steps || []" :key="step">{{ text(step) }}</li></ul>
      <p class="soft-warning">{{ text(safeReport.knia_fault_adjustment_card.notice) }}</p>
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
    <MissingInfoCard :missing="safeReport.missing_info || {}" />
    <DetailToggleSection :details="safeReport.detail_sections || {}" />
  </section>
</template>
<script setup lang="ts">
import { computed, ref } from "vue";
import TopConclusionCard from "./TopConclusionCard.vue";
import ElderlyActionCard from "./ElderlyActionCard.vue";
import EvidenceReliabilityCard from "./EvidenceReliabilityCard.vue";
import EasyFaultRatioCard from "./EasyFaultRatioCard.vue";
import EasyLegalBasisCard from "./EasyLegalBasisCard.vue";
import MissingInfoCard from "./MissingInfoCard.vue";
import DetailToggleSection from "./DetailToggleSection.vue";
import RelatedKniaStandardCard from "../knia/RelatedKniaStandardCard.vue";
import RelatedVideoCard from "../knia/RelatedVideoCard.vue";
import AccidentPartyTypeActionCard from "../result/AccidentPartyTypeActionCard.vue";
import { removeTechnicalFields, sanitizeDisplayText } from "../../utils/displaySanitizer";
const props = defineProps<{ report: any }>();
const showAllBasis = ref(false);
const safeReport = computed(() => removeTechnicalFields(props.report || {}));
const basisCards = computed(() => safeReport.value?.legal_basis_cards || []);
const visibleBasisCards = computed(() => (showAllBasis.value ? basisCards.value : basisCards.value.slice(0, 3)));
function text(value: unknown) { return sanitizeDisplayText(value); }
function signed(value: unknown) {
  const n = Number(value || 0);
  return n > 0 ? `+${n}` : String(n);
}
</script>
