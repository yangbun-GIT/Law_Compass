<template>
  <li class="knia-ranking-row">
    <div class="rank-col">{{ rankLabel }}</div>
    <RouterLink class="chart-badge" :to="localUrl">{{ text(item.chart_no) }}</RouterLink>
    <div class="title-col">
      <RouterLink class="ranking-title" :to="localUrl">{{ text(item.title) }}</RouterLink>
      <span class="source-category">{{ rankingPartyLabel }}</span>
      <span class="detail-chip" :class="{ ready: item.has_detail }">
        {{ item.has_detail ? '상세 수집 완료' : '상세 수집 필요' }}
      </span>
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
const rankLabel = computed(() => {
  const rank = Number(props.item.rank ?? props.item.rank_no);
  return Number.isFinite(rank) && rank > 0 ? `${rank}위` : '기준';
});
const rankingPartyLabel = computed(() => {
  const existing = text(props.item.accident_party_label);
  if (existing && existing !== '확인이 필요합니다.' && existing !== '사고유형 확인 필요') return existing;
  const party = String(props.item.accident_party_type || '');
  const chartNo = String(props.item.chart_no || '');
  if (party === 'car_vs_bicycle' || chartNo.startsWith('자') || chartNo.startsWith('거')) return '차대자전거 사고';
  if (party === 'car_vs_person' || chartNo.startsWith('보')) return '차대보행자 사고';
  if (party === 'car_vs_car' || chartNo.startsWith('차')) return '차대차 사고';
  if (party === 'single_vehicle' || chartNo.startsWith('단')) return '단독 사고';
  return text(props.item.source_category || '전체');
});
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
  padding: 16px;
  border: 1px solid rgba(201, 169, 98, 0.22);
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(37, 30, 25, 0.92), rgba(28, 23, 20, 0.96));
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.20);
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}
.knia-ranking-row:hover {
  transform: translateY(-1px);
  background: linear-gradient(145deg, rgba(61, 51, 43, 0.92), rgba(37, 30, 25, 0.98));
  border-color: rgba(201, 169, 98, 0.44);
}
.rank-col { color: var(--text-main); font-weight: 950; }
.chart-badge {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  min-height: 34px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(201, 169, 98, 0.14);
  border: 1px solid rgba(201, 169, 98, 0.46);
  color: var(--accent-strong);
  font-weight: 900;
  text-decoration: none;
  white-space: nowrap;
}
.title-col { display: grid; gap: 4px; min-width: 0; }
.ranking-title { color: var(--text-main); font-weight: 900; text-decoration: none; line-height: 1.45; overflow-wrap: anywhere; }
.ranking-title:hover, .chart-badge:hover { color: var(--accent-strong); }
.source-category, .meta-label { color: rgba(191, 175, 157, 0.86); font-size: 0.78rem; }
.detail-chip {
  align-self: start;
  border: 1px solid rgba(215, 181, 109, 0.34);
  border-radius: 999px;
  color: #ead08f;
  font-size: 0.76rem;
  font-weight: 900;
  justify-self: start;
  padding: 4px 8px;
}
.detail-chip.ready {
  border-color: rgba(167, 193, 122, 0.42);
  color: #d7e7b7;
}
.count-col, .percent-col { display: grid; gap: 3px; }
.count-col strong, .percent-col strong { color: var(--text-main); white-space: nowrap; font-size: 1rem; }
.actions-col { display: flex; gap: 8px; justify-content: flex-end; align-items: center; }
.compact { min-height: 38px; padding: 9px 12px; font-size: 0.9rem; white-space: nowrap; }
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
  .knia-ranking-row { grid-template-columns: 1fr; grid-template-areas: none; gap: 12px; padding: 16px; }
  .rank-col, .chart-badge, .title-col, .count-col, .percent-col, .actions-col { grid-area: auto; }
  .actions-col { display: grid; grid-template-columns: 1fr; width: 100%; }
  .actions-col .btn { width: 100%; justify-content: center; min-height: 46px; }
  .chart-badge { justify-self: start; }
  .count-col,
  .percent-col {
    grid-template-columns: auto 1fr;
    align-items: baseline;
    gap: 8px;
  }
}
</style>
