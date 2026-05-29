<template>
  <article class="card easy-card">
    <h2>지금 해야 할 일 3가지</h2>
    <ol class="action-steps">
      <li v-for="item in actions" :key="item.order || item.title">
        <strong>{{ text(item.title, "확인할 조치") }}</strong>
        <p>{{ text(item.description, "사고 처리에 필요한 내용을 차분히 확인해 주세요.") }}</p>
        <span
          :class="[
            'importance-badge',
            String(item.importance || '').includes('매우') ? 'is-critical' : 'is-normal',
          ]"
        >
          {{ text(item.importance, "중요") }}
        </span>
      </li>
    </ol>
  </article>
</template>

<script setup lang="ts">
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

defineProps<{ actions: any[] }>();

function text(value: unknown, fallback = "") {
  return sanitizeDisplayText(value, fallback);
}
</script>
