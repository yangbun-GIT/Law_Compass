<template>
  <article class="card detail-card">
    <button class="detail-toggle" @click="open = !open">{{ open ? "자세한 분석 정보 접기" : "자세한 분석 정보 보기" }}</button>
    <div v-if="open" class="detail-body">
      <h3>근거 요약</h3>
      <ul class="check-list" v-if="safeSummaries.length">
        <li v-for="item in safeSummaries" :key="item">{{ item }}</li>
      </ul>
      <p v-else>일반 화면에서는 내부 식별자와 모델 정보가 표시되지 않습니다.</p>
      <div v-if="debugEnabled" class="developer-debug">
        <h3>개발자 전용 정보</h3>
        <p class="soft-warning">이 영역은 URL에 debug=1을 붙였거나 개발자 모드 환경변수를 켠 경우에만 표시됩니다.</p>
        <pre>{{ safeDebugText }}</pre>
      </div>
    </div>
  </article>
</template>
<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { removeTechnicalFields, sanitizeDisplayText } from "../../utils/displaySanitizer";
const props = defineProps<{ details: any }>();
const open = ref(false);
const route = useRoute();
const debugEnabled = computed(() => route.query.debug === "1" || import.meta.env.VITE_ENABLE_DEBUG_REPORT === "true");
const safeSummaries = computed(() => (props.details?.evidence_summaries || []).map((x: unknown) => sanitizeDisplayText(x)).filter(Boolean));
const safeDebugText = computed(() => JSON.stringify(removeTechnicalFields(props.details || {}), null, 2));
</script>
