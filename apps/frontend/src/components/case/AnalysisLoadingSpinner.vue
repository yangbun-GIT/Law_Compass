<template>
  <div class="analysis-loading-spinner" role="status" aria-live="polite">
    <div
      class="spinner-orb"
      :style="{ '--progress': `${safePercent * 3.6}deg` }"
      aria-hidden="true"
    >
      <div class="spinner-core">
        <strong>{{ safePercent }}%</strong>
        <span>{{ label }}</span>
        <small>{{ message }}</small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    percent?: number;
    label?: string;
    message?: string;
  }>(),
  {
    percent: 0,
    label: "분석 중",
    message: "사고 정보를 정리하고 있습니다.",
  },
);

const safePercent = computed(() => {
  const value = Number(props.percent || 0);
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
});
</script>

<style scoped>
.analysis-loading-spinner {
  display: grid;
  place-items: center;
  min-height: 280px;
  padding: 28px 16px;
}

.spinner-orb {
  --progress: 0deg;
  position: relative;
  width: min(260px, 72vw);
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at 50% 50%, rgba(28, 23, 20, 0.96) 0 45%, transparent 46%),
    conic-gradient(from 220deg, #c9a962 0deg, #d4b872 var(--progress), rgba(232, 223, 212, 0.10) var(--progress) 360deg);
  box-shadow:
    0 24px 70px rgba(0, 0, 0, 0.42),
    inset 0 0 26px rgba(201, 169, 98, 0.16);
}

.spinner-orb::before {
  content: "";
  position: absolute;
  inset: 13px;
  border-radius: 50%;
  border: 10px solid rgba(232, 223, 212, 0.08);
  border-top-color: rgba(201, 169, 98, 0.92);
  border-right-color: rgba(139, 38, 53, 0.86);
  animation: analysis-spin 1.35s linear infinite;
}

.spinner-orb::after {
  content: "";
  position: absolute;
  inset: 42px;
  border-radius: 50%;
  background: linear-gradient(145deg, rgba(37, 30, 25, 0.98), rgba(28, 23, 20, 0.98));
  border: 1px solid rgba(201, 169, 98, 0.22);
  box-shadow: inset 0 1px 0 rgba(232, 223, 212, 0.06);
}

.spinner-core {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 5px;
  place-items: center;
  text-align: center;
}

.spinner-core strong {
  color: var(--text-main);
  font-size: clamp(2.4rem, 8vw, 4.2rem);
  font-weight: 950;
  line-height: 1;
  letter-spacing: -0.04em;
  text-shadow: 0 2px 16px rgba(0, 0, 0, 0.52);
}

.spinner-core span {
  color: var(--accent-strong);
  font-weight: 900;
  letter-spacing: 0.08em;
}

.spinner-core small {
  max-width: 160px;
  color: var(--text-sub);
  line-height: 1.35;
}

@keyframes analysis-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinner-orb::before {
    animation: none;
  }
}

@media (max-width: 520px) {
  .analysis-loading-spinner {
    min-height: 230px;
  }

  .spinner-orb {
    width: min(220px, 74vw);
  }
}
</style>
