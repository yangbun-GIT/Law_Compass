<template>
  <article class="card easy-card reliability-card" v-if="card">
    <div class="reliability-head">
      <div>
        <p class="eyebrow">근거 검증</p>
        <h2>{{ text(card.title || "근거 연결 상태") }}</h2>
      </div>
      <span class="reliability-badge" :class="badgeClass">{{ text(card.level_label || "보통") }}</span>
    </div>
    <p class="big-text">{{ text(card.summary) }}</p>
    <div class="reliability-stats">
      <div v-for="item in card.stats || []" :key="`${item.label}-${item.value}`">
        <span>{{ text(item.value) }}</span>
        <p>{{ text(item.label) }}</p>
      </div>
    </div>
    <ul class="check-list" v-if="card.warnings?.length">
      <li v-for="warning in card.warnings" :key="warning">{{ text(warning) }}</li>
    </ul>
    <p v-if="card.notice" class="kv">{{ text(card.notice) }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ card: any }>();

const badgeClass = computed(() => {
  const label = sanitizeDisplayText(props.card?.level_label);
  if (label === "높음") return "reliability-badge--high";
  if (label === "낮음") return "reliability-badge--low";
  return "reliability-badge--medium";
});

function text(value: unknown) {
  return sanitizeDisplayText(value);
}
</script>
