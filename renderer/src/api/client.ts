const getBaseUrl = (): string => {
  if (import.meta.env.DEV) {
    return '/api'
  }
  const port =
    (window as unknown as { __JMCOMIC_BACKEND_PORT__?: number }).__JMCOMIC_BACKEND_PORT__ ?? 18500
  return `http://127.0.0.1:${port}/api`
}

export interface ApiError extends Error {
  status: number
  statusText: string
  body?: unknown
}

export async function apiFetch<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getBaseUrl()
  const url = `${baseUrl}${path}`
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = new Error(
      `API request failed: ${response.status} ${response.statusText}`,
    ) as ApiError
    error.status = response.status
    error.statusText = response.statusText
    try {
      const text = await response.text()
      try {
        error.body = JSON.parse(text)
      } catch {
        error.body = text
      }
    } catch {
      // body 无法读取时忽略
    }
    throw error
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
