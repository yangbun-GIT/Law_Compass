<template>
  <div
    class="knia-fault-ratio-bar"
    :class="[`is-${variant}`, { 'is-empty': !normalizedRatio }]"
  >
    <p v-if="!normalizedRatio" class="knia-fault-ratio-empty">
      {{ fallbackText }}
    </p>

    <template v-else>
      <div class="knia-fault-ratio-labels" aria-hidden="true">
        <span class="knia-fault-ratio-party is-left">{{ leftLabel }}</span>
        <span class="knia-fault-ratio-party is-right">{{ rightLabel }}</span>
      </div>

      <div class="knia-fault-ratio-track-shell">
        <div
          class="knia-fault-ratio-track"
          role="img"
          :aria-label="computedAriaLabel"
        >
          <div
            class="knia-fault-ratio-segment knia-fault-ratio-a"
            :class="{
              'is-zero': normalizedRatio.left <= 0,
              'is-full': normalizedRatio.left >= 100,
              'is-tiny': leftTiny,
            }"
            :style="{ flexBasis: `${normalizedRatio.left}%` }"
          >
            <span class="knia-fault-ratio-percent">
              {{ leftInsideLabel }} {{ normalizedRatio.left }}%
            </span>
          </div>

          <div
            class="knia-fault-ratio-segment knia-fault-ratio-b"
            :class="{
              'is-zero': normalizedRatio.right <= 0,
              'is-full': normalizedRatio.right >= 100,
              'is-tiny': rightTiny,
            }"
            :style="{ flexBasis: `${normalizedRatio.right}%` }"
          >
            <span class="knia-fault-ratio-percent">
              {{ rightInsideLabel }} {{ normalizedRatio.right }}%
            </span>
          </div>
        </div>

        <div
          class="knia-fault-ratio-marker"
          :style="{ left: splitMarkerLeft }"
          aria-hidden="true"
        >
          <span>{{ normalizedRatio.left }}:{{ normalizedRatio.right }}</span>
        </div>
      </div>

      <div class="knia-fault-ratio-readout" aria-hidden="true">
        <span>{{ leftLabel }} {{ normalizedRatio.left }}%</span>
        <span>{{ rightLabel }} {{ normalizedRatio.right }}%</span>
      </div>

      <p v-if="caption" class="knia-fault-ratio-caption">
        {{ caption }}
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

type RatioValue = number | string | null | undefined;
type RatioVariant = "knia" | "user" | "compact";

type NormalizedRatio = {
  left: number;
  right: number;
};

const props = withDefaults(
  defineProps<{
    a?: RatioValue;
    b?: RatioValue;
    left?: RatioValue;
    right?: RatioValue;
    leftLabel?: string;
    rightLabel?: string;
    caption?: string;
    variant?: RatioVariant;
    ariaLabel?: string;
    fallbackText?: string;
  }>(),
  {
    leftLabel: "\uC67C\uCABD A",
    rightLabel: "\uC624\uB978\uCABD B",
    caption: "",
    variant: "knia",
    ariaLabel: "",
    fallbackText: "\uACFC\uC2E4\uBE44\uC728 \uD655\uC778 \uD544\uC694",
  },
);

const normalizedRatio = computed<NormalizedRatio | null>(() => {
  return normalizeRatioPair(firstRatioValue(props.a, props.left), firstRatioValue(props.b, props.right));
});

const leftTiny = computed(() => {
  const ratio = normalizedRatio.value;
  return Boolean(ratio && ratio.left > 0 && ratio.left < 14);
});

const rightTiny = computed(() => {
  const ratio = normalizedRatio.value;
  return Boolean(ratio && ratio.right > 0 && ratio.right < 14);
});

const splitMarkerLeft = computed(() => {
  const ratio = normalizedRatio.value;
  if (!ratio) return "50%";
  if (ratio.left <= 0) return "clamp(32px, 0%, calc(100% - 32px))";
  if (ratio.left >= 100) return "clamp(32px, 100%, calc(100% - 32px))";
  return `clamp(32px, ${ratio.left}%, calc(100% - 32px))`;
});

