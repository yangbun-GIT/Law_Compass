<template>
  <article v-if="card" class="card easy-card wide-card expert-guidance-card">
    <div class="expert-header">
      <div>
        <p class="kv">전문가 검토 안내</p>
        <h2>{{ text(card.title, "전문가 검토가 필요한 항목") }}</h2>
      </div>
      <span class="expert-status">{{ text(card.status_label, "참고") }}</span>
    </div>
    <p class="big-text">{{ text(card.summary, "KNIA 기준, 법률 근거, 보험 대응 관점에서 추가 확인할 내용을 정리했습니다.") }}</p>

    <div class="expert-panels">
      <section class="expert-panel">
        <h3>{{ text(card.legal?.title, "법률 검토 포인트") }}</h3>
        <p>{{ text(card.legal?.summary, "사고 사실과 관련 법령을 함께 확인해야 합니다.") }}</p>
        <p v-if="text(card.legal?.fault_range_label)" class="fault-range">{{ text(card.legal?.fault_range_label) }}</p>
        <ul v-if="card.legal?.points?.length" class="check-list">
          <li v-for="item in card.legal.points" :key="item">{{ text(item) }}</li>
        </ul>
      </section>

      <section class="expert-panel">
        <h3>{{ text(card.insurance?.title, "보험 대응 포인트") }}</h3>
        <p>{{ text(card.insurance?.summary, "보험사에는 확인된 사고 사실과 증거 중심으로 설명하는 것이 좋습니다.") }}</p>
        <ul v-if="card.insurance?.steps?.length" class="check-list">
          <li v-for="item in card.insurance.steps" :key="item">{{ text(item) }}</li>
        </ul>
        <div v-if="card.insurance?.documents?.length" class="chips">
          <span class="chip" v-for="item in card.insurance.documents" :key="item">{{ text(item) }}</span>
        </div>
      </section>
    </div>

    <section v-if="card.basis?.length" class="expert-basis">
      <h3>확인한 근거</h3>
      <p v-if="card.source_summary" class="source-summary">{{ text(card.source_summary) }}</p>
      <div class="basis-list">
        <div v-for="item in card.basis" :key="`${item.family_label}-${item.title}`">
          <div class="basis-meta">
            <span>{{ text(item.family_label, "근거") }}</span>
            <span class="source-badge" :class="{ review: item.needs_original_source_review }">
              {{ text(item.source_quality_label, "출처 확인 필요") }}
            </span>
          </div>
          <strong>{{ text(item.title, "교통사고 관련 근거") }}</strong>
          <p>{{ text(item.reason, "이번 사고와 유사한 쟁점을 확인하는 데 참고할 수 있습니다.") }}</p>
          <p v-if="item.needs_original_source_review && item.source_review_note" class="source-note">
            {{ text(item.source_review_note) }}
          </p>
          <a v-if="safeUrl(item.source_url)" class="source-link" :href="safeUrl(item.source_url)" target="_blank" rel="noreferrer">
            원문 보기
          </a>
        </div>
      </div>
    </section>

    <section v-if="card.missing_items?.length" class="expert-missing">
      <h3>추가로 확인하면 좋은 사실</h3>
      <ul class="check-list">
        <li v-for="item in card.missing_items" :key="item">{{ text(item) }}</li>
      </ul>
    </section>

    <p v-if="card.notice" class="soft-warning">{{ text(card.notice) }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ card?: any }>();
const card = computed(() => props.card);

function text(value: unknown, fallback = "") {
  return sanitizeDisplayText(value, fallback);
}

function safeUrl(value: unknown) {
  const url = String(value || "").trim();
  return /^https?:\/\//i.test(url) ? url : "";
}
</script>

<style scoped>
.expert-guidance-card {
  display: grid;
  gap: 18px;
}

.expert-header {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.expert-panels,
.basis-list {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.fault-range {
  color: var(--accent-strong);
  font-size: 1.08rem;
  font-weight: 900;
}

.source-summary,
.source-note {
  color: var(--text-sub);
}

@media (max-width: 760px) {
  .expert-header {
    display: grid;
  }

  .expert-status {
    justify-self: flex-start;
  }

  .expert-panels,
  .basis-list {
    grid-template-columns: 1fr;
  }
}
</style>
