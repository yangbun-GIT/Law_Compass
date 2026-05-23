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
      <div class="basis-list">
        <div v-for="item in card.basis" :key="`${item.family_label}-${item.title}`">
          <span>{{ text(item.family_label) }}</span>
          <strong>{{ text(item.title) }}</strong>
          <p>{{ text(item.reason) }}</p>
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

.expert-status {
  background: rgba(84, 226, 243, 0.14);
  border: 1px solid rgba(84, 226, 243, 0.42);
  border-radius: 999px;
  color: #7ae8f4;
  flex: 0 0 auto;
  font-weight: 800;
  padding: 9px 13px;
}

.expert-panels {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.expert-panel,
.expert-basis,
.expert-missing {
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  min-width: 0;
  padding: 16px;
}

.expert-panel h3,
.expert-basis h3,
.expert-missing h3 {
  margin-top: 0;
}

.fault-range {
  color: #7ae8f4;
  font-size: 1.15rem;
  font-weight: 900;
}

.basis-list {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.basis-list div {
  background: rgba(9, 16, 28, 0.36);
  border: 1px solid rgba(255, 255, 255, 0.11);
  border-radius: 10px;
  padding: 12px;
}

.basis-list span {
  color: #6de3ef;
  display: block;
  font-size: 0.88rem;
  font-weight: 800;
}

.basis-list strong {
  color: #f1f7ff;
  display: block;
  margin-top: 4px;
}

.basis-list p {
  color: #cbd7e8;
  line-height: 1.55;
  margin-bottom: 0;
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