const computedAriaLabel = computed(() => {
  const ratio = normalizedRatio.value;
  if (!ratio) return props.fallbackText;
  return props.ariaLabel || `${props.leftLabel} ${ratio.left}%, ${props.rightLabel} ${ratio.right}%`;
});

const leftInsideLabel = computed(() => props.variant === "user" ? "\uB0B4" : shortSegmentLabel(props.leftLabel, "A"));
const rightInsideLabel = computed(() => props.variant === "user" ? "\uC0C1\uB300" : shortSegmentLabel(props.rightLabel, "B"));

function firstRatioValue(...values: RatioValue[]) {
  for (const value of values) {
    const parsed = parseRatioValue(value);
    if (parsed !== null) return parsed;
  }
  return null;
}

function parseRatioValue(value: RatioValue) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;

  const raw = String(value).trim();
  if (!raw) return null;
  const match = raw.match(/-?\d+(?:\.\d+)?/);
  if (!match) return null;

  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeRatioPair(leftValue: number | null, rightValue: number | null): NormalizedRatio | null {
  let left = leftValue;
  let right = rightValue;

  if (left === null && right === null) return null;
  if (left !== null && right === null) right = 100 - left;
  if (left === null && right !== null) left = 100 - right;
  if (left === null || right === null) return null;

  const clampedLeft = clampPercent(left);
  const clampedRight = clampPercent(right);
  const total = clampedLeft + clampedRight;

  if (total <= 0) return null;
  if (total === 100) return { left: clampedLeft, right: clampedRight };

  const nextLeft = Math.round((clampedLeft / total) * 100);
  return { left: nextLeft, right: 100 - nextLeft };
}

