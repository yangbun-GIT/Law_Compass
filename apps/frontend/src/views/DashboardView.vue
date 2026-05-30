<template>
  <section class="dashboard">
    <article class="card hero-card dashboard-hero">
      <div class="hero-copy">
        <p class="eyebrow">LawCompass 로컬 MVP</p>
        <h2>내 교통사고 케이스</h2>
        <p class="hero-text">
          케이스 생성부터 사고 정보 입력, 영상 업로드, AI 분석, 쉬운 리포트와 근거 문서 확인까지 한 화면 흐름으로 이어갑니다.
        </p>
        <div class="btn-row hero-actions">
          <RouterLink class="btn" to="/cases/new">새 케이스 만들기</RouterLink>
          <RouterLink class="btn secondary" to="/knia/ranking">검색순위 보기</RouterLink>
        </div>
      </div>

      <aside class="workflow-panel" aria-label="진행 흐름">
        <span class="entry-kicker">진행 흐름</span>
        <ol>
          <li>사고 케이스 생성</li>
          <li>상황 입력 및 영상 업로드</li>
          <li>AI 분석 요청</li>
          <li>리포트와 근거 확인</li>
        </ol>
      </aside>
    </article>

    <div class="dashboard-knia-grid">
      <RouterLink class="knia-entry-card" to="/knia/ranking">
        <span class="entry-kicker">검색순위 보기</span>
        <strong>많이 검색된 사고유형</strong>
        <small>KNIA 과실비율정보포털에서 많이 조회된 기준을 봅니다.</small>
      </RouterLink>
    </div>

    <article class="card case-list-card">
      <div class="section-head">
        <div>
          <p class="eyebrow">Cases</p>
          <h3>최근 케이스</h3>
        </div>
        <RouterLink class="btn secondary" to="/cases/new">추가</RouterLink>
      </div>

      <p v-if="loading" class="kv">케이스 목록을 불러오는 중입니다.</p>
      <p v-else-if="error" class="msg-error">{{ error }}</p>

      <ul v-else-if="items.length" class="list-reset case-list">
        <li v-for="item in items" :key="item.id" class="case-row">
          <div class="case-main">
            <div class="case-title-row">
              <strong>{{ item.title }}</strong>
              <span class="badge" :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span>
            </div>
            <p class="kv">생성: {{ formatDate(item.created_at) }}</p>
            <p>{{ item.description_text || "사고 설명이 아직 입력되지 않았습니다." }}</p>
          </div>
          <div class="btn-row case-actions">
            <RouterLink class="btn secondary" :to="`/cases/${item.id}/wizard`">입력 이어가기</RouterLink>
            <RouterLink class="btn secondary" :to="`/cases/${item.id}/result`">결과 보기</RouterLink>
          </div>
        </li>
      </ul>

      <div v-else class="empty-state">
        <strong>등록된 케이스가 없습니다.</strong>
        <p class="kv">첫 케이스를 만들고 사고 상황을 입력하면 분석 흐름을 시작할 수 있습니다.</p>
        <RouterLink class="btn" to="/cases/new">첫 케이스 만들기</RouterLink>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, formatApiError, type CaseItem } from "../api/client";

const items = ref<CaseItem[]>([]);
const loading = ref(false);
const error = ref("");

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" });
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    draft: "작성 중",
    ready: "분석 가능",
    analyzing: "분석 중",
    completed: "분석 완료",
    failed: "실패"
  };
  return labels[status] || status;
}

