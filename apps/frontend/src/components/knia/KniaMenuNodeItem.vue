<script setup lang="ts">
import { ref } from 'vue';
const props = defineProps<{ node: any }>();
const open = ref((props.node.children || []).length < 3);
</script>
<template>
  <div class="knia-tree-node">
    <button class="tree-node-head" type="button" @click="open = !open">
      <span>{{ node.label }}</span>
      <small>{{ node.accident_party_label }}</small>
    </button>
    <div class="tree-node-actions">
      <RouterLink v-if="node.chart_no" :to="`/knia/charts/${encodeURIComponent(node.chart_no)}`">기준 보기</RouterLink>
      <a v-if="node.source_url" :href="node.source_url" target="_blank" rel="noreferrer">원문 보기</a>
    </div>
    <div v-if="open && node.children?.length" class="tree-node-children">
      <KniaMenuNodeItem v-for="child in node.children" :key="child.id" :node="child" />
    </div>
  </div>
</template>
