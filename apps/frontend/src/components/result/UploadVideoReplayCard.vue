<template>
  <article v-if="upload" class="card easy-card wide-card upload-video-replay-card">
    <div class="upload-video-head">
      <div>
        <p class="eyebrow">블랙박스 영상</p>
        <h2>업로드한 사고 영상을 다시 볼 수 있습니다</h2>
        <p class="kv">
          영상은 저장소 경로를 직접 공개하지 않고, 짧게 만료되는 보안 링크로 재생됩니다.
        </p>
      </div>
      <div class="btn-row">
        <button class="btn secondary" :disabled="loading" @click="$emit('refresh')">
          {{ loading ? "링크 발급 중..." : "영상 링크 새로고침" }}
        </button>
        <button class="btn secondary" :disabled="loading" @click="$emit('download')">다운로드</button>
      </div>
    </div>

    <div class="upload-video-meta">
      <span class="chip selected">{{ upload.file_name }}</span>
      <span class="chip">{{ statusLabel(upload.status) }}</span>
      <span v-if="expiresAt" class="chip">만료 {{ expiresAt }}</span>
    </div>

    <p v-if="error" class="msg-error">{{ error }}</p>

    <video
      v-if="viewUrl"
      class="video-preview result-video-preview"
      controls
      playsinline
      preload="metadata"
      :src="viewUrl"
      @error="$emit('refresh')"
    ></video>

    <div v-else class="upload-video-placeholder">
      <p>{{ loading ? "영상 재생 링크를 준비하고 있습니다." : "영상 링크가 만료되었거나 아직 발급되지 않았습니다." }}</p>
      <button class="btn" :disabled="loading" @click="$emit('refresh')">영상 보기</button>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { UploadItem } from "../../api/client";

defineProps<{
  upload: UploadItem | null;
  viewUrl: string;
  loading?: boolean;
  error?: string;
  expiresAt?: string;
}>();

defineEmits<{
  refresh: [];
  download: [];
}>();

function statusLabel(status?: string) {
  const value = String(status || "").toLowerCase();
  if (value === "ready") return "분석 완료";
  if (value === "processing") return "분석 중";
  if (value === "verified") return "확인 완료";
  if (value === "uploaded") return "업로드 완료";
  return status || "상태 확인 중";
}
</script>

<style scoped>
.upload-video-replay-card {
  display: grid;
  gap: 16px;
}

.upload-video-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.upload-video-head h2,
.upload-video-head p {
  margin: 0;
}

.upload-video-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.result-video-preview {
  width: 100%;
  max-height: 520px;
  background: #000;
}

.upload-video-placeholder {
  display: grid;
  justify-items: start;
  gap: 10px;
  padding: 18px;
  border: 1px dashed rgba(201, 169, 98, 0.38);
  border-radius: 14px;
  background: rgba(232, 223, 212, 0.06);
}

.upload-video-placeholder p {
  margin: 0;
  color: var(--text-sub);
}

@media (max-width: 760px) {
  .upload-video-head {
    flex-direction: column;
  }
}
</style>
