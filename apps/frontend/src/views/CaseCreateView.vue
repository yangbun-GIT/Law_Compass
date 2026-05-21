<template>
  <section class="card case-create-card">
    <p class="eyebrow">새 사고 케이스</p>
    <h2>사고 내용을 입력해 주세요</h2>
    <p class="kv">제목과 기본 설명만 입력해도 시작할 수 있습니다. 자세한 사고 정보와 영상은 다음 단계에서 보완합니다.</p>

    <div v-if="draftApplied" class="soft-warning">
      AI가 채팅 내용을 바탕으로 입력 초안을 만들었습니다. 틀린 부분이 있으면 편하게 수정해 주세요.
    </div>

    <label>케이스 제목
      <input v-model="title" placeholder="예: 정차 중 후미추돌 사고" />
    </label>
    <label>기본 사고 설명
      <textarea v-model="description" rows="5" placeholder="예: 신호대기 중 정차해 있던 중 뒤 차량이 후미를 추돌했습니다. 목 통증이 있습니다." />
    </label>

    <div class="form-grid">
      <label>분석 모드
        <select v-model="analysisMode">
          <option value="quick_summary">빠른 요약</option>
          <option value="fault-focused">과실비율 중심</option>
          <option value="criminal-liability-focused">형사책임 중심</option>
          <option value="insurance-focused">보험/대응 중심</option>
        </select>
      </label>
      <label>사고 유형
        <select v-model="facts.accident_type">
          <option value="rear_end_collision">후미추돌</option>
          <option value="intersection_collision">교차로 충돌</option>
          <option value="lane_change_collision">차선변경 충돌</option>
          <option value="pedestrian_crosswalk_accident">보행자 사고</option>
          <option value="parking_or_stopped_vehicle_accident">주차/정차 중 사고</option>
          <option value="general_collision">기타</option>
        </select>
      </label>
    </div>

    <div class="chips" v-if="keywords.length">
      <span v-for="keyword in keywords" :key="keyword" class="chip selected">{{ keyword }}</span>
    </div>

    <div class="btn-row">
      <button class="btn" :disabled="loading || !title.trim()" @click="create">
        {{ loading ? "생성 중..." : "케이스 생성 후 사고 입력으로 이동" }}
      </button>
      <RouterLink class="btn secondary" to="/">목록으로</RouterLink>
    </div>
    <p v-if="message" :class="ok ? 'msg-ok' : 'msg-error'">{{ message }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { api, type AccidentFacts } from "../api/client";

const DRAFT_KEY = "lawcompass:draftCase";
const router = useRouter();
const title = ref("정차 중 후미추돌 사고");
const description = ref("신호대기 중 정차해 있던 중 뒤 차량이 후미를 추돌했습니다. 블랙박스 영상이 있습니다.");
const analysisMode = ref("quick_summary");
const keywords = ref<string[]>(["후미추돌", "블랙박스", "과실비율"]);
const facts = reactive<AccidentFacts>({ accident_type: "rear_end_collision", stopped: true, signal_state: "unknown", injury: null });
const loading = ref(false);
const message = ref("");
const ok = ref(true);
const draftApplied = ref(false);

onMounted(() => {
  const raw = localStorage.getItem(DRAFT_KEY);
  if (!raw) return;
  try {
    const draft = JSON.parse(raw);
    title.value = draft.title || title.value;
    description.value = draft.description_text || description.value;
    analysisMode.value = draft.analysis_mode || analysisMode.value;
    keywords.value = Array.isArray(draft.selected_keywords) ? draft.selected_keywords : keywords.value;
    Object.assign(facts, draft.structured_facts || {});
    draftApplied.value = true;
  } catch {
    localStorage.removeItem(DRAFT_KEY);
  }
});

async function create() {
  loading.value = true;
  message.value = "";
  ok.value = true;
  try {
    const data = await api.createCase({
      title: title.value.trim(),
      description_text: description.value.trim(),
      structured_facts: { ...facts },
      selected_keywords: keywords.value,
      analysis_mode: analysisMode.value
    });
    localStorage.removeItem(DRAFT_KEY);
    await router.push(`/cases/${data.case.id}/wizard`);
  } catch (e: any) {
    message.value = e.message || "케이스 생성에 실패했습니다.";
    ok.value = false;
  } finally {
    loading.value = false;
  }
}
</script>
