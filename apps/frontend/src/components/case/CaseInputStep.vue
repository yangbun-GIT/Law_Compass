<template>
  <article class="card easy-card">
    <div class="step-head">
      <span class="step-index">1</span>
      <div>
        <h2>사고 상황 입력</h2>
        <p class="kv">분석에 필요한 기본 사실관계와 키워드를 먼저 저장합니다.</p>
      </div>
    </div>

    <label>사고 설명
      <textarea
        :value="descriptionText"
        rows="5"
        placeholder="예: 신호대기 중 정차해 있는데 뒤 차량이 추돌했습니다. 목이 아픕니다."
        @input="updateDescription"
      />
    </label>

    <div class="form-grid">
      <label>분석 모드
        <select :value="analysisMode" @change="updateAnalysisMode">
          <option value="quick_summary">빠른 요약</option>
          <option value="rear-end-focused">후방추돌</option>
          <option value="intersection-signal-focused">교차로 신호위반</option>
          <option value="lane-change-focused">차선변경</option>
          <option value="school-zone-focused">어린이보호구역</option>
        </select>
      </label>
      <label>사고 유형
        <select :value="facts.accident_type" @change="updateFact('accident_type', eventValue($event))">
          <option value="rear_end_collision">후방추돌</option>
          <option value="intersection_collision">교차로 충돌</option>
          <option value="lane_change_collision">차선변경 충돌</option>
          <option value="pedestrian_crosswalk_accident">보행자 사고</option>
          <option value="parking_or_stopped_vehicle_accident">주차/정차 중 사고</option>
          <option value="general_collision">기타</option>
        </select>
      </label>
      <label>상대 차량 행동
        <input :value="facts.opponent_behavior || ''" placeholder="예: 뒤에서 추돌" @input="updateFact('opponent_behavior', eventValue($event).trim())" />
      </label>
      <label>차량 손상 정도
        <input :value="facts.damage_level || ''" placeholder="예: 범퍼 파손" @input="updateFact('damage_level', eventValue($event).trim())" />
      </label>
    </div>

    <div class="chips">
      <label class="chip"><input type="checkbox" :checked="!!facts.stopped" @change="updateFact('stopped', eventChecked($event))" /> 정차 중</label>
      <label class="chip"><input type="checkbox" :checked="!!facts.sudden_brake" @change="updateFact('sudden_brake', eventChecked($event))" /> 급정거</label>
      <label class="chip"><input type="checkbox" :checked="!!facts.injury" @change="updateFact('injury', eventChecked($event))" /> 다친 사람 있음</label>
      <label class="chip"><input type="checkbox" :checked="!!facts.school_zone" @change="updateFact('school_zone', eventChecked($event))" /> 어린이보호구역</label>
      <label class="chip"><input type="checkbox" :checked="!!facts.opponent_signal_violation" @change="updateFact('opponent_signal_violation', eventChecked($event))" /> 상대 신호위반</label>
      <label class="chip"><input type="checkbox" :checked="!!facts.lane_change" @change="updateFact('lane_change', eventChecked($event))" /> 차선변경</label>
    </div>

    <div class="chips">
      <button
        v-for="kw in keywordPool"
        :key="kw"
        class="chip"
        :class="{ selected: selectedKeywords.includes(kw) }"
        type="button"
        @click="$emit('toggleKeyword', kw)"
      >
        {{ kw }}
      </button>
    </div>

    <button class="btn" :disabled="!!busy" @click="$emit('save')">
      {{ busy === "save" ? "저장 중..." : "입력 저장" }}
    </button>
  </article>
</template>

<script setup lang="ts">
import type { AccidentFacts } from "../../api/client";

const props = defineProps<{
  descriptionText: string;
  analysisMode: string;
  facts: AccidentFacts;
  selectedKeywords: string[];
  keywordPool: string[];
  busy: string;
}>();

const emit = defineEmits<{
  (event: "update:descriptionText", value: string): void;
  (event: "update:analysisMode", value: string): void;
  (event: "update:facts", value: AccidentFacts): void;
  (event: "toggleKeyword", value: string): void;
  (event: "save"): void;
}>();

function eventValue(event: Event) {
  return (event.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement).value;
}

function eventChecked(event: Event) {
  return (event.target as HTMLInputElement).checked;
}

function updateDescription(event: Event) {
  emit("update:descriptionText", eventValue(event).trim());
}

function updateAnalysisMode(event: Event) {
  emit("update:analysisMode", eventValue(event));
}

function updateFact(key: keyof AccidentFacts, value: AccidentFacts[keyof AccidentFacts]) {
  emit("update:facts", { ...props.facts, [key]: value });
}
</script>

<style scoped>
.step-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.step-head h2,
.step-head p {
  margin: 0;
}

.step-head h2 {
  font-size: 1.55rem;
  line-height: 1.25;
}

.step-index {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #06202a;
  background: linear-gradient(135deg, var(--accent), #a7f3d0);
  font-weight: 900;
}
</style>
