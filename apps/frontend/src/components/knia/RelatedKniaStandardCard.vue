<template>
  <article class="card easy-card knia-card" v-if="standard">
    <p class="eyebrow">과실비율정보포털 기준</p>
    <h2>{{ text(standard.title || standard.chart_title || "이 사고와 비슷한 과실비율 인정기준") }}</h2>
    <div class="chips">
      <span class="chip selected" v-if="standard.chart_no">기준번호 {{ text(standard.chart_no) }}</span>
      <span class="chip" v-if="partyLabel">대분류: {{ partyLabel }}</span>
      <span class="chip" v-if="standard.base_fault_label">{{ text(standard.base_fault_label) }}</span>
    </div>

    <h3>{{ text(standard.chart_title || standard.title || "유사 사고 기준") }}</h3>
    <section class="knia-section">
      <h4>기준 요약</h4>
      <div class="knia-paragraphs">
        <p v-for="paragraph in summaryParagraphs" :key="paragraph">{{ paragraph }}</p>
      </div>
    </section>

    <details class="inline-details" v-if="similarityParagraphs.length">
      <summary>이 기준을 함께 보는 이유</summary>
      <div class="knia-paragraphs">
        <p v-for="paragraph in similarityParagraphs" :key="paragraph">{{ paragraph }}</p>
      </div>
    </details>

    <div class="btn-row">
      <a v-if="standard.source_url" class="btn secondary" :href="standard.source_url" target="_blank" rel="noopener noreferrer">KNIA 원문 기준 보기</a>
      <a v-if="standard.video_url" class="btn secondary" :href="standard.video_url" target="_blank" rel="noopener noreferrer">KNIA 관련 영상 보기</a>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { formatKniaBody, sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ standard: any }>();

const partyLabel = computed(() => resolveAccidentPartyLabel({
  accident_party_label: props.standard?.accident_party_label || props.standard?.major_party_label,
  accident_party_type: props.standard?.major_party_type || props.standard?.accident_party_type || props.standard?.party_type,
  chart_no: props.standard?.chart_no || props.standard?.subchart_no,
}));
const summaryParagraphs = computed(() => formatKniaBody(props.standard?.easy_explanation || props.standard?.summary || props.standard?.body));
const similarityParagraphs = computed(() => formatKniaBody(props.standard?.why_similar || props.standard?.match_reason));

function resolveAccidentPartyLabel(input: { accident_party_label?: unknown; accident_party_type?: unknown; chart_no?: unknown }) {
  const existing = sanitizeDisplayText(input.accident_party_label, "");
  if (existing && existing !== "확인이 필요합니다.") return existing;

  const type = String(input.accident_party_type || "").trim();
  const byType: Record<string, string> = {
    car_vs_car: "차대차 사고",
    vehicle_vs_vehicle: "차대차 사고",
    car_vs_person: "차대보행자 사고",
    pedestrian_crosswalk_accident: "차대보행자 사고",
    car_vs_bicycle: "차대자전거 사고",
    bicycle_collision: "차대자전거 사고",
    single_vehicle: "단독 사고",
    single_vehicle_accident: "단독 사고",
    object_collision: "물체/시설물 사고",
    car_vs_object: "물체/시설물 사고",
  };
  if (byType[type]) return byType[type];

  const chartNo = sanitizeDisplayText(input.chart_no, "");
  if (chartNo.startsWith("차")) return "차대차 사고";
  if (chartNo.startsWith("보")) return "차대보행자 사고";
  if (chartNo.startsWith("자") || chartNo.startsWith("거")) return "차대자전거 사고";
  if (chartNo.startsWith("단")) return "단독 사고";
  if (chartNo.startsWith("기") || chartNo.startsWith("물")) return "물체/시설물 사고";
  return "확인이 필요합니다.";
}

function text(value: unknown) {
  return sanitizeDisplayText(value);
}
</script>
