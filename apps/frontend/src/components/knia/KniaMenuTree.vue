<script setup lang="ts">
import KniaMenuNodeItem from './KniaMenuNodeItem.vue';
defineProps<{ nodes: any[] }>();
</script>
<template>
  <div class="knia-tree">
    <KniaMenuNodeItem v-for="node in nodes" :key="node.id" :node="node" />
  </div>
</template>
