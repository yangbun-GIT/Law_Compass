<script setup lang="ts">
import { computed } from "vue";
import { formatKniaBody, sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ item: any }>();
const paragraphs = computed(() => formatKniaBody(props.item?.summary || props.item?.body || "원문 기준을 확인해 주세요."));
function text(value: unknown) {
  return sanitizeDisplayText(value);
}
</script>

<template>
  <article class="glass-card knia-json-evidence-card">
    <p class="eyebrow">{{ text(item.accident_party_label || "KNIA 근거") }}</p>
    <h3>{{ text(item.title || "과실비율 기준") }}</h3>
    <div class="knia-paragraphs">
      <p v-for="paragraph in paragraphs" :key="paragraph">{{ paragraph }}</p>
    </div>
    <div class="tag-row"><span v-for="tag in item.display_tags || []" :key="tag" class="tag">{{ text(tag) }}</span></div>
    <a v-if="item.source_url" :href="item.source_url" target="_blank" rel="noreferrer">원문 기준 보기</a>
    <small>{{ text(item.attribution || "자료 출처: 과실비율정보포털") }}</small>
  </article>
</template>
