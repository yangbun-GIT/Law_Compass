<template>
  <article class="card easy-card">
    <h2>{{ text(fault.title || "과실비율 참고 추정") }}</h2>
    <KniaFaultRatioBar
      :a="fault.my_percent"
      :b="fault.other_percent"
      :left-label="text(fault.my_label || '내 책임')"
      :right-label="text(fault.other_label || '상대방 책임')"
      variant="user"
    />
    <p class="big-text">{{ text(fault.easy_explanation) }}</p>
    <h3>왜 이렇게 보나요?</h3>
    <ul class="check-list">
      <li v-for="item in fault.why || []" :key="item">{{ text(item) }}</li>
    </ul>
    <p v-if="fault.caution" class="soft-warning">{{ text(fault.caution) }}</p>
  </article>
</template>

<script setup lang="ts">
import KniaFaultRatioBar from "../knia/KniaFaultRatioBar.vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

defineProps<{ fault: any }>();

function text(value: unknown) {
  return sanitizeDisplayText(value);
}

</script>
