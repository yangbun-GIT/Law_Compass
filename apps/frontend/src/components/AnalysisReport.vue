<template>
  <section class="report-grid" v-if="report">
    <article class="card hero-card">
      <p class="kv">사고 요약</p>
      <h2>{{ report.overview?.title || "교통사고 분석 리포트" }}</h2>
      <p>{{ report.overview?.summary }}</p>
      <p class="kv">시나리오: {{ report.overview?.scenario_type || "-" }}</p>
      <p class="kv" v-if="report.overview?.video_summary">{{ report.overview.video_summary }}</p>
    </article>

    <article class="card wide-card">
      <h3>적용 가능 법규</h3>
      <p>{{ report.legal_rules_card?.legal_issue_summary }}</p>
      <div class="chips">
        <span class="chip selected" v-for="rule in report.legal_rules_card?.applicable_rules || []" :key="rule">{{ rule }}</span>
      </div>
      <p class="kv">위험 플래그</p>
      <div class="chips">
        <span class="chip" v-for="flag in report.legal_rules_card?.risk_flags || []" :key="flag">{{ flag }}</span>
      </div>
    </article>

    <article class="card" v-if="report.school_zone_card?.visible">
      <h3>민식이법 / 어린이보호구역 위험</h3>
      <p>{{ report.school_zone_card?.summary }}</p>
      <p>어린이보호구역 형사 리스크 검토: {{ report.school_zone_card?.school_zone_risk ? "필요" : "추가 사실 필요" }}</p>
      <ul class="check-list">
        <li v-for="item in report.school_zone_card?.missing_facts || []" :key="item">{{ item }}</li>
      </ul>
    </article>

    <article class="card ratio-card">
      <h3>추정 과실비율</h3>
      <div class="ratio-row">
        <div>
          <span class="ratio-num">{{ report.fault_ratio_card?.my ?? "-" }}%</span>
          <p class="kv">내 과실</p>
        </div>
        <div>
          <span class="ratio-num accent">{{ report.fault_ratio_card?.other ?? "-" }}%</span>
          <p class="kv">상대 과실</p>
        </div>
      </div>
      <p>신뢰도: {{ report.fault_ratio_card?.confidence ?? "-" }}</p>
      <p>{{ report.fault_ratio_card?.basis }}</p>
      <div class="chips">
        <span class="chip selected" v-for="factor in report.fault_ratio_card?.key_factors || []" :key="factor">{{ factor }}</span>
      </div>
    </article>

    <article class="card">
      <h3>형사책임 / 신고 필요 여부</h3>
      <p>{{ report.liability_card?.reporting_required ? "신고 또는 형사 리스크 확인이 필요합니다." : "현재 입력 기준으로는 신고 필요성이 낮아 보입니다." }}</p>
      <p class="kv">위험 수준: {{ report.liability_card?.criminal_risk_level || "-" }}</p>
      <ul class="check-list">
        <li v-for="item in report.liability_card?.checklist || []" :key="item">{{ item }}</li>
      </ul>
      <p class="kv">{{ report.liability_card?.note }}</p>
    </article>

    <article class="card">
      <h3>보험 처리 예시 / 필요 서류</h3>
      <p>{{ report.insurance_card?.summary }}</p>
      <div class="chips">
        <span class="chip selected" v-for="type in report.insurance_card?.claim_type || []" :key="type">{{ type }}</span>
      </div>
      <ul class="check-list">
        <li v-for="step in report.insurance_card?.steps || []" :key="step">{{ step }}</li>
      </ul>
      <p class="kv">필요 서류</p>
      <div class="chips">
        <span class="chip" v-for="doc in report.insurance_card?.required_documents || []" :key="doc">{{ doc }}</span>
      </div>
      <p>{{ report.insurance_card?.settlement_example }}</p>
    </article>

    <article class="card">
      <h3>지금 바로 해야 할 행동</h3>
      <ul class="check-list">
        <li v-for="item in report.action_plan_card?.immediate || []" :key="item">{{ item }}</li>
        <li v-for="item in report.action_plan_card?.evidence_collection || []" :key="item">{{ item }}</li>
        <li v-for="item in report.action_plan_card?.insurance_police || []" :key="item">{{ item }}</li>
      </ul>
    </article>

    <article class="card">
      <h3>근거 신뢰도 / 추가 사실 필요</h3>
      <p>근거 품질: {{ report.evidence_card?.quality || "-" }}</p>
      <p>평균 점수: {{ report.evidence_card?.average_score ?? "-" }}</p>
      <ul class="check-list">
        <li v-for="item in report.evidence_card?.weak_points || []" :key="item">{{ item }}</li>
        <li v-for="item in combinedGaps" :key="item">{{ item }}</li>
      </ul>
    </article>

    <article class="card wide-card">
      <h3>근거 문서</h3>
      <ul class="evidence-list">
        <li v-for="ev in report.evidence_card?.items || []" :key="ev.chunk_id">
          <RouterLink :to="`/evidence/${ev.chunk_id}`"><strong>{{ ev.title || ev.chunk_id }}</strong></RouterLink>
          <p class="kv">{{ ev.source }} / {{ ev.article_no || "조문 미상" }} / score {{ Number(ev.score || 0).toFixed(3) }}</p>
          <p>{{ ev.snippet }}</p>
          <p class="kv">사용 방식: {{ ev.used_for }}</p>
          <div class="chips">
            <span class="chip" v-for="tag in ev.scenario_tags || []" :key="tag">{{ tag }}</span>
          </div>
        </li>
      </ul>
    </article>

    <article class="card wide-card">
      <h3>불확실성 / 면책</h3>
      <p>{{ report.meta?.uncertainty?.reason }}</p>
      <ul class="check-list">
        <li v-for="item in report.meta?.disclaimers || []" :key="item">{{ item }}</li>
      </ul>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ report: any }>();

const combinedGaps = computed(() => {
  const gap = props.report?.input_gap_card || {};
  return Array.from(new Set([...(gap.followup_questions || []), ...(gap.suggested_next_inputs || []), ...(gap.missing_fields || []).map((x: string) => `${x} 입력 필요`)]));
});
</script>
