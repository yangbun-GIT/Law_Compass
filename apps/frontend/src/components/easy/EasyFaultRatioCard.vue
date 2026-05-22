<template>
  <article class="card easy-card">
    <h2>{{ text(fault.title || "과실비율 참고 추정") }}</h2>
    <div class="easy-ratio-row">
      <div>
        <span>{{ showPercent(fault.my_percent) }}</span>
        <p>{{ text(fault.my_label || "내 책임") }}</p>
      </div>
      <div>
        <span class="accent">{{ showPercent(fault.other_percent) }}</span>
        <p>{{ text(fault.other_label || "상대방 책임") }}</p>
      </div>
    </div>
    <p class="big-text">{{ text(fault.easy_explanation) }}</p>
    <h3>왜 이렇게 보나요?</h3>
    <ul class="check-list">
      <li v-for="item in fault.why || []" :key="item">{{ text(item) }}</li>
    </ul>
    <p v-if="fault.caution" class="soft-warning">{{ text(fault.caution) }}</p>
  </article>
</template>

<script setup lang="ts">
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

defineProps<{ fault: any }>();

function text(value: unknown) {
  return sanitizeDisplayText(value);
}

function showPercent(value: number | string | null | undefined) {
  const n = Number(value);
  return Number.isFinite(n) ? `${Math.round(n)}%` : "확인 필요";
}
</script>
