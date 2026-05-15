/**
 * Должно совпадать с `app/core/pagination.py` (ALLOWED_PAGE_SIZES и default).
 */
export const PAGE_SIZE_DEFAULT = 10
export const ALLOWED_PAGE_SIZES = [10, 25, 50] as const
export type PageSize = (typeof ALLOWED_PAGE_SIZES)[number]

export function isPageSize(n: number): n is PageSize {
  return (ALLOWED_PAGE_SIZES as readonly number[]).includes(n)
}

export function parsePageSize(param: string | null): PageSize {
  const raw = Number.parseInt(param ?? '', 10)
  return isPageSize(raw) ? raw : PAGE_SIZE_DEFAULT
}

export function parsePage(param: string | null): number {
  const raw = Number.parseInt(param ?? '1', 10)
  return Number.isFinite(raw) && raw >= 1 ? raw : 1
}
