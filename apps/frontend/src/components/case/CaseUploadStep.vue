<template>
  <article class="card easy-card">
    <div class="step-head">
      <span class="step-index">2</span>
      <div>
        <h2>영상 업로드</h2>
        <p class="kv">선택한 영상은 안전하게 보관한 뒤 사고 장면 확인에 사용합니다.</p>
      </div>
    </div>

    <input type="file" accept="video/*" @change="$emit('fileChange', $event)" />
    <p v-if="file" class="kv">선택 파일: {{ file.name }} ({{ prettySize(file.size) }})</p>

    <div class="btn-row">
      <button class="btn" :disabled="!file || !!busy" @click="$emit('uploadLocal')">
        {{ busy === "upload" ? "영상을 저장하고 있습니다..." : "영상 저장하기" }}
      </button>
      <button class="btn secondary" :disabled="!activeUploadId || !!busy" @click="$emit('completeUpload')">
        {{ busy === "preprocess" ? "영상 분석 준비 중..." : "사고 장면 확인하기" }}
      </button>
      <button class="btn secondary" :disabled="!!busy" @click="$emit('loadUploads')">저장된 영상 불러오기</button>
    </div>

    <label>업로드 선택
      <select :value="selectedUploadId" @change="$emit('update:selectedUploadId', eventValue($event))">
        <option value="">선택하세요</option>
        <option v-for="up in uploads" :key="up.id" :value="up.id">
          {{ up.file_name }} / {{ statusLabel(up.status) }}
        </option>
      </select>
    </label>

    <ul v-if="uploads.length" class="list-reset upload-list">
      <li v-for="up in uploads" :key="up.id">
        <strong>{{ up.file_name }}</strong>
        <span class="badge" :class="statusClass(up.status)">{{ statusLabel(up.status) }}</span>
        <p class="kv">{{ prettySize(up.file_size_bytes) }} / {{ formatDate(up.created_at) }}</p>
      </li>
    </ul>

    <div class="btn-row">
      <button class="btn secondary" :disabled="!activeUploadId || !!busy" @click="$emit('fetchViewUrl')">영상 재생</button>
      <button class="btn secondary" :disabled="!activeUploadId || !!busy" @click="$emit('fetchDownloadUrl')">다운로드</button>
    </div>
    <video v-if="viewUrl" controls :src="viewUrl" class="video-preview"></video>
  </article>
</template>

<script setup lang="ts">
import type { UploadItem } from "../../api/client";

defineProps<{
  file: File | null;
  uploads: UploadItem[];
  selectedUploadId: string;
  activeUploadId: string;
  viewUrl: string;
  busy: string;
  prettySize: (bytes: number) => string;
  formatDate: (iso: string) => string;
  statusLabel: (status?: string) => string;
  statusClass: (status?: string) => string;
}>();

defineEmits<{
  (event: "fileChange", value: Event): void;
  (event: "update:selectedUploadId", value: string): void;
  (event: "uploadLocal"): void;
  (event: "completeUpload"): void;
  (event: "loadUploads"): void;
  (event: "fetchViewUrl"): void;
  (event: "fetchDownloadUrl"): void;
}>();

function eventValue(event: Event) {
  return (event.target as HTMLSelectElement).value;
}
</script>

<style scoped>
.step-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.step-head h2,
.step-head p {
  margin: 0;
}

.step-head h2 {
  font-size: 1.55rem;
  line-height: 1.25;
}

.step-index {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #06202a;
  background: linear-gradient(135deg, var(--accent), #a7f3d0);
  font-weight: 900;
}

.upload-list {
  display: grid;
  gap: 8px;
  margin: 12px 0;
}

.upload-list li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 12px;
  align-items: center;
}

.upload-list .kv {
  grid-column: 1 / -1;
}
</style>
