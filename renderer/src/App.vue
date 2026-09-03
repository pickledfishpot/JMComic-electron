<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useAppStore } from './stores/app'

const store = useAppStore()
const { health, error, loading } = storeToRefs(store)

onMounted(() => {
  store.checkHealth()
})

const electron = window.electronAPI
</script>

<template>
  <div class="min-h-screen flex flex-col items-center justify-center p-8">
    <h1
      class="text-4xl font-bold bg-gradient-to-r from-red-400 to-yellow-400 bg-clip-text text-transparent mb-8"
    >
      JMComic
    </h1>

    <div class="bg-[#1a1a1a] rounded-xl p-6 max-w-xl w-full">
      <h2 class="text-lg font-semibold mb-4 text-[#f0f0f0]">后端状态</h2>

      <div v-if="error" class="text-red-400">{{ error }}</div>
      <div v-else-if="loading" class="text-[#feca57] animate-pulse">正在连接后端...</div>
      <div v-else class="space-y-2 text-sm text-[#f0f0f0]">
        <div class="flex justify-between">
          <span class="text-gray-400">状态</span>
          <span class="text-green-400">{{ health?.status }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-400">版本</span>
          <span>{{ health?.version }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-400">数据目录</span>
          <span class="truncate max-w-xs" :title="health?.dataDir">{{ health?.dataDir }}</span>
        </div>
      </div>
    </div>

    <p v-if="electron" class="mt-8 text-sm text-gray-500">
      Electron {{ electron.versions.electron }} · Chrome {{ electron.versions.chrome }} · Node
      {{ electron.versions.node }}
    </p>
  </div>
</template>
