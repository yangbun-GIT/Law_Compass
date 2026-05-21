<template>
  <li class="knia-ranking-row">
    <div class="rank-col">{{ item.rank ?? item.rank_no }}위</div>
    <RouterLink class="chart-badge" :to="localUrl">{{ text(item.chart_no) }}</RouterLink>
    <div class="title-col">
      <RouterLink class="ranking-title" :to="localUrl">{{ text(item.title) }}</RouterLink>
      <span class="source-category">{{ text(item.source_category || '전체') }} 검색순위</span>
    </div>
    <div class="count-col">
      <span class="meta-label">검색건수</span>
      <strong>{{ formatCount(item.search_count) }}</strong>
    </div>
    <div class="percent-col">
      <span class="meta-label">비율</span>
      <strong>{{ formatPercent(item.percentage) }}</strong>
    </div>
    <div class="actions-col">
      <RouterLink class="btn secondary compact" :to="localUrl">기준 보기</RouterLink>
      <a
        v-if="hasDetailUrl"
        class="btn secondary compact"
        :href="item.source_detail_url"
        target="_blank"
        rel="noopener noreferrer"
      >KNIA 원본 보기</a>
      <button v-else class="btn secondary compact" type="button" disabled title="원본 상세 링크가 아직 수집되지 않았습니다">원본 링크 없음</button>
    </div>
  </li>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { sanitizeDisplayText } from '../../utils/displaySanitizer';

const props = defineProps<{ item: any }>();

const localUrl = computed(() => props.item.local_chart_url || props.item.chart_url || `/knia/charts/${encodeURIComponent(props.item.chart_no)}?chartType=${encodeURIComponent(props.item.chart_type || '1')}`);
const hasDetailUrl = computed(() => {
  const url = String(props.item.source_detail_url || '');
  return !!url && url !== 'https://accident.knia.or.kr/ranking' && /chartNo=/.test(url);
});

function text(value: unknown) { return sanitizeDisplayText(value); }
function formatCount(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toLocaleString('ko-KR')}건` : '-';
}
function formatPercent(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(1)}%` : '-';
}
</script>


<style scoped>
.knia-ranking-row {
  display: grid;
  grid-template-columns: 56px 96px minmax(260px, 1fr) 140px 80px 220px;
  gap: 12px;
  align-items: center;
  padding: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(7, 14, 28, 0.28);
}
.knia-ranking-row:hover { background: rgba(76, 216, 255, 0.08); }
.rank-col { color: #dce9ff; font-weight: 900; }
.chart-badge {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  min-height: 34px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(76, 216, 255, 0.16);
  border: 1px solid rgba(76, 216, 255, 0.42);
  color: #9eecff;
  font-weight: 900;
  text-decoration: none;
  white-space: nowrap;
}
.title-col { display: grid; gap: 4px; min-width: 0; }
.ranking-title { color: #f3f7ff; font-weight: 850; text-decoration: none; line-height: 1.35; }
.ranking-title:hover, .chart-badge:hover { color: #ffffff; }
.source-category, .meta-label { color: #8fa3bd; font-size: 0.78rem; }
.count-col, .percent-col { display: grid; gap: 3px; }
.count-col strong, .percent-col strong { color: #f3f7ff; white-space: nowrap; }
.actions-col { display: flex; gap: 8px; justify-content: flex-end; align-items: center; }
.compact { min-height: 34px; padding: 8px 11px; font-size: 0.88rem; white-space: nowrap; }
button[disabled] { opacity: 0.48; cursor: not-allowed; }
@media (max-width: 980px) {
  .knia-ranking-row {
    grid-template-columns: 54px 90px minmax(0, 1fr);
    grid-template-areas:
      "rank badge title"
      "rank count percent"
      "actions actions actions";
  }
  .rank-col { grid-area: rank; }
  .chart-badge { grid-area: badge; }
  .title-col { grid-area: title; }
  .count-col { grid-area: count; }
  .percent-col { grid-area: percent; }
  .actions-col { grid-area: actions; justify-content: flex-start; flex-wrap: wrap; }
}
@media (max-width: 560px) {
  .knia-ranking-row { grid-template-columns: 1fr; grid-template-areas: none; }
  .rank-col, .chart-badge, .title-col, .count-col, .percent-col, .actions-col { grid-area: auto; }
  .actions-col .btn { flex: 1; justify-content: center; }
}
</style>
