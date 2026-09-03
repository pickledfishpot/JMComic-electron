<script setup lang="ts">
defineProps<{
  type: "loading" | "empty" | "error";
  message?: string;
}>();

const emit = defineEmits<{ (e: "retry"): void }>();
</script>

<template>
  <div class="py-20 text-center">
    <template v-if="type === 'loading'">
      <p class="text-muted">{{ message || "加载中..." }}</p>
    </template>
    <template v-else-if="type === 'empty'">
      <p class="text-muted">{{ message || "暂无内容" }}</p>
      <slot />
    </template>
    <template v-else>
      <p class="text-error">{{ message || "加载失败" }}</p>
      <slot />
      <button
        class="mt-4 rounded-md bg-surface-card px-4 py-2 text-sm font-medium text-ink transition hover:bg-surface-strong"
        @click="emit('retry')"
      >
        重试
      </button>
    </template>
  </div>
</template>
