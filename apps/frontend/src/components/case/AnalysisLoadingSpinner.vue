vue
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
  min-height: 160px;
  padding: 8px 12px 16px;
}

.spinner-orb {
  --progress: 0deg;
  position: relative;
  width: clamp(118px, 24vw, 150px);
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background:
      radial-gradient(circle at 50% 50%, rgba(28, 23, 20, 0.96) 0 47%, transparent 48%),
      conic-gradient(
          from 220deg,
          #c9a962 0deg,
          #d4b872 var(--progress),
          rgba(232, 223, 212, 0.10) var(--progress) 360deg
      );
  box-shadow:
      0 12px 28px rgba(0, 0, 0, 0.30),
      inset 0 0 12px rgba(201, 169, 98, 0.12);
}

.spinner-orb::before {
  content: "";
  position: absolute;
  inset: 10px;
  border-radius: 50%;
  border: 3px solid rgba(232, 223, 212, 0.08);
  border-top-color: rgba(201, 169, 98, 0.92);
  border-right-color: rgba(139, 38, 53, 0.82);
  animation: analysis-spin 1.35s linear infinite;
}

.spinner-orb::after {
  content: "";
  position: absolute;
  inset: 27px;
  border-radius: 50%;
  background: linear-gradient(145deg, rgba(37, 30, 25, 0.98), rgba(28, 23, 20, 0.98));
  border: 1px solid rgba(201, 169, 98, 0.20);
  box-shadow: inset 0 1px 0 rgba(232, 223, 212, 0.06);
}

.spinner-core {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 4px;
  place-items: center;
  max-width: 72%;
  text-align: center;
}

.spinner-core strong {
  color: var(--text-main);
  font-size: clamp(1.45rem, 4.2vw, 2.15rem);
  font-weight: 950;
  line-height: 1;
  letter-spacing: -0.03em;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.46);
}

.spinner-core span {
  color: var(--accent-strong);
  font-size: 0.78rem;
  font-weight: 900;
  letter-spacing: 0.04em;
  line-height: 1.2;
  white-space: nowrap;
}

.spinner-core small {
  max-width: 108px;
  color: var(--text-sub);
  font-size: 0.68rem;
  line-height: 1.3;
  word-break: keep-all;
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
    min-height: 140px;
    padding: 6px 8px 12px;
  }

  .spinner-orb {
    width: clamp(106px, 38vw, 132px);
  }

  .spinner-orb::before {
    inset: 9px;
    border-width: 3px;
  }

  .spinner-orb::after {
    inset: 23px;
  }

  .spinner-core strong {
    font-size: clamp(1.35rem, 6vw, 1.9rem);
  }

  .spinner-core span {
    font-size: 0.74rem;
  }

  .spinner-core small {
    display: none;
  }
}
</style>

