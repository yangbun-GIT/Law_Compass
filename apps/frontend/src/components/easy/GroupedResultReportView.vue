<template>
  <section v-if="safeReport" class="easy-report grouped-result-report">
    <TopConclusionCard :report="safeReport" />

    <section class="result-toggle-list" aria-label="상세 분석 묶음">
      <details
        v-if="hasAccidentInfo"
        class="card easy-card grouped-toggle"
        @toggle="setToggle('accident', $event)"
      >
        <summary class="grouped-toggle-summary">
          <span>사고 정보</span>
          <small>사고 상황, 대분류, 확인된 사실</small>
        </summary>
        <div v-if="openSections.accident" class="grouped-toggle-body">
          <section class="basis-card">
            <p class="eyebrow">사고 개요</p>
            <h3>{{ simpleSituationTitle }}</h3>
            <p v-if="simpleSituationDetail">{{ simpleSituationDetail }}</p>
            <div v-if="videoSceneFacts.length" class="chips">
              <span v-for="fact in videoSceneFacts" :key="`${fact.label}-${fact.value}`" class="chip">
                {{ text(fact.label) }}: {{ text(fact.value) }}
              </span>
            </div>
            <div v-if="videoSceneQuestions.length" class="chips compact">
              <span class="chip selected">추가 확인 필요</span>
              <span v-for="question in videoSceneQuestions" :key="String(question.field || question.label)" class="chip">
                {{ text(question.label || question.field) }}
              </span>
            </div>
          </section>

          <AccidentPartyTypeActionCard
            v-if="safeReport.accident_party_type_card"
            :card="safeReport.accident_party_type_card"
          />

          <section v-if="finalityCard" class="basis-grid compact-grid">
            <article class="basis-card">
              <p class="eyebrow">판단 상태</p>
              <h3>{{ text(finalityCard.status_label || "참고용") }}</h3>
              <p>{{ text(finalityCard.summary) }}</p>
              <span class="chip selected">{{ text(finalityCard.fault_status_label || "참고 범위") }}</span>
            </article>
            <article class="basis-card">
              <p class="eyebrow">확인된 사실</p>
              <ul v-if="finalityConfirmedFacts.length" class="check-list">
                <li v-for="item in finalityConfirmedFacts" :key="item">{{ item }}</li>
              </ul>
              <p v-else class="kv">현재 입력에서 바로 확정한 핵심 사실은 제한적입니다.</p>
            </article>
            <article class="basis-card">
              <p class="eyebrow">더 확인할 사실</p>
              <ul v-if="finalityMissingFacts.length" class="check-list">
                <li v-for="item in finalityMissingFacts" :key="item">{{ item }}</li>
              </ul>
              <p v-else class="kv">추가로 우선 확인할 사실은 따로 표시되지 않았습니다.</p>
            </article>
          </section>
        </div>
      </details>

      <details
        v-if="hasFaultInsuranceInfo"
        class="card easy-card grouped-toggle"
        @toggle="setToggle('faultInsurance', $event)"
      >
        <summary class="grouped-toggle-summary">
          <span>과실·보험</span>
          <small>예상 과실, 보험 대응, 지금 할 일</small>
        </summary>
        <div v-if="openSections.faultInsurance" class="grouped-toggle-body">
          <section class="basis-card">
            <p class="eyebrow">현재 입력 기준 예상</p>
            <h3>예상 과실비율</h3>
            <KniaFaultRatioBar
              :a="simpleFaultRatio.my ?? simpleFaultRatio.my_percent ?? simpleFaultRatio.my_fault"
              :b="simpleFaultRatio.other ?? simpleFaultRatio.other_percent ?? simpleFaultRatio.opponent_fault"
              left-label="내 과실"
              right-label="상대 과실"
              variant="user"
            />
            <p>
              {{ text(simpleFaultRatio.basis || simpleFaultRatio.summary || safeReport?.fault_ratio_summary || "입력한 사고 사실과 KNIA 기준을 함께 검토했습니다.") }}
            </p>
            <ul v-if="simpleFaultRatio.key_factors?.length" class="check-list">
              <li v-for="factor in simpleFaultRatio.key_factors.slice(0, 4)" :key="String(factor)">
                {{ text(factor) }}
              </li>
            </ul>
          </section>

          <EasyFaultRatioCard v-if="safeReport.fault_explanation" :fault="safeReport.fault_explanation" />

          <article v-if="insuranceScriptLines.length" class="basis-card">
            <p class="eyebrow">보험 대응 문장</p>
            <h3>보험사에 이렇게 말해 보세요</h3>
            <ul class="script-list">
              <li v-for="line in insuranceScriptLines" :key="line">{{ text(line) }}</li>
            </ul>
          </article>

          <article v-if="safeReport.insurance_explanation" class="basis-card">
            <p class="eyebrow">보험 처리 안내</p>
            <h3>{{ text(safeReport.insurance_explanation?.title || "보험 처리 안내") }}</h3>
            <p>{{ text(safeReport.insurance_explanation?.simple_summary) }}</p>
            <h4>진행 순서</h4>
            <ul class="check-list">
              <li v-for="step in safeReport.insurance_explanation?.steps || []" :key="step">{{ text(step) }}</li>
            </ul>
            <h4>챙겨두면 좋은 서류</h4>
            <div class="chips">
              <span class="chip" v-for="doc in safeReport.insurance_explanation?.documents || []" :key="doc">{{ text(doc) }}</span>
            </div>
          </article>

          <ElderlyActionCard v-if="actionItems.length" :actions="actionItems" />
        </div>
      </details>

      <details
        v-if="hasKniaInfo"
        class="card easy-card grouped-toggle"
        @toggle="setToggle('knia', $event)"
      >
        <summary class="grouped-toggle-summary">
          <span>KNIA 기준·가감요소</span>
          <small>가까운 기준, 기본 과실, 수정요소</small>
        </summary>
        <div v-if="openSections.knia" class="grouped-toggle-body">
          <section v-if="simpleKniaEvidence" class="basis-card">
            <p class="eyebrow">가장 가까운 KNIA 기준</p>
            <h3>
              {{ simpleKniaEvidence.chart_no || simpleKniaEvidence.subchart_no || "KNIA 기준 확인 중" }}
              <span v-if="simpleKniaEvidence.title"> · {{ text(simpleKniaEvidence.title) }}</span>
            </h3>
            <div v-if="simpleKniaPartyLabel" class="chips">
              <span class="chip selected">대분류: {{ simpleKniaPartyLabel }}</span>
            </div>
            <p v-if="simpleKniaEvidence.menu_path?.length">
              {{ simpleKniaEvidence.menu_path.map(text).join(" > ") }}
            </p>
            <p v-if="simpleKniaEvidence.match_reason || simpleKniaEvidence.why_matched">
              {{ text(simpleKniaEvidence.match_reason || simpleKniaEvidence.why_matched) }}
            </p>
            <div v-if="faultText(simpleKniaEvidence.base_fault) || faultText(simpleKniaEvidence.final_fault) || faultText(simpleKniaEvidence.fault_range)" class="simple-fault-lines">
              <p v-if="faultText(simpleKniaEvidence.base_fault)">기준 과실 {{ faultText(simpleKniaEvidence.base_fault) }}</p>
              <p v-if="faultText(simpleKniaEvidence.final_fault)">수정 과실 {{ faultText(simpleKniaEvidence.final_fault) }}</p>
              <p v-if="faultText(simpleKniaEvidence.fault_range)">참고 범위 {{ faultText(simpleKniaEvidence.fault_range) }}</p>
            </div>
            <a
              v-if="safeKniaButtonUrl(simpleKniaEvidence)"
              class="btn secondary"
              :href="safeKniaButtonUrl(simpleKniaEvidence)"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ simpleKniaEvidence.video_url ? "KNIA 관련 영상 보기" : "KNIA 원문 기준 보기" }}
            </a>
          </section>

          <RelatedKniaStandardCard v-if="visibleRelatedFaultStandard" :standard="visibleRelatedFaultStandard" />

          <KniaDetailEvidenceCard
            v-if="simpleKniaChartNo"
            :chart-no="simpleKniaChartNo"
            :chart-type="simpleKniaChartType"
            :fallback-standard="simpleKniaEvidence"
          />

          <article v-if="safeReport.knia_fault_adjustment_card" class="basis-card knia-adjustment-card">
            <p class="eyebrow">가감요소</p>
            <h3>{{ text(safeReport.knia_fault_adjustment_card.title || "KNIA 기준 검토") }}</h3>
            <p>
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
            <div class="basis-grid compact-grid">
              <section class="basis-card">
                <h4>적용한 가감요소</h4>
                <ul class="check-list" v-if="safeReport.knia_fault_adjustment_card.applied_adjustments?.length">
                  <li v-for="item in safeReport.knia_fault_adjustment_card.applied_adjustments" :key="item.label">
                    {{ text(item.label) }}
                    <span v-if="item.applied_effect"> · A {{ signed(item.applied_effect?.A) }}, B {{ signed(item.applied_effect?.B) }}</span>
                  </li>
                </ul>
                <p v-else class="kv">현재 입력만으로 바로 적용하는 가감요소는 확인되지 않았습니다.</p>
              </section>
              <section class="basis-card">
                <h4>아직 모르는 항목</h4>
                <ul class="check-list" v-if="safeReport.knia_fault_adjustment_card.unknown_adjustments?.length">
                  <li v-for="item in safeReport.knia_fault_adjustment_card.unknown_adjustments" :key="item.label || item">
                    {{ text(item.label || item.reason || item) }}
                  </li>
                </ul>
                <p v-else class="kv">추가 확인이 필요한 가감요소가 따로 표시되지 않았습니다.</p>
              </section>
            </div>
          </article>

          <section v-if="userAdjustmentRows.length" class="user-adjustment-panel">
            <div class="user-adjustment-head">
              <div>
                <p class="eyebrow">직접 조정</p>
                <h3>해당되는 조건을 선택해 참고 과실을 확인하세요</h3>
              </div>
              <span class="chip selected">{{ selectedAdjustmentCount }}개 적용</span>
            </div>
            <div v-if="manualFault" class="user-adjustment-result">
              <span>조정 후 참고 과실</span>
              <KniaFaultRatioBar
                :a="manualFault.A"
                :b="manualFault.B"
                left-label="A"
                right-label="B"
                :caption="manualFaultText"
                variant="compact"
              />
            </div>
            <label
              v-for="item in userAdjustmentRows"
              :key="item.key"
              class="user-adjustment-row"
              :class="{ 'is-selected': isAdjustmentSelected(item) }"
            >
              <input
                type="checkbox"
                :checked="isAdjustmentSelected(item)"
                @change="toggleUserAdjustment(item)"
              />
              <span class="user-adjustment-main">
                <strong>{{ text(item.label) }}</strong>
                <small>{{ text(item.reason || item.source_label || "사용자 확인에 따라 적용 여부가 달라지는 KNIA 가감기준입니다.") }}</small>
              </span>
              <span v-if="adjustmentEffectText(item)" class="user-adjustment-effect">{{ adjustmentEffectText(item) }}</span>
              <span class="selection-status" :class="{ 'is-on': isAdjustmentSelected(item) }">
                {{ isAdjustmentSelected(item) ? "적용" : "미적용" }}
              </span>
            </label>
          </section>

          <article v-if="visibleKniaBasisCards.length" class="basis-card">
            <p class="eyebrow">함께 참고할 수 있는 KNIA 기준</p>
            <div class="basis-grid">
              <div class="basis-card" v-for="card in visibleKniaBasisCards" :key="`${card.chart_no}-${card.title}`">
                <p class="kv">기준번호 {{ text(card.chart_no) }}</p>
                <h4>{{ text(card.title) }}</h4>
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
              </div>
            </div>
          </article>

          <RelatedVideoCard v-if="simpleKniaLinkCard" :video="simpleKniaLinkCard" />
        </div>
      </details>

      <details
        v-if="hasLegalInfo"
        class="card easy-card grouped-toggle"
        @toggle="setToggle('legal', $event)"
      >
        <summary class="grouped-toggle-summary">
          <span>법률 근거</span>
          <small>관련 법규, 판례·분쟁 참고, 법적 유의점</small>
        </summary>
        <div v-if="openSections.legal" class="grouped-toggle-body">
          <article v-if="safeReport.legal_explanation" class="basis-card">
            <p class="eyebrow">법률상 확인사항</p>
            <h3>{{ text(safeReport.legal_explanation?.title || "법률상 확인사항") }}</h3>
            <p>{{ text(safeReport.legal_explanation?.simple_summary) }}</p>
            <div class="chips">
              <span class="chip selected">위험도 {{ text(safeReport.legal_explanation?.risk_label || "확인 필요") }}</span>
            </div>
            <ul class="check-list">
              <li v-for="item in safeReport.legal_explanation?.checklist || []" :key="item">{{ text(item) }}</li>
            </ul>
            <p v-if="safeReport.legal_explanation?.caution" class="soft-warning">{{ text(safeReport.legal_explanation.caution) }}</p>
          </article>

          <ExpertGuidanceCard v-if="safeReport.expert_guidance_card" :card="safeReport.expert_guidance_card" />

          <article v-if="basisCards.length" class="basis-card">
            <p class="eyebrow">법률 근거 쉽게 보기</p>
            <h3>이번 사고와 함께 검토할 근거</h3>
            <div class="basis-grid">
              <EasyLegalBasisCard
                v-for="card in visibleBasisCards"
                :key="`${card.law_name}-${card.easy_title}`"
                :card="card"
              />
            </div>
            <button v-if="basisCards.length > 3" class="btn secondary" @click="showAllBasis = !showAllBasis">
              {{ showAllBasis ? "근거 줄이기" : `근거 ${basisCards.length - 3}개 더 보기` }}
            </button>
          </article>
        </div>
      </details>

      <details
        v-if="hasEvidenceInfo"
        class="card easy-card grouped-toggle"
        @toggle="setToggle('evidence', $event)"
      >
        <summary class="grouped-toggle-summary">
          <span>영상·증거</span>
          <small>영상 관찰값, 프레임 근거, 근거 신뢰도</small>
        </summary>
        <div v-if="openSections.evidence" class="grouped-toggle-body">
          <section v-if="simpleVideoSummary" class="basis-card">
            <p class="eyebrow">영상에서 확인한 점</p>
            <h3>영상 요약</h3>
            <p>{{ simpleVideoSummary }}</p>
          </section>
          <VideoFactExplanationCard v-if="safeReport.video_fact_explanation_card" :card="safeReport.video_fact_explanation_card" />
          <FrameEvidenceCard v-if="frameEvidenceCards.length" :cards="frameEvidenceCards" />
          <EvidenceReliabilityCard v-if="safeReport.evidence_reliability_card" :card="safeReport.evidence_reliability_card" />
          <RelatedVideoCard v-if="safeReport.related_video" :video="safeReport.related_video" />
          <RelatedVideoCard v-if="safeReport.related_knia_video_card" :video="safeReport.related_knia_video_card" />
        </div>
      </details>

      <details
        v-if="hasFollowupInfo"
        class="card easy-card grouped-toggle"
        @toggle="setToggle('followup', $event)"
      >
        <summary class="grouped-toggle-summary">
          <span>추가 확인</span>
          <small>질문 답변, 조건별 결과, 보완 자료</small>
        </summary>
        <div v-if="openSections.followup" class="grouped-toggle-body">
          <MissingInfoCard
            v-if="hasMissingInfo"
            :missing="displayMissingInfo"
            :submitting="followupSubmitting"
            :error="followupError"
            @submit="(answers) => emit('submitFollowup', answers)"
          />

          <article v-if="safeReport.conditional_outcome_card" class="basis-card">
            <p class="eyebrow">조건별 결과</p>
            <h3>상황별로 달라질 수 있는 판단</h3>
            <p>{{ text(safeReport.conditional_outcome_card.summary) }}</p>
            <div class="basis-grid">
              <div class="basis-card" v-for="item in safeReport.conditional_outcome_card.cases || []" :key="item.label">
                <h4>{{ text(item.label) }}</h4>
                <p class="accent-text">{{ text(item.likely_direction) }}</p>
                <p>{{ text(item.explanation) }}</p>
                <ul class="check-list">
                  <li v-for="point in item.check_points || []" :key="point">{{ text(point) }}</li>
                </ul>
              </div>
            </div>
            <h4>먼저 확인할 자료</h4>
            <div class="chips">
              <span class="chip" v-for="item in safeReport.conditional_outcome_card.needed_evidence || []" :key="item">{{ text(item) }}</span>
            </div>
            <p v-if="safeReport.conditional_outcome_card.notice" class="soft-warning">{{ text(safeReport.conditional_outcome_card.notice) }}</p>
          </article>
        </div>
      </details>

      <details
        v-if="hasAdvancedInfo"
        class="card easy-card grouped-toggle diagnostic-panel advanced-diagnostics"
        @toggle="setToggle('advanced', $event)"
      >
        <summary class="grouped-toggle-summary">
          <span>고급 진단</span>
          <small>분석 단계와 변경 이력</small>
        </summary>
        <div v-if="openSections.advanced" class="grouped-toggle-body advanced-diagnostics-body">
          <AnalysisChangeCard v-if="safeReport.analysis_change_card" :card="safeReport.analysis_change_card" />
          <AgentProcessCard v-if="safeReport.agent_process_card" :card="safeReport.agent_process_card" />
          <DetailToggleSection v-if="safeReport.detail_sections" :details="safeReport.detail_sections || {}" />
        </div>
      </details>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import TopConclusionCard from "./TopConclusionCard.vue";