function clampPercent(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function shortSegmentLabel(label: string, fallback: string) {
  const value = String(label || "").trim();
  if (!value) return fallback;
  const upper = value.toUpperCase();
  if (upper.includes("A")) return "A";
  if (upper.includes("B")) return "B";
  return fallback;
}
</script>

<style scoped>
.knia-fault-ratio-bar {
  display: grid;
  gap: 10px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.knia-fault-ratio-labels,
.knia-fault-ratio-readout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.knia-fault-ratio-party {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid rgba(201, 169, 98, 0.42);
  background: rgba(28, 23, 20, 0.52);
  color: var(--text-main, #e8dfd4);
  font-size: 0.82rem;
  font-weight: 900;
  white-space: nowrap;
}

.knia-fault-ratio-party.is-left {
  color: #ffe2e4;
  border-color: rgba(184, 75, 85, 0.58);
  background: rgba(139, 38, 53, 0.24);
}

.knia-fault-ratio-party.is-right {
  color: var(--accent-foreground, #1c1714);
  border-color: rgba(201, 169, 98, 0.58);
  background: rgba(201, 169, 98, 0.78);
}

.knia-fault-ratio-track-shell {
  position: relative;
  width: 100%;
  min-width: 0;
}

.knia-fault-ratio-track {
  display: flex;
  width: 100%;
  min-width: 0;
  height: 56px;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid rgba(201, 169, 98, 0.40);
  background:
    linear-gradient(180deg, rgba(232, 223, 212, 0.08), transparent 40%),
    rgba(28, 23, 20, 0.70);
  box-shadow:
    inset 0 1px 0 rgba(232, 223, 212, 0.10),
    0 14px 30px rgba(0, 0, 0, 0.24);
}

.knia-fault-ratio-segment {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 0;
  height: 100%;
  box-sizing: border-box;
  overflow: hidden;
  flex-grow: 0;
  flex-shrink: 0;
  color: var(--text-main, #e8dfd4);
  font-size: 0.94rem;
  font-weight: 950;
  line-height: 1;
  white-space: nowrap;
  transition:
    flex-basis 0.22s ease,
    opacity 0.18s ease;
}

.knia-fault-ratio-segment::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.16), transparent 42%, rgba(0, 0, 0, 0.16));
}

.knia-fault-ratio-a {
  justify-content: flex-start;
  padding-left: 18px;
  padding-right: 8px;
  background:
    linear-gradient(90deg, rgba(116, 30, 43, 0.98), rgba(178, 73, 82, 0.96));
  color: #fff2f2;
}

.knia-fault-ratio-b {
  justify-content: flex-end;
  padding-left: 8px;
  padding-right: 18px;
  background:
    linear-gradient(90deg, var(--accent-dark, #b8953f), var(--accent-strong, #d4b872));
  color: var(--accent-foreground, #1c1714);
}

.knia-fault-ratio-percent {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 5ch;
  max-width: 100%;
  padding: 0 6px;
  overflow: hidden;
  text-align: center;
  text-overflow: ellipsis;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.24);
}

.knia-fault-ratio-segment.is-tiny .knia-fault-ratio-percent,
.knia-fault-ratio-segment.is-zero .knia-fault-ratio-percent {
  display: none;
}

.knia-fault-ratio-segment.is-zero {
  min-width: 0;
  flex-basis: 0% !important;
  width: 0 !important;
  padding: 0 !important;
  opacity: 0;
}

.knia-fault-ratio-segment.is-full {
  flex-basis: 100% !important;
}

.knia-fault-ratio-marker {
  position: absolute;
  top: 50%;
  z-index: 3;
  display: grid;
  place-items: center;
  width: 56px;
  height: 36px;
  transform: translate(-50%, -50%);
  clip-path: polygon(24% 0, 76% 0, 100% 50%, 76% 100%, 24% 100%, 0 50%);
  background: linear-gradient(180deg, #f4d780 0%, #d7ae4f 58%, #b98d31 100%);
  color: #2b2119;
  border: 1px solid rgba(255, 238, 188, 0.72);
  box-shadow:
    0 10px 20px rgba(0, 0, 0, 0.26),
    inset 0 1px 0 rgba(255, 255, 255, 0.40);
  font-size: 0.76rem;
  font-weight: 950;
  line-height: 1;
  pointer-events: none;
}

.knia-fault-ratio-marker span,
.knia-fault-ratio-readout span {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
}

.knia-fault-ratio-readout {
  color: var(--text-sub, #bfaf9d);
  font-size: 0.92rem;
  font-weight: 900;
  line-height: 1.35;
}

.knia-fault-ratio-readout span {
  min-width: 7ch;
  text-align: center;
}

.knia-fault-ratio-caption,
.knia-fault-ratio-empty {
  margin: 0;
  color: var(--text-sub, #bfaf9d);
  font-size: 0.94rem;
  font-weight: 800;
  line-height: 1.55;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.knia-fault-ratio-empty {
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px dashed rgba(201, 169, 98, 0.30);
  background: rgba(28, 23, 20, 0.38);
}

.knia-fault-ratio-bar.is-compact {
  gap: 8px;
}

.knia-fault-ratio-bar.is-compact .knia-fault-ratio-track {
  height: 48px;
}

@media (max-width: 640px) {
  .knia-fault-ratio-party {
    min-height: 26px;
    padding: 3px 10px;
    font-size: 0.78rem;
  }

  .knia-fault-ratio-track {
    height: 50px;
    border-radius: 14px;
  }

  .knia-fault-ratio-segment {
    font-size: 0.84rem;
  }

  .knia-fault-ratio-a {
    padding-left: 12px;
    padding-right: 6px;
  }

  .knia-fault-ratio-b {
    padding-left: 6px;
    padding-right: 12px;
  }

  .knia-fault-ratio-marker {
    width: 48px;
    height: 32px;
    font-size: 0.7rem;
  }

  .knia-fault-ratio-readout {
    font-size: 0.86rem;
  }
}
</style>
