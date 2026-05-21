<template>
  <div class="chat-bubble" :class="message.role === 'user' ? 'chat-bubble--user' : 'chat-bubble--assistant'">
    <p>{{ clean(message.content) }}</p>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from "../../types/chat";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

defineProps<{ message: ChatMessage }>();
function clean(value: unknown) {
  return sanitizeDisplayText(value);
}
</script>
