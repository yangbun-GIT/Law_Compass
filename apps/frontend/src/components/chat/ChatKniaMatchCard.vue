<template>
  <article class="chat-card chat-knia-card">
    <p class="chat-card__eyebrow">비슷한 과실비율 인정기준</p>
    <img v-if="match.thumbnail_url" :src="match.thumbnail_url" alt="과실비율 기준 썸네일" loading="lazy" />
    <div class="chat-mini-tags">
      <span v-if="match.accident_party_label">{{ text(match.accident_party_label) }}</span>
      <span v-for="tag in match.display_tags || []" :key="tag">{{ text(tag) }}</span>
    </div>
    <h4>{{ text(match.chart_no) }} · {{ text(match.title) }}</h4>
    <p>{{ text(match.match_reason || "입력하신 사고와 비슷한 기준으로 참고할 수 있습니다.") }}</p>
    <p v-if="faultLabel" class="chat-fault-label">{{ faultLabel }}</p>
    <ul v-if="match.recommended_user_actions?.length" class="check-list">
      <li v-for="action in match.recommended_user_actions.slice(0, 3)" :key="action">{{ text(action) }}</li>
    </ul>
    <div class="btn-row">
      <button class="btn secondary" type="button" @click="goChart">기준 보기</button>
      <button v-if="mediaTarget" class="btn secondary" type="button" @click="openMedia">관련 영상 보기</button>
      <button class="btn secondary" type="button" @click="goRanking">많이 검색된 사고유형 보기</button>
    </div>
    <p class="kv">{{ text(match.attribution || '출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털') }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ChatKniaMatch, ChatSuggestion } from "../../types/chat";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ match: ChatKniaMatch }>();
const emit = defineEmits<{ suggest: [suggestion: ChatSuggestion] }>();
const mediaTarget = computed(() => props.match.video_url || props.match.source_url || "");
const faultLabel = computed(() => {
  if (typeof props.match.base_fault_a === "number" && typeof props.match.base_fault_b === "number") {
    return `기본 참고: A ${props.match.base_fault_a}% / B ${props.match.base_fault_b}%`;
  }
  return "";
});
function text(value: unknown) { return sanitizeDisplayText(value); }
function goChart() {
  emit("suggest", { label: "비슷한 과실비율 기준 보기", action: "navigate", target: `/knia/charts/${encodeURIComponent(props.match.chart_no)}` });
}
function openMedia() {
  emit("suggest", { label: "관련 영상 보기", action: "open_external", target: mediaTarget.value });
}
function goRanking() {
  emit("suggest", { label: "많이 검색된 사고유형 보기", action: "navigate", target: "/knia/ranking" });
}
</script>