function statusClass(status: string) {
  if (status === "completed") return "ok";
  if (status === "failed") return "fail";
  return "warn";
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const data = await api.listCases();
    items.value = data.items;
  } catch (err) {
    error.value = formatApiError(err, "케이스 목록을 불러오지 못했습니다.");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.dashboard {
  display: grid;
  gap: 18px;
}

.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
  gap: 18px;
  align-items: stretch;
  min-height: 260px;
  padding: 22px;
  background:
      radial-gradient(620px 340px at 4% 0%, rgba(139, 38, 53, 0.16), transparent 62%),
      linear-gradient(135deg, rgba(232, 223, 212, 0.06), rgba(201, 169, 98, 0.05)),
      rgba(37, 30, 25, 0.88);
  border-color: rgba(201, 169, 98, 0.38);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.hero-copy h2 {
  margin: 0 0 12px;
  font-size: 2.75rem;
  line-height: 1.12;
  color: #f3e9dc;
}

.hero-text {
  max-width: 720px;
  margin: 0;
  color: rgba(232, 223, 212, 0.84);
  font-size: 1.05rem;
  line-height: 1.7;
}

.hero-actions {
  margin-top: 24px;
}

.workflow-panel {
  display: grid;
  align-content: center;
  gap: 12px;
  padding: 18px;
  border-radius: 12px;
  background: rgba(61, 51, 43, 0.62);
  border: 1px solid rgba(201, 169, 98, 0.32);
}

.workflow-panel ol {
  display: grid;
  gap: 10px;
  margin: 0;
  padding-left: 20px;
}

.workflow-panel li {
  color: rgba(232, 223, 212, 0.9);
  line-height: 1.58;
}

.dashboard-knia-grid {
  display: grid;
  grid-template-columns: minmax(260px, 760px);
  gap: 16px;
  align-items: stretch;
}

.knia-entry-card {
  display: grid;
  gap: 8px;
  min-height: 142px;
  padding: 22px;
  border-radius: 12px;
  text-decoration: none;
  color: #f3e9dc;
  background:
      linear-gradient(135deg, rgba(201, 169, 98, 0.16), rgba(61, 51, 43, 0.7)),
      rgba(37, 30, 25, 0.86);
  border: 1px solid rgba(201, 169, 98, 0.38);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.22);
  transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.knia-entry-card.secondary-entry {
  background:
      linear-gradient(135deg, rgba(139, 38, 53, 0.16), rgba(61, 51, 43, 0.68)),
      rgba(37, 30, 25, 0.86);
  border-color: rgba(201, 169, 98, 0.34);
}

.knia-entry-card:hover {
  transform: translateY(-2px);
  border-color: rgba(212, 184, 114, 0.68);
  box-shadow: 0 22px 54px rgba(0, 0, 0, 0.32);
}

.entry-kicker {
  color: #d4b872;
  font-size: 0.86rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.knia-entry-card strong {
  font-size: 1.12rem;
  color: #f7ead8;
}

.knia-entry-card small {
  color: rgba(232, 223, 212, 0.76);
  line-height: 1.55;
}

.case-list-card {
  padding: 18px;
}

.section-head,
.case-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-head {
  margin-bottom: 10px;
}

.section-head h3,
.section-head .eyebrow {
  margin: 0;
}

.case-list {
  display: grid;
  gap: 10px;
}

.case-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: center;
  padding: 16px;
  border: 1px solid rgba(201, 169, 98, 0.24);
  background: rgba(28, 23, 20, 0.38);
  border-radius: 12px;
}

.case-main {
  min-width: 0;
}

.case-main p:last-child {
  margin-bottom: 0;
  line-height: 1.55;
}

.case-actions {
  justify-content: flex-end;
}

.empty-state {
  display: grid;
  justify-items: start;
  gap: 10px;
  padding: 24px;
  border: 1px dashed rgba(201, 169, 98, 0.32);
  border-radius: 12px;
  background: rgba(61, 51, 43, 0.38);
}

@media (max-width: 900px) {
  .dashboard-hero,
  .dashboard-knia-grid,
  .case-row {
    grid-template-columns: 1fr;
  }

  .dashboard-hero {
    min-height: 0;
    padding: 18px;
  }

  .hero-copy h2 {
    font-size: 2rem;
  }

  .case-actions {
    justify-content: flex-start;
  }

  .case-actions .btn {
    flex: 1 1 180px;
  }
}
</style>
