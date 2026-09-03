<script setup lang="ts">
defineProps<{
  cover: string;
  title: string;
  author?: string;
}>();

defineEmits<{ (e: "open"): void }>();
</script>

<template>
  <div
    class="group cursor-pointer overflow-hidden rounded-lg bg-surface-card transition hover:-translate-y-0.5 hover:shadow-lg"
    @click="$emit('open')"
  >
    <div class="relative aspect-[3/4] overflow-hidden bg-surface-strong">
      <img
        :src="cover"
        :alt="title"
        loading="lazy"
        class="h-full w-full object-cover transition group-hover:opacity-90"
      />
      <slot name="badge" />
    </div>
    <div class="p-3">
      <p class="line-clamp-2 text-sm font-medium leading-snug">{{ title }}</p>
      <slot name="meta">
        <p v-if="author" class="mt-1 truncate text-xs text-muted">
          {{ author }}
        </p>
      </slot>
    </div>
  </div>
</template>
