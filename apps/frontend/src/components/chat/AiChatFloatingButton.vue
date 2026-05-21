<template>
  <button class="ai-chat-fab" aria-label="AI 사고 도우미 열기" @click="chat.isOpen ? chat.close() : chat.open()">
    <svg class="ai-chat-fab__icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4.8 5.4A7.8 7.8 0 0 1 12 2.5c4.35 0 7.9 3.05 7.9 6.82s-3.55 6.83-7.9 6.83c-.66 0-1.3-.07-1.92-.21L5.2 20.4a.8.8 0 0 1-1.3-.67l.56-5.14A6.18 6.18 0 0 1 4.8 5.4Z" fill="currentColor"/>
    </svg>
    <span v-if="chat.unreadCount" class="ai-chat-fab__badge">{{ chat.unreadCount }}</span>
  </button>
  <AiChatPanel v-if="chat.isOpen" />
</template>

<script setup lang="ts">
import { useChatStore } from "../../stores/chatStore";
import AiChatPanel from "./AiChatPanel.vue";

const chat = useChatStore();
</script>
