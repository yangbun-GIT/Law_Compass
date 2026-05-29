<template>
  <article class="basis-card">
    <p class="eyebrow">{{ lawName }}</p>
    <h3>{{ title }}</h3>
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
      <span class="chip">{{ label(card.confidence_label || "참고할 수 있는 근거") }}</span>
      <span class="chip">{{ label(card.source_label || "법률 근거") }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  sanitizeDisplayText,
  splitLegalBasisParagraphs,
  toUserFriendlyEvidenceLabel,
} from "../../utils/displaySanitizer";

const props = defineProps<{ card: any }>();

const lawName = computed(() => text(props.card?.law_name, "교통사고 관련 기준"));
const title = computed(() => text(props.card?.easy_title || props.card?.title, "교통사고 관련 기준"));
const explanationParagraphs = computed(() => {
  const paragraphs = splitLegalBasisParagraphs(props.card?.easy_explanation || props.card?.summary);
  return paragraphs.length ? paragraphs : ["입력된 사고 사실과 관련해 참고할 수 있는 기준입니다."];
});
const reasonParagraphs = computed(() => {
  const paragraphs = splitLegalBasisParagraphs(props.card?.related_to_this_case || props.card?.reason);
  return paragraphs.length ? paragraphs : ["사고 유형과 충돌 상황이 유사해 참고 기준으로 확인할 수 있습니다."];
});

function text(value: unknown, fallback = "") {
  return sanitizeDisplayText(value, fallback);
}

function label(value: unknown) {
  return toUserFriendlyEvidenceLabel(value);
}
</script>
