<script setup lang="ts">
import KniaVideoLinkCard from "./KniaVideoLinkCard.vue";

type AnyRecord = Record<string, any>;

defineProps<{
  video?: AnyRecord | null;
}>();
</script>

<template>
  <KniaVideoLinkCard :video="video" />
</template>
