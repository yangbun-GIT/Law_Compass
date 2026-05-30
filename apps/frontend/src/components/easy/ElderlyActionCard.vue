<template>
  <article class="card easy-card">
    <h2>지금 해야 할 일 3가지</h2>
    <ol class="action-steps">
      <li v-for="item in actions" :key="item.order">
        <strong>{{ text(item.title) }}</strong>
        <p>{{ text(item.description) }}</p>
        <span v-if="text(item.importance)" :class="importanceClass(item.importance)">
          {{ text(item.importance) }}
        </span>
      </li>
    </ol>
  </article>
</template>

<script setup lang="ts">
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

defineProps<{ actions: any[] }>();

function text(value: unknown) {
  return sanitizeDisplayText(value, "");
}

function importanceClass(value: unknown) {
  const label = text(value);
  return ["importance-badge", label.includes("매우") ? "is-critical" : "is-normal"];
}
</script>
