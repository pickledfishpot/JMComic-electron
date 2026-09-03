<script setup lang="ts">
defineProps<{
  options: { value: string; label: string }[];
  modelValue: string;
  size?: "sm" | "md";
}>();

const emit = defineEmits<{ (e: "update:modelValue", value: string): void }>();
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <button
      v-for="o in options"
      :key="o.value"
      class="rounded-full font-medium transition"
      :class="[
        size === 'sm' ? 'px-3 py-1 text-xs' : 'px-4 py-1.5 text-sm',
        o.value === modelValue
          ? 'bg-surface-card text-ink'
          : 'text-muted hover:bg-surface-card/60 hover:text-ink',
      ]"
      @click="emit('update:modelValue', o.value)"
    >
      {{ o.label }}
    </button>
  </div>
</template>
