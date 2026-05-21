<template>
  <article class="card easy-card knia-card" v-if="standard">
    <p class="eyebrow">과실비율정보포털 기준</p>
    <h2>{{ text(standard.title || "이 사고와 비슷한 과실비율 인정기준") }}</h2>
    <div class="chips">
      <span class="chip selected" v-if="standard.chart_no">기준번호 {{ text(standard.chart_no) }}</span>
      <span class="chip" v-if="standard.base_fault_label">{{ text(standard.base_fault_label) }}</span>
    </div>
    <h3>{{ text(standard.chart_title || "유사 사고 기준") }}</h3>
    <p class="big-text">{{ text(standard.easy_explanation) }}</p>
    <p class="soft-warning"><strong>왜 비슷한가요?</strong><br />{{ text(standard.why_similar) }}</p>
    <div class="btn-row">
      <a v-if="standard.source_url" class="btn secondary" :href="standard.source_url" target="_blank" rel="noopener noreferrer">원문 기준 보기</a>
    </div>
    <p class="kv">{{ text(standard.source_label) }}</p>
    <p class="kv">{{ text(standard.disclaimer) }}</p>
  </article>
</template>
<script setup lang="ts">
import { sanitizeDisplayText } from "../../utils/displaySanitizer";
defineProps<{ standard: any }>();
function text(value: unknown) { return sanitizeDisplayText(value); }
</script>
