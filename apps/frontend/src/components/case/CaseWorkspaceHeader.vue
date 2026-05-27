<template>
  <div class="workspace-head">
    <div>
      <p class="eyebrow">사고 입력</p>
      <h2>{{ caseTitle || "사고 케이스" }}</h2>
      <p class="kv">{{ caseStatus ? statusLabel(caseStatus) : "케이스 정보를 확인하는 중입니다." }}</p>
    </div>
    <div class="btn-row">
      <button class="btn secondary" :disabled="initialLoading || !!busy" @click="$emit('refresh')">정보 다시 확인</button>
      <RouterLink class="btn secondary" :to="`/cases/${caseId}/result`">결과 쉽게 보기</RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  caseId: string;
  caseTitle?: string;
  caseStatus?: string;
  initialLoading: boolean;
  busy: string;
  statusLabel: (status?: string) => string;
}>();

defineEmits<{
  (event: "refresh"): void;
}>();
</script>

<style scoped>
.workspace-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.workspace-head h2 {
  margin: 0;
}

@media (max-width: 900px) {
  .workspace-head {
    flex-direction: column;
  }
}
</style>
