<template>
  <article class="chat-card chat-draft-card">
    <p class="chat-card__eyebrow">사고 입력 초안</p>
    <h4>{{ text(draft.title) }}</h4>
    <p>{{ text(draft.description_text) }}</p>
    <div class="chat-mini-tags">
      <span v-for="keyword in draft.selected_keywords || []" :key="keyword">{{ text(keyword) }}</span>
    </div>
    <button class="btn" type="button" @click="$emit('apply')">이 내용으로 사고 입력하기</button>
    <p v-if="draft.followup_questions?.length" class="kv">부족한 정보: {{ draft.followup_questions.map(text).join(', ') }}</p>
  </article>
</template>

<script setup lang="ts">
import type { ChatDraftCase } from "../../types/chat";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

defineProps<{ draft: ChatDraftCase }>();
defineEmits<{ apply: [] }>();
function text(value: unknown) { return sanitizeDisplayText(value); }
</script>
