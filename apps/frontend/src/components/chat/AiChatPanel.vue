<template>
  <aside class="ai-chat-panel glass" role="dialog" aria-label="AI 사고 도우미">
    <header class="ai-chat-header">
      <div>
        <strong>AI 사고 도우미</strong>
        <p>사고 입력과 결과 해석을 쉽게 도와드려요.</p>
      </div>
      <button class="ai-chat-close" aria-label="채팅 닫기" @click="chat.close()">×</button>
    </header>

    <section ref="scrollBox" class="ai-chat-body">
      <div v-if="!chat.messages.length" class="ai-chat-welcome">
        <h3>무엇을 도와드릴까요?</h3>
        <p>사고 상황을 한 문장으로 적어 주시면, 입력 초안과 비슷한 과실비율 기준을 찾아드릴게요.</p>
      </div>
      <template v-for="(message, idx) in chat.messages" :key="idx">
        <ChatMessageBubble :message="message" />
        <ChatViolationNotice v-if="message.safety && !message.safety.allowed" :safety="message.safety" />
        <ChatDraftCaseCard v-if="message.draft_case" :draft="message.draft_case" @apply="chat.applyDraftCase(message.draft_case!)" />
        <ChatKniaMatchCard v-if="message.knia_primary_match" :match="message.knia_primary_match" @suggest="chat.applySuggestion" />
      </template>
      <p v-if="chat.isLoading" class="ai-chat-typing">답변을 준비하고 있어요...</p>
    </section>

    <ChatSuggestionChips :suggestions="chat.suggestions" @select="chat.applySuggestion" />

    <footer class="ai-chat-footer">
      <textarea
        v-model="text"
        rows="2"
        placeholder="예: 정차 중 뒤차가 박았어. 관련 영상도 볼 수 있어?"
        @keydown.enter.exact.prevent="send"
      />
      <button class="btn" :disabled="chat.isLoading || !text.trim()" @click="send">전송</button>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { useChatStore } from "../../stores/chatStore";
import ChatDraftCaseCard from "./ChatDraftCaseCard.vue";
import ChatKniaMatchCard from "./ChatKniaMatchCard.vue";
import ChatMessageBubble from "./ChatMessageBubble.vue";
import ChatSuggestionChips from "./ChatSuggestionChips.vue";
import ChatViolationNotice from "./ChatViolationNotice.vue";

const chat = useChatStore();
const text = ref("");
const scrollBox = ref<HTMLElement | null>(null);

async function send() {
  const value = text.value.trim();
  if (!value) return;
  text.value = "";
  await chat.sendMessage(value);
}

watch(() => chat.messages.length, async () => {
  await nextTick();
  if (scrollBox.value) scrollBox.value.scrollTop = scrollBox.value.scrollHeight;
});
</script>