import AnalysisChangeCard from "./AnalysisChangeCard.vue";
import AgentProcessCard from "./AgentProcessCard.vue";
import ElderlyActionCard from "./ElderlyActionCard.vue";
import EvidenceReliabilityCard from "./EvidenceReliabilityCard.vue";
import EasyFaultRatioCard from "./EasyFaultRatioCard.vue";
import ExpertGuidanceCard from "./ExpertGuidanceCard.vue";
import EasyLegalBasisCard from "./EasyLegalBasisCard.vue";
import FrameEvidenceCard from "./FrameEvidenceCard.vue";
import VideoFactExplanationCard from "./VideoFactExplanationCard.vue";
import MissingInfoCard from "./MissingInfoCard.vue";
import DetailToggleSection from "./DetailToggleSection.vue";
import RelatedKniaStandardCard from "../knia/RelatedKniaStandardCard.vue";
import RelatedVideoCard from "../knia/RelatedVideoCard.vue";
import KniaFaultRatioBar from "../knia/KniaFaultRatioBar.vue";
import KniaDetailEvidenceCard from "../knia/KniaDetailEvidenceCard.vue";
import AccidentPartyTypeActionCard from "../result/AccidentPartyTypeActionCard.vue";
import { formatKniaBody, removeTechnicalFields, sanitizeDisplayText, sanitizeOptionalDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ report: any; followupSubmitting?: boolean; followupError?: string }>();
const emit = defineEmits<{ submitFollowup: [answers: Record<string, string>] }>();

