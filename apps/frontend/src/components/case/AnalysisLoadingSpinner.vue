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
  min-height: 178px;
  padding: 18px 12px;
  overflow: visible;
}

.spinner-orb {
  --progress: 0deg;
  position: relative;
  width: clamp(116px, 24vw, 146px);
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background:
      radial-gradient(circle at 50% 50%, rgba(28, 23, 20, 0.96) 0 49%, transparent 50%),
      conic-gradient(
          from 220deg,
          #c9a962 0deg,
          #d4b872 var(--progress),
          rgba(232, 223, 212, 0.10) var(--progress) 360deg
      );
  box-shadow:
      0 10px 24px rgba(0, 0, 0, 0.28),
      inset 0 0 10px rgba(201, 169, 98, 0.10);
}

.spinner-orb::before {
  content: "";
  position: absolute;
  inset: 11px;
  border-radius: 50%;
  border: 2px solid rgba(232, 223, 212, 0.08);
  border-top-color: rgba(201, 169, 98, 0.92);
  border-right-color: rgba(139, 38, 53, 0.82);
  animation: analysis-spin 1.35s linear infinite;
}

.spinner-orb::after {
  content: "";
  position: absolute;
  inset: 25px;
  border-radius: 50%;
  background: linear-gradient(145deg, rgba(37, 30, 25, 0.98), rgba(28, 23, 20, 0.98));
  border: 1px solid rgba(201, 169, 98, 0.20);
  box-shadow: inset 0 1px 0 rgba(232, 223, 212, 0.06);
}

.spinner-core {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 5px;
  place-items: center;
  max-width: 78%;
  text-align: center;
}

.spinner-core strong {
  color: var(--text-main);
  font-size: clamp(1.6rem, 4vw, 2.2rem);
  font-weight: 950;
  line-height: 1;
  letter-spacing: -0.03em;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.46);
}

.spinner-core span {
  color: var(--accent-strong);
  font-size: 0.78rem;
  font-weight: 900;
  letter-spacing: 0.02em;
  line-height: 1.2;
  white-space: nowrap;
}

.spinner-core small {
  display: none;
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
    min-height: 154px;
    padding: 14px 8px;
  }

  .spinner-orb {
    width: clamp(108px, 36vw, 132px);
  }

  .spinner-orb::before {
    inset: 10px;
    border-width: 1.5px;
  }

  .spinner-orb::after {
    inset: 23px;
  }

  .spinner-core strong {
    font-size: clamp(1.45rem, 6vw, 1.95rem);
  }

  .spinner-core span {
    font-size: 0.72rem;
  }
}
</style>
