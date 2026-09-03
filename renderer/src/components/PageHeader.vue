<script setup lang="ts">
import { useGoBack } from "../composables/useGoBack";

withDefaults(defineProps<{ title: string; back?: boolean }>(), {
  back: true,
});

const goBack = useGoBack();
</script>

<template>
  <header
    class="sticky top-0 z-10 flex h-14 items-center gap-3 border-b border-hairline bg-canvas/90 px-4 backdrop-blur"
  >
    <button
      v-if="back"
      class="rounded-md px-2 py-1.5 text-sm font-medium text-muted transition hover:bg-surface-card hover:text-ink"
      @click="goBack"
    >
      ← 返回
    </button>
    <h1 class="truncate text-base font-semibold">{{ title }}</h1>
    <div class="ml-auto flex items-center gap-2">
      <slot />
    </div>
  </header>
</template>
