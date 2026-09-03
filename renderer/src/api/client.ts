/** 打包后渲染层从 file:// 加载、无 vite 代理，需要拼出 http 基址 */
const getBaseUrl = (): string => {
  if (import.meta.env.DEV) {
    return "/api";
  }
  const port = window.__JMCOMIC_BACKEND_PORT__ ?? 18500;
  return `http://127.0.0.1:${port}/api`;
};

/**
 * 把后端返回的相对资源路径（/api/images/...）转成可加载的绝对地址。
 * dev 下原样返回（交给 vite 代理）；打包后补上 127.0.0.1:端口基址。
 */
export function assetUrl(path: string): string {
  if (!path || import.meta.env.DEV || path.startsWith("http")) {
    return path;
  }
  const port = window.__JMCOMIC_BACKEND_PORT__ ?? 18500;
  return `http://127.0.0.1:${port}${path}`;
}

export interface ApiError extends Error {
  status: number;
  statusText: string;
  body?: unknown;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = new Error(
      `API request failed: ${response.status} ${response.statusText}`,
    ) as ApiError;
    error.status = response.status;
    error.statusText = response.statusText;
    try {
      const text = await response.text();
      try {
        error.body = JSON.parse(text);
      } catch {
        error.body = text;
      }
    } catch {
      // body 无法读取时忽略
    }
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