const showAllBasis = ref(false);
const userAdjustmentOverrides = ref<Record<string, boolean>>({});
const openSections = reactive<Record<string, boolean>>({
  accident: false,
  faultInsurance: false,
  knia: false,
  legal: false,
  evidence: false,
  followup: false,
  advanced: false,
});

const safeReport = computed<any>(() => removeTechnicalFields(props.report || {}));
const basisCards = computed<any[]>(() => safeReport.value?.legal_basis_cards || []);
const visibleBasisCards = computed(() => (showAllBasis.value ? basisCards.value : basisCards.value.slice(0, 3)));
const actionItems = computed(() => Array.isArray(safeReport.value?.top_actions) ? safeReport.value.top_actions : []);
const frameEvidenceCards = computed(() => collectFrameEvidenceCards(safeReport.value));
const displayMissingInfo = computed(() => safeReport.value?.missing_info || {});
const finalityCard = computed(() => safeReport.value?.finality_display_card || safeReport.value?.simple_report?.finality || null);
const finalityConfirmedFacts = computed(() => userVisibleFactList(finalityCard.value?.confirmed_facts, 6));
const finalityMissingFacts = computed(() => userVisibleFactList(finalityCard.value?.missing_facts, 6));
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

const simpleSituationTitle = computed(() => textOrFallback(
  safeReport.value?.video_scene_summary?.title,
  safeReport.value?.structured_facts?.video_scene_summary?.title,
  safeReport.value?.simple_report?.situation_title,
  safeReport.value?.situation_title,
  safeReport.value?.accident_title,
  extractSituationTitle(safeReport.value?.simple_report?.situation_summary),
  extractSituationTitle(safeReport.value?.summary),
  "영상에서 확인된 사고 개요",
  "입력한 사고 상황"
));
const simpleSituationSummary = computed(() => textOrFallback(
  safeReport.value?.video_scene_summary?.summary_text,
  safeReport.value?.structured_facts?.video_scene_summary?.summary_text,
  safeReport.value?.simple_report?.situation_summary,
  safeReport.value?.current_situation_summary,
  safeReport.value?.situation_summary,
  safeReport.value?.one_line_summary,
  safeReport.value?.summary,
  "입력한 영상과 답변을 바탕으로 사고 상황을 정리했습니다.",
  "입력한 사고 설명과 영상 자료를 바탕으로 사고 상황을 정리했습니다."
));
const simpleSituationDetail = computed(() => {
  const detail = sanitizeDisplayText(simpleSituationSummary.value);
  const title = sanitizeDisplayText(simpleSituationTitle.value);
  if (!detail || detail === title || detail === `${title} 상황입니다.`) return "";
  return detail;
});
const videoSceneSummary = computed<any>(() =>
  safeReport.value?.video_scene_summary ||
  safeReport.value?.structured_facts?.video_scene_summary ||
  safeReport.value?.simple_report?.video_scene_summary ||
  {}
);
const videoSceneFacts = computed<any[]>(() => {
  const confirmed = Array.isArray(videoSceneSummary.value?.confirmed_visual_facts)
    ? videoSceneSummary.value.confirmed_visual_facts
    : [];
  const likely = Array.isArray(videoSceneSummary.value?.likely_visual_context)
    ? videoSceneSummary.value.likely_visual_context
    : [];
  return [...confirmed, ...likely]
    .filter((item: any) => item && (item.label || item.field) && item.value !== undefined)
    .slice(0, 5);
});
const videoSceneQuestions = computed<any[]>(() => {
  const questions = Array.isArray(videoSceneSummary.value?.needs_user_confirmation)
    ? videoSceneSummary.value.needs_user_confirmation
    : [];
  return questions.filter((item: any) => item && (item.label || item.field)).slice(0, 4);
});
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
const userAdjustmentRows = computed(() => {
  const card = safeReport.value?.knia_fault_adjustment_card || {};
  const groups = [
    ...(Array.isArray(card.applied_adjustments) ? card.applied_adjustments.map((item: any) => ({ ...item, initialSelected: true })) : []),
    ...(Array.isArray(card.unknown_adjustments) ? card.unknown_adjustments.map((item: any) => ({ ...item, initialSelected: false })) : []),
    ...(Array.isArray(safeReport.value?.knia_unknown_adjustment_card?.items) ? safeReport.value.knia_unknown_adjustment_card.items.map((item: any) => ({ ...item, initialSelected: false })) : []),
    ...(Array.isArray(safeReport.value?.knia_not_applied_adjustment_card?.items) ? safeReport.value.knia_not_applied_adjustment_card.items.map((item: any) => ({ ...item, initialSelected: false })) : []),
  ];
  const seen = new Set<string>();
  return groups
    .map((item: any) => {
      const label = sanitizeDisplayText(item.label || item.title || item.reason || "");
      const key = sanitizeDisplayText(item.factor_id || item.id || label);
      return { ...item, key, label, initialSelected: item.initialSelected === true };
    })
    .filter((item: any) => item.key && item.label && !isAmbiguousAdjustmentLabel(item.label))
    .filter((item: any) => {
      const normalized = item.key.toLowerCase();
      if (seen.has(normalized)) return false;
      seen.add(normalized);
      return true;
    })
    .slice(0, 8);
});
const selectedAdjustmentCount = computed(() => userAdjustmentRows.value.filter(isAdjustmentSelected).length);
const manualFault = computed(() => {
  const base = safeReport.value?.knia_fault_adjustment_card?.base_fault || simpleKniaEvidence.value?.base_fault;
  const pair = normalizeFaultPair(base);
  if (!pair) return null;
  let a = pair.A;
  let b = pair.B;
  for (const item of userAdjustmentRows.value) {
    if (!isAdjustmentSelected(item)) continue;
    const effect = adjustmentEffect(item);
    a += effect.A;
    b += effect.B;
  }
  return { A: clampPercent(a), B: clampPercent(b) };
});
const manualFaultText = computed(() => manualFault.value ? `A ${manualFault.value.A}% / B ${manualFault.value.B}%` : "");
const simpleKniaEvidence = computed<any>(() => {
  const candidates = [
    safeReport.value?.related_knia_video_card,
    safeReport.value?.related_video,
    safeReport.value?.simple_report?.knia_and_video?.primary,
    safeReport.value?.simple_report?.knia_video_evidence,
    safeReport.value?.knia_match_summary,
    safeReport.value?.knia_primary_match,
    Array.isArray(safeReport.value?.knia_basis_cards) ? safeReport.value.knia_basis_cards[0] : null,
    Array.isArray(safeReport.value?.knia_matches) ? safeReport.value.knia_matches[0] : null,
    safeReport.value?.related_fault_standard,
    safeReport.value?.knia_reference,
  ];

  return candidates.find((item) => item && (item.has_knia_candidate || item.chart_no || item.subchart_no || item.title || item.chart_title)) || null;
});
const simpleKniaLinkCard = computed<any>(() => {
  const card = safeReport.value?.related_knia_video_card || safeReport.value?.related_video || safeReport.value?.simple_report?.knia_and_video?.primary;
  return card && (card.has_knia_candidate || card.button_url || card.source_url || card.video_url) ? card : null;
});
const simpleKniaPartyLabel = computed(() => resolveAccidentPartyLabel({
  accident_party_label: simpleKniaEvidence.value?.accident_party_label || simpleKniaEvidence.value?.major_party_label,
  accident_party_type: simpleKniaEvidence.value?.major_party_type || simpleKniaEvidence.value?.accident_party_type || safeReport.value?.accident_party_type,
  chart_no: simpleKniaEvidence.value?.chart_no || simpleKniaEvidence.value?.subchart_no,
}));
const simpleKniaChartNo = computed(() => sanitizeDisplayText(simpleKniaEvidence.value?.chart_no || simpleKniaEvidence.value?.subchart_no, ""));
const simpleKniaChartType = computed(() => sanitizeDisplayText(simpleKniaEvidence.value?.chart_type || "1", "1"));
const simpleVideoSummary = computed(() => textOrFallback(
  safeReport.value?.simple_report?.video_summary,
  safeReport.value?.video_summary,
  safeReport.value?.video_context_summary,
  safeReport.value?.video_observation_summary,
  ""
));

