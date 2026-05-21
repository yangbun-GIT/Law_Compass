<template>
  <div v-if="suggestions.length" class="chat-suggestions">
    <button v-for="item in suggestions" :key="item.label + item.action" type="button" @click="$emit('select', item)">
      {{ text(item.label) }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { ChatSuggestion } from "../../types/chat";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

defineProps<{ suggestions: ChatSuggestion[] }>();
defineEmits<{ select: [suggestion: ChatSuggestion] }>();
function text(value: unknown) { return sanitizeDisplayText(value); }
</script>
