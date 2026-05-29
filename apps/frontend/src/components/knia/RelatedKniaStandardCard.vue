<template>
  <article class="card easy-card knia-card" v-if="standard">
    <p class="eyebrow">과실비율정보포털 기준</p>
    <h2>{{ text(standard.title || "이 사고와 비슷한 과실비율 인정기준") }}</h2>
    <div class="chips">
      <span class="chip selected" v-if="standard.chart_no">기준번호 {{ text(standard.chart_no) }}</span>
      <span class="chip" v-if="partyLabel">{{ partyLabel }}</span>
      <span class="chip" v-if="standard.base_fault_label">{{ text(standard.base_fault_label) }}</span>
    </div>

    <h3>{{ text(standard.chart_title || "유사 사고 기준") }}</h3>
    <section class="knia-section">
      <h4>기준 요약</h4>
      <div class="knia-paragraphs">
        <p v-for="paragraph in summaryParagraphs" :key="paragraph">{{ paragraph }}</p>
      </div>
    </section>

    <details class="inline-details" v-if="similarityParagraphs.length">
      <summary>이 기준을 함께 보는 이유</summary>
      <div class="knia-paragraphs">
        <p v-for="paragraph in similarityParagraphs" :key="paragraph">{{ paragraph }}</p>
      </div>
    </details>

    <p v-if="fallbackNotice" class="soft-warning">{{ fallbackNotice }}</p>
    <div class="btn-row">
      <a v-if="standard.source_url" class="btn secondary" :href="standard.source_url" target="_blank" rel="noopener noreferrer">원문 기준 보기</a>
    </div>
    <p class="kv">{{ text(standard.source_label) }}</p>
    <p class="kv">{{ text(standard.disclaimer) }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { formatKniaBody, sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ standard: any }>();
const partyLabel = computed(() => {
  const raw = props.standard?.major_party_type || props.standard?.accident_party_type || props.standard?.party_type || "";
  return raw ? `대분류: ${sanitizeDisplayText(raw)}` : "";
});
const summaryParagraphs = computed(() => formatKniaBody(props.standard?.easy_explanation || props.standard?.summary || props.standard?.body));
const similarityParagraphs = computed(() => formatKniaBody(props.standard?.why_similar));
const fallbackNotice = computed(() => {
  const raw = JSON.stringify(props.standard || {});
  if (/fallback_used|reference_only|review_required/i.test(raw)) {
    return "정확히 같은 상황의 기준은 부족할 수 있어, 같은 대분류에서 참고 가능한 기준으로 보여드립니다.";
  }
  return "";
});

function text(value: unknown) {
  return sanitizeDisplayText(value);
}
</script>
