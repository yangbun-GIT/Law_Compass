<template>
  <article class="chat-card chat-warning">
    <strong>안전한 안내만 도와드릴 수 있어요.</strong>
    <p>{{ safeText }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ChatSafety } from "../../types/chat";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ safety: ChatSafety }>();
const safeText = computed(() => sanitizeDisplayText(props.safety.safe_reply || "그 요청은 도와드릴 수 없습니다. 대신 정식 절차로 대응하는 방법은 안내해 드릴 수 있습니다."));
</script>
