<template>
  <article class="card easy-card" v-if="card">
    <p class="eyebrow">사고 대분류</p>
    <h2>{{ text(card.label || card.title || '사고유형 확인 필요') }}</h2>
    <p class="big-text">{{ text(card.summary || '사고 유형에 맞춰 필요한 조치를 정리했습니다.') }}</p>
    <h3>먼저 해 주세요</h3>
    <ul class="check-list">
      <li v-for="action in card.top_actions || []" :key="action">{{ text(action) }}</li>
    </ul>
    <p v-if="card.cautions?.length" class="soft-warning">{{ card.cautions.map(text).join(' ') }}</p>
  </article>
</template>
<script setup lang="ts">
import { sanitizeDisplayText } from '../../utils/displaySanitizer';
defineProps<{ card: any }>();
function text(value: unknown) { return sanitizeDisplayText(value); }
</script>