const hasAccidentInfo = computed(() => Boolean(
  simpleSituationTitle.value ||
  simpleSituationDetail.value ||
  videoSceneFacts.value.length ||
  videoSceneQuestions.value.length ||
  finalityCard.value ||
  safeReport.value?.accident_party_type_card
));
const hasFaultInsuranceInfo = computed(() => Boolean(
  simpleFaultRatio.value ||
  safeReport.value?.fault_explanation ||
  safeReport.value?.insurance_explanation ||
  insuranceScriptLines.value.length ||
  actionItems.value.length
));
const hasKniaInfo = computed(() => Boolean(
  simpleKniaEvidence.value ||
  visibleRelatedFaultStandard.value ||
  simpleKniaChartNo.value ||
  safeReport.value?.knia_fault_adjustment_card ||
  userAdjustmentRows.value.length ||
  visibleKniaBasisCards.value.length ||
  simpleKniaLinkCard.value
));
const hasLegalInfo = computed(() => Boolean(
  safeReport.value?.legal_explanation ||
  safeReport.value?.expert_guidance_card ||
  basisCards.value.length
));
const hasEvidenceInfo = computed(() => Boolean(
  simpleVideoSummary.value ||
  safeReport.value?.video_fact_explanation_card ||
  frameEvidenceCards.value.length ||
  safeReport.value?.evidence_reliability_card ||
  safeReport.value?.related_video ||
  safeReport.value?.related_knia_video_card
));
const hasFollowupInfo = computed(() => Boolean(
  hasMissingInfo.value ||
  safeReport.value?.conditional_outcome_card
));
const hasAdvancedInfo = computed(() => Boolean(
  safeReport.value?.analysis_change_card ||
  safeReport.value?.agent_process_card ||
  safeReport.value?.detail_sections
));

