<template>
  <div class="mobile-demo-table-wrap">
    <table class="mobile-demo-table">
      <thead>
        <tr>
          <th>시간</th>
          <th>라벨</th>
          <th>신뢰도</th>
          <th>bbox</th>
          <th>track_id</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, index) in rows" :key="index">
          <td>{{ item.frame_time_sec.toFixed(2) }}s</td>
          <td>{{ item.metadata.label }}</td>
          <td>{{ Math.round(item.confidence * 100) }}%</td>
          <td>{{ item.bbox.map((value) => value.toFixed(2)).join(", ") }}</td>
          <td>{{ item.track_id ?? "-" }}</td>
        </tr>
        <tr v-if="!rows.length">
          <td colspan="5">아직 감지 결과가 없습니다.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { ClientPreObservation } from "../../types/mobileObservations";

defineProps<{
  rows: ClientPreObservation[];
}>();
</script>

