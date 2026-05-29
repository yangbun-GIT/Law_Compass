<template>
  <div class="mobile-demo-frame-preview">
    <div class="frame-canvas-wrap" v-if="frame">
      <img :src="frame.previewUrl" alt="샘플링된 영상 프레임" />
      <div
        v-for="(object, index) in objects"
        :key="`${frame.frameIndex}-${index}`"
        class="bbox"
        :style="bboxStyle(object)"
      >
        <span>{{ labelFor(object) }}</span>
      </div>
    </div>
    <p v-else class="muted">분석을 실행하면 샘플 프레임과 객체 후보 박스가 표시됩니다.</p>
  </div>
</template>

<script setup lang="ts">
import type { MlKitDetectedObject } from "../../types/mlkit";
import type { SampledVideoFrame } from "../../services/mobileMlkitDemo";

const props = defineProps<{
  frame?: SampledVideoFrame | null;
  objects?: MlKitDetectedObject[];
}>();

function labelFor(object: MlKitDetectedObject) {
  return object.labels?.[0]?.text || "unknown_object";
}

function bboxStyle(object: MlKitDetectedObject) {
  if (!props.frame) return {};
  const box = object.boundingBox;
  return {
    left: `${(box.left / props.frame.width) * 100}%`,
    top: `${(box.top / props.frame.height) * 100}%`,
    width: `${(box.width / props.frame.width) * 100}%`,
    height: `${(box.height / props.frame.height) * 100}%`,
  };
}
</script>