function setToggle(section: string, event: Event) {
  openSections[section] = (event.currentTarget as HTMLDetailsElement).open;
}

function textOrFallback(...values: any[]) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return sanitizeDisplayText(value);
  }
  return "";
}

function userVisibleFactList(value: any, limit = 6) {
  const source = Array.isArray(value) ? value : [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of source) {
    const record = item && typeof item === "object" ? item as Record<string, unknown> : null;
    const candidate = record
      ? (record.label || record.title || record.question || record.field || record.fact_key || record.name)
      : item;
    const itemText = sanitizeOptionalDisplayText(candidate);
    if (!itemText || itemText === "확인이 필요합니다") continue;
    const normalized = itemText.replace(/\s+/g, " ").trim().toLowerCase();
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    out.push(itemText);
    if (out.length >= limit) break;
  }
  return out;
}

function collectFrameEvidenceCards(report: any) {
  const sources = [
    report?.frame_interpretation_cards,
    report?.video_fact_explanation_card?.frame_interpretation_cards,
    report?.simple_report?.frame_interpretation_cards,
  ];
  const seen = new Set<string>();
  return sources
    .flatMap((source) => Array.isArray(source) ? source : [])
    .filter((card: any) => card?.display_allowed === true)
    .filter((card: any) => {
      const key = [
        card?.image_ref?.case_id,
        card?.image_ref?.upload_id,
        card?.frame_ref || card?.image_ref?.frame_ref,
        card?.time_sec,
      ].join(":");
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 6);
}

function text(value: unknown) { return sanitizeDisplayText(value); }
function kniaParagraphs(value: unknown) { return formatKniaBody(value); }

function resolveAccidentPartyLabel(input: { accident_party_label?: unknown; accident_party_type?: unknown; chart_no?: unknown }) {
  const existing = sanitizeDisplayText(input.accident_party_label, "");
  if (existing && existing !== "확인이 필요합니다.") return existing;
  const type = String(input.accident_party_type || "").trim();
  const byType: Record<string, string> = {
    car_vs_car: "차대차 사고",
    vehicle_vs_vehicle: "차대차 사고",
    car_vs_person: "차대사람 사고",
    pedestrian_crosswalk_accident: "차대사람 사고",
    car_vs_bicycle: "차대자전거 사고",
    bicycle_collision: "차대자전거 사고",
    car_vs_motorcycle: "차대오토바이 사고",
    single_vehicle: "단독 사고",
    single_vehicle_accident: "단독 사고",
    object_collision: "물체/시설물 사고",
    car_vs_object: "물체/시설물 사고",
  };
  if (byType[type]) return byType[type];
  const chartNo = sanitizeDisplayText(input.chart_no, "");
  if (chartNo.startsWith("차")) return "차대차 사고";
  if (chartNo.startsWith("보")) return "차대사람 사고";
  if (chartNo.startsWith("자") || chartNo.startsWith("거")) return "차대자전거 사고";
  if (chartNo.startsWith("단")) return "단독 사고";
  if (chartNo.startsWith("기") || chartNo.startsWith("물")) return "물체/시설물 사고";
  return "";
}

function extractSituationTitle(value: unknown) {
  let raw = sanitizeDisplayText(value);
  if (!raw) return "";
  raw = raw.replace(/^[\s,，.]+/, "").trim();
  const mixed = raw.match(/^(.+?\s*사고)\s*상황은\s*[^,.。]*로 보이며(?:,|\s|$)/);
  if (mixed?.[1]) return mixed[1].trim();
  const sentence = raw.split(/[.!?。]\s*/)[0]?.trim() || raw;
  const title = sentence.match(/^(.+?\s*사고)(?:\s|$)/);
  return sanitizeDisplayText(title?.[1] || sentence);
}

function percentText(value: unknown) {
  if (value === null || value === undefined || value === "") return "확인 필요";
  const textValue = sanitizeDisplayText(value);
  if (!textValue) return "확인 필요";
  if (/%|확인|필요|~/.test(textValue)) return textValue;
  const numeric = Number(textValue);
  if (Number.isFinite(numeric)) return `${numeric}%`;
  return textValue;
}

function isAmbiguousAdjustmentLabel(label: string) {
  return /현저한 과실|중대한 과실|12대 중과실|형사 위험|중과실/.test(label);
}

function isAdjustmentSelected(item: any) {
  if (!item?.key) return false;
  const override = userAdjustmentOverrides.value[item.key];
  return override === undefined ? item.initialSelected === true : override === true;
}

function toggleUserAdjustment(item: any) {
  if (!item?.key) return;
  userAdjustmentOverrides.value = {
    ...userAdjustmentOverrides.value,
    [item.key]: !isAdjustmentSelected(item),
  };
}

function adjustmentEffect(item: any) {
  const source = item?.applied_effect || item?.effect || item?.delta || {};
  const a = source?.A ?? source?.a ?? source?.my ?? item?.delta_A ?? item?.delta_a ?? item?.delta_my ?? 0;
  const b = source?.B ?? source?.b ?? source?.other ?? item?.delta_B ?? item?.delta_b ?? item?.delta_other ?? 0;
  return { A: Number(a) || 0, B: Number(b) || 0 };
}

function adjustmentEffectText(item: any) {
  const effect = adjustmentEffect(item);
  const parts = [];
  if (effect.A) parts.push(`A ${effect.A > 0 ? "+" : ""}${effect.A}%p`);
  if (effect.B) parts.push(`B ${effect.B > 0 ? "+" : ""}${effect.B}%p`);
  return parts.join(" / ");
}

function normalizeFaultPair(value: any): { A: number; B: number } | null {
  if (!value) return null;
  if (typeof value === "object") {
    const a = value.A ?? value.a ?? value.my ?? value.user ?? value.driver;
    const b = value.B ?? value.b ?? value.other ?? value.opponent ?? value.counterparty;
    if (a !== undefined && b !== undefined) return { A: clampPercent(Number(a)), B: clampPercent(Number(b)) };
  }
  return null;
}

function clampPercent(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function safeKniaButtonUrl(card: any) {
  const raw = String(card?.button_url || card?.video_url || card?.source_url || card?.source_detail_url || card?.source_page_url || "").trim();
  if (!raw || /\s/.test(raw)) return "";
  try {
    const url = new URL(raw);
    return url.hostname.toLowerCase() === "accident.knia.or.kr" && ["http:", "https:"].includes(url.protocol) ? url.toString() : "";
  } catch {
    return "";
  }
}

function faultText(value: any): string {
  if (!value) return "";
  if (typeof value === "string" || typeof value === "number") return percentText(value);
  if (typeof value !== "object") return "";
  const my = value.my ?? value.A ?? value.user ?? value.ego ?? value.driver;
  const other = value.other ?? value.B ?? value.opponent ?? value.counterparty;
  if (my !== undefined && other !== undefined) return `A ${percentText(my)} / B ${percentText(other)}`;
  const min = value.min ?? value.minimum;
  const max = value.max ?? value.maximum;
  if (min !== undefined && max !== undefined) return `${percentText(min)}~${percentText(max)}`;
  return text(value.label || value.summary || "");
}

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
