import { apiFetch } from './client'

export interface HealthResponse {
  status: string
  version: string
  dataDir: string
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health')
}
