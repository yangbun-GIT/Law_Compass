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
        <button class="btn" :disabled="loading" @click="$emit('refresh')">
          {{ viewUrl ? "블랙박스 영상 다시 보기" : "블랙박스 영상 보기" }}
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

    <div v-if="loading" class="upload-video-loading" role="status" aria-live="polite">
      <span class="upload-video-spinner" aria-hidden="true"></span>
      <div>
        <strong>보안 재생 토큰을 발급하고 있습니다</strong>
        <p>짧게 만료되는 HMAC 링크를 준비하는 중입니다. 잠시만 기다려 주세요.</p>
      </div>
    </div>

    <div v-if="viewUrl" class="upload-video-player-shell">
      <video
        class="video-preview result-video-preview"
        controls
        playsinline
        preload="metadata"
        :src="viewUrl"
        @error="$emit('token-expired')"
      ></video>
      <p class="kv">재생 링크가 만료되면 위의 “블랙박스 영상 다시 보기”를 눌러 새 보안 링크를 발급하세요.</p>
    </div>

    <div v-else class="upload-video-placeholder">
      <p>
        영상은 바로 공개하지 않고, 버튼을 누를 때마다 짧게 만료되는 HMAC 보안 링크를 발급해 재생합니다.
      </p>
      <button class="btn" :disabled="loading" @click="$emit('refresh')">블랙박스 영상 보기</button>
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
  "token-expired": [];
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

.upload-video-player-shell {
  display: grid;
  gap: 10px;
}

.upload-video-loading {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(201, 169, 98, 0.38);
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(201, 169, 98, 0.16), rgba(37, 30, 25, 0.76)),
    rgba(28, 23, 20, 0.84);
  color: var(--text-main);
}

.upload-video-loading strong,
.upload-video-loading p {
  margin: 0;
}

.upload-video-loading p {
  color: var(--text-sub);
  line-height: 1.55;
}

.upload-video-spinner {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border-radius: 999px;
  border: 3px solid rgba(201, 169, 98, 0.28);
  border-top-color: var(--accent-strong);
  animation: upload-token-spin 0.9s linear infinite;
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

  .upload-video-loading {
    align-items: flex-start;
  }
}

@keyframes upload-token-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
