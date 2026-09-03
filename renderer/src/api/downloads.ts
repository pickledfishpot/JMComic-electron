import { apiFetch } from "./client";

export type DownloadStatus =
  "pending" | "downloading" | "paused" | "done" | "error";

export interface DownloadTask {
  id: string;
  bookId: string;
  bookTitle: string;
  epsIndex: number;
  epsId: string;
  epsName: string;
  status: DownloadStatus;
  totalPages: number;
  donePages: number;
  error: string;
  createdAt: number;
  updatedAt: number;
}

export function listDownloads(): Promise<{ tasks: DownloadTask[] }> {
  return apiFetch("/downloads");
}

export function startDownload(
  bookId: string,
  epsIndexes?: number[],
  bookTitle?: string,
): Promise<{ taskIds: string[] }> {
  return apiFetch("/downloads/start", {
    method: "POST",
    body: JSON.stringify({ bookId, epsIndexes, bookTitle }),
  });
}

function taskAction(id: string, action: string): Promise<{ ok: boolean }> {
  return apiFetch(`/downloads/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
  });
}

export const pauseDownload = (id: string) => taskAction(id, "pause");
export const resumeDownload = (id: string) => taskAction(id, "resume");
export const retryDownload = (id: string) => taskAction(id, "retry");

export function removeDownload(id: string): Promise<{ ok: boolean }> {
  return apiFetch(`/downloads/${encodeURIComponent(id)}`, { method: "DELETE" });
}
