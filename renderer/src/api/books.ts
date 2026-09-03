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

export interface SearchResponse {
  query: string;
  page: number;
  sort: string;
  total: number;
  books: BookItem[];
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  type: string;
  total: number;
}

export interface CategoriesResponse {
  categories: Category[];
  blocks: Record<string, string[]>;
}

export interface CategoryBooksResponse {
  slug: string;
  page: number;
  sort: string;
  total: number;
  books: BookItem[];
}

export interface CommentItem {
  id: string;
  uid: string;
  name: string;
  title?: string;
  level?: string;
  content: string;
  headUrl: string;
  like?: string;
  date?: string;
  linkBookName?: string;
  linkBookId?: string;
  subComments: CommentItem[];
}

export interface CommentsResponse {
  bookId: string;
  page: number;
  total: number;
  comments: CommentItem[];
}

export interface EpsPage {
  index: number;
  name: string;
  url: string;
}

export interface EpsPagesResponse {
  bookId: string;
  epsIndex: number;
  epsId: string;
  scrambleId: number;
  pages: EpsPage[];
}

export interface ReadingProgress {
  epsIndex: number;
  pageIndex: number;
  updatedAt: number;
}

export function getIndex(page = "0"): Promise<IndexResponse> {
  return apiFetch(`/index?page=${encodeURIComponent(page)}`);
}

export function getBookDetail(bookId: string): Promise<BookDetail> {
  return apiFetch(`/books/${encodeURIComponent(bookId)}`);
}

export function searchBooks(
  q: string,
  page = 1,
  sort = "mr",
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q });
  if (page > 1) params.set("page", String(page));
  if (sort) params.set("sort", sort);
  return apiFetch(`/search?${params.toString()}`);
}

export function getCategories(): Promise<CategoriesResponse> {
  return apiFetch("/categories");
}

export function getCategoryBooks(
  slug: string,
  page = 1,
  sort = "mr",
): Promise<CategoryBooksResponse> {
  const params = new URLSearchParams();
  if (page > 1) params.set("page", String(page));
  if (sort) params.set("sort", sort);
  return apiFetch(
    `/categories/${encodeURIComponent(slug)}/books?${params.toString()}`,
  );
}

export function getBookComments(
  bookId: string,
  page = 1,
): Promise<CommentsResponse> {
  const params = new URLSearchParams();
  if (page > 1) params.set("page", String(page));
  return apiFetch(
    `/books/${encodeURIComponent(bookId)}/comments?${params.toString()}`,
  );
}

export function getEpsPages(
  bookId: string,
  epsIndex: number,
): Promise<EpsPagesResponse> {
  return apiFetch(`/books/${encodeURIComponent(bookId)}/eps/${epsIndex}/pages`);
}

export function getReadingProgress(
  bookId: string,
): Promise<{ bookId: string; progress: ReadingProgress | null }> {
  return apiFetch(`/books/${encodeURIComponent(bookId)}/progress`);
}

export function saveReadingProgress(
  bookId: string,
  epsIndex: number,
  pageIndex: number,
  title?: string,
): Promise<{ ok: boolean }> {
  return apiFetch(`/books/${encodeURIComponent(bookId)}/progress`, {
    method: "PUT",
    body: JSON.stringify({ epsIndex, pageIndex, title }),
  });
}
