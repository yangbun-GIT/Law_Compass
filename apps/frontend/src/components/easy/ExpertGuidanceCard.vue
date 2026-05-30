<template>
  <article v-if="card" class="card easy-card wide-card expert-guidance-card">
    <div class="expert-header">
      <div>
        <p class="kv">판례·KNIA·보험 기준 참고</p>
        <h2>{{ text(card.title || "전문가 관점 예상 안내") }}</h2>
      </div>
      <span class="expert-status">{{ text(card.status_label || "참고용") }}</span>
    </div>
    <p class="big-text">{{ text(card.summary) }}</p>

    <div class="expert-panels">
      <section class="expert-panel">
        <h3>{{ text(card.legal?.title || "법률 관점 예상") }}</h3>
        <p>{{ text(card.legal?.summary) }}</p>
        <p class="fault-range">{{ text(card.legal?.fault_range_label) }}</p>
        <ul v-if="card.legal?.points?.length" class="check-list">
          <li v-for="item in card.legal.points" :key="item">{{ text(item) }}</li>
        </ul>
      </section>

      <section class="expert-panel">
        <h3>{{ text(card.insurance?.title || "보험 처리 예상") }}</h3>
        <p>{{ text(card.insurance?.summary) }}</p>
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
            <span>{{ text(item.family_label) }}</span>
            <span class="source-badge" :class="{ review: item.needs_original_source_review }">
              {{ text(item.source_quality_label || "근거 출처 확인 필요") }}
            </span>
          </div>
          <strong>{{ text(item.title) }}</strong>
          <p>{{ text(item.reason) }}</p>
          <p v-if="item.needs_original_source_review && item.source_review_note" class="source-note">{{ text(item.source_review_note) }}</p>
          <a v-if="safeUrl(item.source_url)" class="source-link" :href="safeUrl(item.source_url)" target="_blank" rel="noreferrer">
            원문 보기
          </a>
        </div>
      </div>
    </section>

    <section v-if="card.missing_items?.length" class="expert-missing">
      <h3>더 확인하면 좋은 사실</h3>
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

function text(value: unknown) {
  return sanitizeDisplayText(value);
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
  border: 1px solid rgba(201, 169, 98, 0.28);
  background: linear-gradient(145deg, rgba(37, 30, 25, 0.94), rgba(28, 23, 20, 0.96));
  color: var(--text-main);
}

.expert-header {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.expert-status,
.source-badge {
  align-items: center;
  background: var(--accent-soft);
  border: 1px solid rgba(201, 169, 98, 0.40);
  border-radius: 999px;
  color: var(--accent-strong);
  display: inline-flex;
  font-size: 0.9rem;
  font-weight: 900;
  min-height: 30px;
  padding: 6px 12px;
  width: fit-content;
}

.expert-status.needs-review,
.source-badge.review {
  background: var(--warning-soft);
  border-color: rgba(215, 181, 109, 0.48);
  color: #F1D99A;
}

.expert-panels {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.expert-panel,
.expert-basis,
.expert-missing {
  background: linear-gradient(145deg, rgba(61, 51, 43, 0.92), rgba(37, 30, 25, 0.96));
  border: 1px solid rgba(201, 169, 98, 0.28);
  border-radius: 18px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.20);
  color: var(--text-main);
  min-width: 0;
  padding: 18px;
}

.expert-panel h3,
.expert-basis h3,
.expert-missing h3 {
  color: var(--text-main);
  font-size: clamp(1.05rem, 1.8vw, 1.25rem);
  font-weight: 900;
  line-height: 1.35;
  margin: 0 0 10px;
}

.expert-panel p,
.expert-basis p,
.expert-missing p {
  color: var(--text-sub);
  font-size: 0.98rem;
  line-height: 1.68;
}

.fault-range {
  background: rgba(201, 169, 98, 0.14);
  border: 1px solid rgba(201, 169, 98, 0.34);
  border-radius: 999px;
  color: var(--accent-strong);
  display: inline-flex;
  font-weight: 900;
  margin: 10px 0;
  padding: 7px 11px;
  width: fit-content;
}

.check-list {
  display: grid;
  gap: 8px;
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
}

.check-list li {
  color: var(--text-sub);
  line-height: 1.55;
  padding-left: 20px;
  position: relative;
}

.check-list li::before {
  background: var(--accent);
  border-radius: 999px;
  box-shadow: 0 0 0 3px rgba(201, 169, 98, 0.14);
  content: "";
  height: 7px;
  left: 0;
  position: absolute;
  top: 0.72em;
  width: 7px;
}

.basis-list {
  display: grid;
  gap: 12px;
}

.source-summary {
  color: var(--text-sub);
  margin-top: -4px;
}

.basis-list div {
  background: rgba(232, 223, 212, 0.065);
  border: 1px solid rgba(201, 169, 98, 0.24);
  border-radius: 16px;
  color: var(--text-main);
  display: grid;
  gap: 8px;
  padding: 15px;
}

.basis-meta {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.basis-meta > span:first-child {
  color: var(--accent-strong);
  font-weight: 900;
}

.basis-list strong {
  color: var(--text-main);
  display: block;
}

.basis-list p {
  color: var(--text-sub);
  line-height: 1.55;
  margin-bottom: 0;
}

.source-note {
  color: var(--text-sub);
  font-size: 0.9rem;
  margin-top: 8px;
}

.source-link {
  align-items: center;
  background: rgba(201, 169, 98, 0.12);
  border: 1px solid rgba(201, 169, 98, 0.34);
  border-radius: 999px;
  color: var(--accent-strong);
  display: inline-flex;
  font-weight: 900;
  margin-top: 10px;
  padding: 7px 10px;
  text-decoration: none;
}

.source-link:hover {
  border-color: rgba(201, 169, 98, 0.72);
  color: var(--paper);
}

.soft-warning {
  background: var(--warning-soft);
  border: 1px solid rgba(215, 181, 109, 0.36);
  border-radius: 16px;
  color: #F1D99A;
  font-weight: 800;
  line-height: 1.6;
  margin: 0;
  padding: 14px 16px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  background: rgba(232, 223, 212, 0.08);
  border: 1px solid rgba(201, 169, 98, 0.24);
  border-radius: 999px;
  color: var(--text-sub);
  font-size: 0.9rem;
  font-weight: 800;
  padding: 6px 10px;
}

@media (max-width: 760px) {
  .expert-header {
    display: grid;
  }

  .expert-status {
    justify-self: flex-start;
  }

  .expert-panel,
  .expert-basis,
  .expert-missing {
    padding: 15px;
  }
}
</style>
