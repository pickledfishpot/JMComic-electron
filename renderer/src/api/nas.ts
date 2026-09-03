import { apiFetch } from "./client";

export interface NasConfig {
  id: string;
  name: string;
  protocol: string;
  address: string;
  port: number;
  username: string;
  password: string;
  remotePath: string;
  createdAt: number;
  updatedAt: number;
}

export interface NasConfigInput {
  name: string;
  protocol: string;
  address: string;
  port: number;
  username: string;
  password: string;
  remote_path: string;
}

export function listNas(): Promise<{ configs: NasConfig[] }> {
  return apiFetch("/nas");
}

export function addNas(input: NasConfigInput): Promise<NasConfig> {
  return apiFetch("/nas", { method: "POST", body: JSON.stringify(input) });
}

export function updateNas(
  id: string,
  input: Partial<NasConfigInput>,
): Promise<NasConfig> {
  return apiFetch(`/nas/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function deleteNas(id: string): Promise<{ ok: boolean }> {
  return apiFetch(`/nas/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function testNas(id: string): Promise<{ ok: boolean; error?: string }> {
  return apiFetch(`/nas/${encodeURIComponent(id)}/test`, { method: "POST" });
}

export function uploadToNas(
  id: string,
  bookId: string,
  bookTitle: string,
): Promise<{ ok: boolean; files: number }> {
  return apiFetch(`/nas/${encodeURIComponent(id)}/upload`, {
    method: "POST",
    body: JSON.stringify({ bookId, bookTitle }),
  });
}
