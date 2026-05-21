<template>
  <div class="party-tabs" role="tablist" aria-label="KNIA 검색순위 분류 선택">
    <button
      v-for="item in tabs"
      :key="item.value"
      type="button"
      :class="['party-tab', { active: modelValue === item.value }]"
      @click="$emit('update:modelValue', item.value)"
    >
      <strong>{{ item.label }}</strong>
      <span>{{ item.help }}</span>
    </button>
  </div>
</template>
<script setup lang="ts">
defineProps<{ modelValue: string }>();
defineEmits<{ 'update:modelValue': [value: string] }>();
const tabs = [
  { value: 'all', label: '전체', help: '원본 전체 순위' },
  { value: 'car_vs_car', label: '차대차', help: '차량끼리 사고' },
  { value: 'car_vs_person', label: '차대사람', help: '보행자 사고' },
  { value: 'car_vs_bicycle', label: '차대자전거', help: '자전거 사고' }
];
</script>
