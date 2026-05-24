<template>
  <article class="card easy-card" v-if="video?.source_url">
    <h2>{{ text(video.title || '관련 영상 또는 원문 보기') }}</h2>
    <p class="easy-summary">{{ text(video.notice || '영상은 원본 사이트 링크로만 제공합니다.') }}</p>
    <div class="btn-row">
      <a class="btn" :href="video.source_url" target="_blank" rel="noopener noreferrer">{{ text(video.button_label || '과실비율정보포털에서 보기') }}</a>
    </div>
    <p class="kv">{{ text(video.source_label || video.attribution || '자료 출처: 과실비율정보포털') }}</p>
  </article>
</template>
<script setup lang="ts">
import { sanitizeDisplayText } from '../../utils/displaySanitizer';
defineProps<{ video: any }>();
function text(value: unknown) { return sanitizeDisplayText(value); }
</script>
