<template>
  <article class="card hero-card easy-hero">
    <p class="eyebrow">핵심 결론</p>
    <h1>{{ text(report.headline) }}</h1>
    <div v-if="faultLabel" class="fault-summary-card">{{ faultLabel }}</div>
    <div class="chips">
      <span class="chip selected">{{ text(report.summary_for_user?.accident_type_label || "교통사고") }}</span>
      <span class="chip">참고용 분석입니다</span>
    </div>
    <p class="easy-summary">{{ text(report.summary_for_user?.short_summary) }}</p>
    <p v-if="report.summary_for_user?.warning" class="soft-warning">{{ text(report.summary_for_user.warning) }}</p>
  </article>
</template>

<script setup lang="ts">
import { sanitizeDisplayText } from "../../utils/displaySanitizer";
import { computed } from "vue";

const props = defineProps<{ report: any }>();

const faultLabel = computed(() => {
  const fault = props.report?.fault_explanation || {};
  const my = Number(fault.my_percent);
  const other = Number(fault.other_percent);
  if (!Number.isFinite(my) || !Number.isFinite(other)) return "";
  const accidentLabel = String(props.report?.summary_for_user?.accident_type_label || "");
  if (props.report?.scenario_type === "rear_end_collision" || accidentLabel.includes("후미")) {
    const myLow = my <= 10 ? 0 : Math.max(0, my - 10);
    const myHigh = my <= 10 ? 10 : my;
    const otherLow = other >= 90 ? 90 : other;
    const otherHigh = other >= 90 ? 100 : Math.min(100, other + 10);
    return `예상 과실: 내 차 ${myLow}~${myHigh}% / 상대 ${otherLow}~${otherHigh}%`;
  }
  return `예상 과실: 내 차 ${Math.round(my)}% / 상대 ${Math.round(other)}%`;
});

function text(value: unknown) {
  return sanitizeDisplayText(value);
}
</script>
