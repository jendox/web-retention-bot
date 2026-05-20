import { ALLOWED_PAGE_SIZES, type PageSize } from '../../lib/pagination'

type Props = {
  page: number
  pageSize: PageSize
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: PageSize) => void
  className?: string
}

export function ListPagination({ page, pageSize, total, onPageChange, onPageSizeChange, className }: Props) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div
      className={
        className ??
        'mt-3 flex flex-col gap-3 border-t border-stone-200 bg-stone-50/50 px-1 pt-3 dark:border-stone-700 dark:bg-stone-950/30 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between'
      }
    >
      <p className="text-sm text-stone-600 dark:text-stone-400">
        Страница {page} из {totalPages}
        <span className="text-stone-400 dark:text-stone-500"> · </span>
        всего {total}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-sm text-stone-600 dark:text-stone-400">
          <span className="whitespace-nowrap">На странице</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value) as PageSize)}
            className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-stone-900 shadow-sm dark:border-stone-600 dark:bg-stone-900 dark:text-stone-100"
          >
            {ALLOWED_PAGE_SIZES.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <div className="flex gap-1">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 enabled:hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-stone-600 dark:text-stone-200 dark:enabled:hover:bg-stone-800"
          >
            Назад
          </button>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
            className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 enabled:hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-stone-600 dark:text-stone-200 dark:enabled:hover:bg-stone-800"
          >
            Вперёд
          </button>
        </div>
      </div>
    </div>
  )
}
