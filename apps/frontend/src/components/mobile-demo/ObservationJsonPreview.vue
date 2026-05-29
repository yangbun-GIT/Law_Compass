<template>
  <pre class="mobile-demo-json">{{ formatted }}</pre>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ClientPreObservationsPayload } from "../../types/mobileObservations";

const props = defineProps<{
  payload?: ClientPreObservationsPayload | null;
}>();

const formatted = computed(() => JSON.stringify(props.payload ?? { status: "waiting_for_analysis" }, null, 2));
</script>

