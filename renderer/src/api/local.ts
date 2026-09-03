import { apiFetch } from "./client";

export interface LocalEps {
  index: number;
  name: string;
  pageCount: number;
}

export interface LocalBook {
  id: string;
  title: string;
  isZip: boolean;
  path: string;
  eps: LocalEps[];
  pageCount: number;
}

export interface LocalBookList {
  count: number;
  books: LocalBook[];
}

export interface LocalPage {
  index: number;
  name: string;
  url: string;
}

export interface LocalPages {
  bookId: string;
  epsIndex: number;
  pages: LocalPage[];
}

export interface LocalReadingProgress {
  epsIndex: number;
  pageIndex: number;
  updatedAt: number;
}

export function scanLocal(): Promise<LocalBookList> {
  return apiFetch("/local/scan", { method: "POST" });
}

export function listLocal(): Promise<LocalBookList> {
  return apiFetch("/local/books");
}

export function getLocalBook(bookId: string): Promise<LocalBook> {
  return apiFetch(`/local/books/${encodeURIComponent(bookId)}`);
}

export function getLocalPages(
  bookId: string,
  epsIndex: number,
): Promise<LocalPages> {
  return apiFetch(
    `/local/books/${encodeURIComponent(bookId)}/eps/${epsIndex}/pages`,
  );
}

export function getLocalProgress(
  bookId: string,
): Promise<{ bookId: string; progress: LocalReadingProgress | null }> {
  return apiFetch(`/local/books/${encodeURIComponent(bookId)}/progress`);
}

export function saveLocalProgress(
  bookId: string,
  epsIndex: number,
  pageIndex: number,
  title?: string,
): Promise<{ ok: boolean }> {
  return apiFetch(`/local/books/${encodeURIComponent(bookId)}/progress`, {
    method: "PUT",
    body: JSON.stringify({ epsIndex, pageIndex, title }),
  });
}
