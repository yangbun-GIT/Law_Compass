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
          <option value="legal-focused">법률/판례 근거 중심</option>
          <option value="criminal-liability-focused">형사책임 중심</option>
          <option value="insurance-focused">보험/대응 중심</option>
          <option value="evidence-review">증거 보강 중심</option>
        </select>
      </label>
      <label>사고 대분류
        <select v-model="facts.accident_party_type">
          <option value="">영상/설명 기준으로 판단</option>
          <option value="car_vs_car">차 대 차</option>
          <option value="car_vs_person">차 대 사람</option>
          <option value="car_vs_bicycle">차 대 자전거/이륜</option>
          <option value="car_vs_object">차 대 물체/시설물</option>
          <option value="single_vehicle">단독 사고</option>
        </select>
      </label>
      <label>사고 유형
        <select v-model="facts.accident_type">
          <option value="">영상/설명 기준으로 판단</option>
          <option value="rear_end_collision">후방추돌/앞뒤 충돌</option>
          <option value="right_turn_front_stop">우회전 중 앞차 정차 추돌</option>
          <option value="intersection_collision">교차로 충돌</option>
          <option value="intersection_signal_violation">교차로 신호 쟁점</option>
          <option value="lane_change_collision">차선변경/진로변경 충돌</option>
          <option value="centerline_obstacle_collision">중앙선/장애물 회피 중 대향 충돌</option>
          <option value="stopped_vehicle_collision">정차 차량/무등화 차량 추돌</option>
          <option value="non_contact_trigger">비접촉 유발/급정지 유발</option>
          <option value="pedestrian_crosswalk_accident">보행자 사고</option>
          <option value="bicycle_collision">자전거 사고</option>
          <option value="object_collision">물체/시설물 충돌</option>
          <option value="single_vehicle_accident">단독 사고</option>
          <option value="general_collision">기타/불명확</option>
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
import { api, formatApiError, type AccidentFacts } from "../api/client";

const DRAFT_KEY = "lawcompass:draftCase";
const router = useRouter();
const title = ref("");
const description = ref("");
const analysisMode = ref("quick_summary");
const keywords = ref<string[]>(["블랙박스", "과실비율"]);
const facts = reactive<AccidentFacts>({ accident_type: "", accident_party_type: "", injury: null });
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
    message.value = formatApiError(e, "케이스 생성에 실패했습니다.");
    ok.value = false;
  } finally {
    loading.value = false;
  }
}
</script>
