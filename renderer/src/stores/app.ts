import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getHealth, type HealthResponse } from '../api/health'

export const useAppStore = defineStore('app', () => {
  const health = ref<HealthResponse | null>(null)
  const error = ref<string | null>(null)
  const loading = computed(() => health.value === null && error.value === null)

  async function checkHealth() {
    try {
      error.value = null
      health.value = await getHealth()
    } catch (err) {
      error.value = String(err)
    }
  }

  return { health, error, loading, checkHealth }
})
