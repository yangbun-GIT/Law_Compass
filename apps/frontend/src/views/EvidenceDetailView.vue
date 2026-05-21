<template>
  <section class="card">
    <RouterLink class="btn secondary" to="/">목록으로</RouterLink>
    <h2>{{ chunk?.document_title || "근거 문서" }}</h2>
    <p class="kv">source: {{ chunk?.source_name || "-" }}</p>
    <p class="kv">chunk_id: {{ chunk?.id }}</p>
    <article class="evidence-detail">
      <p>{{ chunk?.chunk_summary || chunk?.chunk_text }}</p>
      <pre v-if="chunk?.chunk_text">{{ chunk.chunk_text }}</pre>
    </article>
    <p v-if="message" class="msg-error">{{ message }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api/client";

const chunkId = useRoute().params.chunkId as string;
const chunk = ref<any>(null);
const message = ref("");

onMounted(async () => {
  try {
    chunk.value = (await api.getEvidenceChunk(chunkId)).chunk;
  } catch (e: any) {
    message.value = e.message;
  }
});
</script>
