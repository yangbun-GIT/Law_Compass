<template>
  <article class="basis-card">
    <p class="eyebrow">{{ sourceName }}</p>
    <h3>{{ title }}</h3>
    <div class="legal-paragraphs">
      <p v-for="paragraph in explanationParagraphs" :key="paragraph">{{ paragraph }}</p>
    </div>
    <details v-if="reasonText" class="inline-details">
      <summary>이번 사고와 관련된 이유</summary>
      <div class="legal-paragraphs">
        <p>{{ reasonText }}</p>
      </div>
    </details>
    <div class="chips">
      <span class="chip">{{ confidenceLabel }}</span>
      <span class="chip">{{ sourceLabel }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText, toUserFriendlyEvidenceLabel } from "../../utils/displaySanitizer";

const props = defineProps<{ card: any }>();

const sourceName = computed(() =>
  sanitizeDisplayText(props.card?.law_name || props.card?.source_name, "교통사고 관련 기준"),
);

const title = computed(() =>
  sanitizeDisplayText(
    props.card?.easy_title || props.card?.title || props.card?.name,
    "교통사고 관련 기준",
  ),
);

const explanationParagraphs = computed(() => {
  const raw =
    props.card?.paragraphs ||
    props.card?.body ||
    props.card?.summary ||
    props.card?.easy_explanation;
  const items = Array.isArray(raw) ? raw : String(raw || "").split(/\n+/);
  const cleaned = items.map((item) => sanitizeDisplayText(item, "")).filter(Boolean);
  return cleaned.length ? cleaned : ["입력된 사고 사실과 관련해 참고할 수 있는 기준입니다."];
});

const reasonText = computed(() =>
  sanitizeDisplayText(
    props.card?.related_to_this_case || props.card?.reason || props.card?.why_similar,
    "",
  ),
);

const confidenceLabel = computed(() =>
  toUserFriendlyEvidenceLabel(props.card?.confidence_label || "참고할 수 있는 근거"),
);

const sourceLabel = computed(() =>
  toUserFriendlyEvidenceLabel(props.card?.source_label || "국가법령정보센터 또는 과실비율 인정기준 자료"),
);
</script>
