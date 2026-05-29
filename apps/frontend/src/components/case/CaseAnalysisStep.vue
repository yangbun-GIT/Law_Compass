<template>
  <article class="card easy-card">
    <div class="step-head">
      <span class="step-index">3</span>
      <div>
        <h2>분석 요청</h2>
        <p class="kv">텍스트 분석은 즉시 결과를 만들고, 영상 분석은 작업 큐에 등록합니다.</p>
      </div>
    </div>

    <div class="btn-row">
      <button class="btn" :disabled="!!busy" @click="$emit('analyzeText')">
        {{ busy === "text-analysis" ? "분석 중..." : "텍스트 분석" }}
      </button>
      <button class="btn secondary" :disabled="!activeUploadId || !!busy" @click="$emit('analyzeVideo')">
        {{ busy === "video-analysis" ? "작업 등록 중..." : "영상 분석 작업 등록" }}
      </button>
      <button class="btn secondary" :disabled="!!busy" @click="$emit('loadJobs')">작업 조회</button>
      <button class="btn secondary" :disabled="!!busy" @click="$emit('loadReport')">결과 새로고침</button>
    </div>

    <p v-if="message" :class="messageOk ? 'msg-ok' : 'msg-error'">{{ message }}</p>

    <ul v-if="jobs.length" class="list-reset job-list">
      <li v-for="job in jobs" :key="job.id">
        <strong>{{ job.type }}</strong>
        <span class="badge" :class="statusClass(job.status)">{{ statusLabel(job.status) }}</span>
        <p class="kv">attempts: {{ job.attempts ?? job.attempt ?? 0 }}</p>
      </li>
    </ul>
    <p v-else class="kv">등록된 분석 작업이 없습니다.</p>
  </article>
</template>

<script setup lang="ts">
type JobItem = {
  id: string;
  type: string;
  status: string;
  attempts?: number;
  attempt?: number;
};

defineProps<{
  jobs: JobItem[];
  message: string;
  messageOk: boolean;
  activeUploadId: string;
  busy: string;
  statusLabel: (status?: string) => string;
  statusClass: (status?: string) => string;
}>();

defineEmits<{
  (event: "analyzeText"): void;
  (event: "analyzeVideo"): void;
  (event: "loadJobs"): void;
  (event: "loadReport"): void;
}>();
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
  background: linear-gradient(180deg, #D4B872 0%, #C9A962 62%, #B8953F 100%);
  font-weight: 900;
}

.job-list {
  display: grid;
  gap: 8px;
  margin: 12px 0;
}

.job-list li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 12px;
  align-items: center;
}

.job-list .kv {
  grid-column: 1 / -1;
}
</style>
