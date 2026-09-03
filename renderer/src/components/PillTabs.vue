<script setup lang="ts">
defineProps<{
  options: { value: string; label: string }[];
  modelValue: string;
  size?: "sm" | "md";
  /** 激活态按选项索引轮换的品牌色 class（来自 utils/brand BRAND_PILL_COLORS） */
  colors?: string[];
}>();

const emit = defineEmits<{ (e: "update:modelValue", value: string): void }>();
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <button
      v-for="(o, i) in options"
      :key="o.value"
      class="rounded-full font-medium transition"
      :class="[
        size === 'sm' ? 'px-3 py-1 text-xs' : 'px-4 py-1.5 text-sm',
        o.value === modelValue
          ? colors && colors[i % colors.length]
            ? colors[i % colors.length]
            : 'bg-surface-card text-ink'
          : 'text-muted hover:bg-surface-card/60 hover:text-ink',
      ]"
      @click="emit('update:modelValue', o.value)"
    >
      {{ o.label }}
    </button>
  </div>
</template>
