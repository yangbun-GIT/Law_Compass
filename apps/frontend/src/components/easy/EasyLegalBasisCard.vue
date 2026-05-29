<template>
  <article class="basis-card">
    <p class="eyebrow">{{ text(card.law_name || "법률 근거") }}</p>
    <h3>{{ text(card.easy_title || "함께 검토할 법률 기준") }}</h3>
    <div class="legal-paragraphs">
      <p v-for="paragraph in explanationParagraphs" :key="paragraph">{{ paragraph }}</p>
    </div>
    <details class="inline-details" v-if="reasonParagraphs.length">
      <summary>이번 사고와 관련된 이유</summary>
      <div class="legal-paragraphs">
        <p v-for="paragraph in reasonParagraphs" :key="paragraph">{{ paragraph }}</p>
      </div>
    </details>
    <div class="chips">
      <span class="chip">{{ label(card.confidence_label || "근거용") }}</span>
      <span class="chip">{{ label(card.source_label || "법률 근거") }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText, splitLegalBasisParagraphs, toUserFriendlyEvidenceLabel } from "../../utils/displaySanitizer";

const props = defineProps<{ card: any }>();
const explanationParagraphs = computed(() => splitLegalBasisParagraphs(props.card?.easy_explanation || props.card?.summary));
const reasonParagraphs = computed(() => splitLegalBasisParagraphs(props.card?.related_to_this_case));

function text(value: unknown) {
  return sanitizeDisplayText(value);
}

function label(value: unknown) {
  return toUserFriendlyEvidenceLabel(value);
}
</script>
