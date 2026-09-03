import { apiFetch } from "./client";

export interface UserInfo {
  uid: string;
  username: string;
  title: string;
  level: string;
  coin: string;
  gender: string;
  favorites: string;
  favorites_max: string;
  exp: number;
  next_exp: number;
}

export interface LoginResponse {
  user: UserInfo;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  passwordConfirm: string;
  gender: string;
  verification: string;
}

export interface FavoritesResponse {
  total: number;
  count: number;
  books: import("./books").BookItem[];
  folders: { id: string; name: string }[];
  page: number;
  sort: string;
  folderId: string;
}

export interface HistoryItem {
  bookId: string;
  title: string;
  epsIndex: number;
  pageIndex: number;
  updatedAt: number;
}

export interface HistoryResponse {
  total: number;
  items: HistoryItem[];
  page: number;
  pageSize: number;
}

export function login(
  username: string,
  password: string,
): Promise<LoginResponse> {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return apiFetch("/auth/logout", { method: "POST" });
}

export function getMe(): Promise<{ user: UserInfo | null }> {
  return apiFetch("/auth/me");
}

export function getCaptchaUrl(): string {
  return `/api/auth/captcha?t=${Date.now()}`;
}

export function register(
  payload: RegisterPayload,
): Promise<{ ok: boolean; message: string }> {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFavorites(
  page = 1,
  sort = "mr",
  folderId = "0",
): Promise<FavoritesResponse> {
  const params = new URLSearchParams({ page: String(page), sort, folderId });
  return apiFetch(`/favorites?${params.toString()}`);
}

export function toggleFavorite(
  bookId: string,
): Promise<{ ok: boolean; message: string }> {
  return apiFetch("/favorites", {
    method: "POST",
    body: JSON.stringify({ bookId }),
  });
}

export function addFavoriteFolder(
  name: string,
): Promise<{ ok: boolean; message: string }> {
  return apiFetch("/favorites/folders", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function deleteFavoriteFolder(
  folderId: string,
): Promise<{ ok: boolean; message: string }> {
  return apiFetch(`/favorites/folders/${encodeURIComponent(folderId)}`, {
    method: "DELETE",
  });
}

export function getHistory(page = 1, pageSize = 50): Promise<HistoryResponse> {
  const params = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
  });
  return apiFetch(`/history?${params.toString()}`);
}

export function removeHistory(bookId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/history/${encodeURIComponent(bookId)}`, {
    method: "DELETE",
  });
}
