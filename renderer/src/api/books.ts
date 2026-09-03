import { apiFetch } from "./client";

export interface BookItem {
  id: string;
  title: string;
  author?: string | string[];
  authorList: string[];
  tags: string[];
  categories: string[];
  coverUrl: string;
  likes?: string;
  views?: string;
}

export interface BookEps {
  index: number;
  epsId: string;
  name?: string;
  sort: number;
}

export interface BookDetail {
  id: string;
  title: string;
  description?: string;
  authorList: string[];
  tags: string[];
  categories: string[];
  coverUrl: string;
  likes?: string;
  views?: string;
  commentTotal: number;
  isFavorite?: boolean;
  eps: BookEps[];
}

export interface IndexResponse {
  page: string;
  sections: Record<string, BookItem[]>;
}

export function getIndex(page = "0"): Promise<IndexResponse> {
  return apiFetch(`/index?page=${encodeURIComponent(page)}`);
}

export function getBookDetail(bookId: string): Promise<BookDetail> {
  return apiFetch(`/books/${encodeURIComponent(bookId)}`);
}
