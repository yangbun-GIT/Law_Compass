<template>
  <article class="basis-card knia-chart-card">
    <p class="kv">기준번호 {{ text(chart.chart_no) }}</p>
    <h3>{{ text(chart.title) }}</h3>
    <p v-if="faultLabel" class="chip selected">{{ faultLabel }}</p>
    <div class="knia-paragraphs">
      <p v-for="paragraph in paragraphs" :key="paragraph">{{ paragraph }}</p>
    </div>
    <p class="kv">{{ text(chart.attribution || "자료 출처: 과실비율정보포털") }}</p>
    <div class="btn-row">
      <RouterLink class="btn secondary" :to="`/knia/charts/${encodeURIComponent(chart.chart_no)}`">자세히 보기</RouterLink>
      <a v-if="chart.source_url" class="btn secondary" :href="chart.source_url" target="_blank" rel="noopener noreferrer">원문 보기</a>
    </div>
  </article>
</template>
<script setup lang="ts">
import { computed } from "vue";
import { formatKniaBody, sanitizeDisplayText } from "../../utils/displaySanitizer";
const props = defineProps<{ chart: any }>();
const faultLabel = computed(() => typeof props.chart.base_fault_a === "number" && typeof props.chart.base_fault_b === "number" ? `기본 참고 A ${props.chart.base_fault_a}% / B ${props.chart.base_fault_b}%` : "");
const paragraphs = computed(() => formatKniaBody(props.chart.accident_summary || props.chart.basic_fault_text));
function text(value: unknown) { return sanitizeDisplayText(value); }
</script>
