<template>
  <article class="card hero-card case-summary">
    <div>
      <span class="badge" :class="statusClass(caseData.status)">{{ statusLabel(caseData.status) }}</span>
      <h3>{{ caseData.title }}</h3>
      <p>{{ descriptionText || "사고 설명을 입력해 주세요." }}</p>
    </div>
    <div class="summary-metrics">
      <div>
        <strong>{{ selectedKeywordCount }}</strong>
        <span>선택 키워드</span>
      </div>
      <div>
        <strong>{{ uploadCount }}</strong>
        <span>업로드</span>
      </div>
      <div>
        <strong>{{ jobCount }}</strong>
        <span>작업</span>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { CaseItem } from "../../api/client";

defineProps<{
  caseData: CaseItem;
  descriptionText: string;
  selectedKeywordCount: number;
  uploadCount: number;
  jobCount: number;
  statusLabel: (status?: string) => string;
  statusClass: (status?: string) => string;
}>();
</script>

<style scoped>
.case-summary {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.case-summary h3 {
  margin: 12px 0 8px;
  font-size: 1.5rem;
}

.case-summary p {
  margin: 0;
  line-height: 1.6;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(92px, 1fr));
  gap: 10px;
  min-width: min(360px, 100%);
}

.summary-metrics div {
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  text-align: center;
}

.summary-metrics strong {
  display: block;
  font-size: 1.7rem;
}

.summary-metrics span {
  color: var(--text-sub);
  font-size: 0.84rem;
}

@media (max-width: 900px) {
  .case-summary {
    flex-direction: column;
  }

  .summary-metrics {
    width: 100%;
  }
}

@media (max-width: 560px) {
  .summary-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
