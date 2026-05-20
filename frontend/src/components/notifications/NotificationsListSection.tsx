import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { notificationsMarkReadApi, notificationsMyListApi } from '../../api/notifications'
import { ListPagination } from '../ui/ListPagination'
import { getUserFacingError } from '../../lib/apiErrors'
import { cn } from '../../lib/forms'
import { parsePage, parsePageSize, type PageSize } from '../../lib/pagination'

function formatRelativeDay(iso: string) {
  const dt = new Date(iso)
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(dt)
}

type Props = {
  page: number
  pageSize: PageSize
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: PageSize) => void
  enabled?: boolean
}

export function NotificationsListSection({
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  enabled = true,
}: Props) {
  const queryClient = useQueryClient()

  const list = useQuery({
    queryKey: ['notifications', 'me', page, pageSize],
    queryFn: () => notificationsMyListApi({ page, page_size: pageSize }),
    enabled,
  })

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsMarkReadApi(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['notifications', 'me'] }),
  })

  useEffect(() => {
    if (!list.isSuccess || !list.data) {
      return
    }
    const totalPages = Math.max(1, Math.ceil(list.data.total / pageSize))
    if (page > totalPages) {
      onPageChange(totalPages)
    }
  }, [list.isSuccess, list.data, page, pageSize, onPageChange])

  if (list.isLoading) {
    return <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем уведомления…</p>
  }

  if (list.isError) {
    return <p className="text-sm text-rose-600 dark:text-rose-300">{getUserFacingError(list.error)}</p>
  }

  const items = list.data?.items ?? []
  const total = list.data?.total ?? 0
  const unreadCount = list.data?.unread_count ?? 0

  return (
    <div className="space-y-4">
      {unreadCount > 0 ? (
        <p className="text-sm text-stone-600 dark:text-stone-400">
          Непрочитанных: <span className="font-semibold text-stone-900 dark:text-stone-100">{unreadCount}</span>
        </p>
      ) : null}

      {items.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-stone-400">Пока нет уведомлений.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((n) => (
            <li
              key={n.id}
              className={cn(
                'rounded-xl border border-stone-100 bg-white px-4 py-3 shadow-sm dark:border-stone-800 dark:bg-stone-900/80',
                n.read_at == null ? 'ring-1 ring-teal-500/25' : '',
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="font-medium text-stone-900 dark:text-stone-50">{n.title}</p>
                <time className="text-xs text-stone-500 dark:text-stone-400" dateTime={n.created_at}>
                  {formatRelativeDay(n.created_at)}
                </time>
              </div>
              <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{n.body}</p>
              {n.read_at == null ? (
                <button
                  type="button"
                  disabled={markRead.isPending}
                  onClick={() => markRead.mutate(n.id)}
                  className="mt-2 text-xs font-medium text-teal-700 hover:underline dark:text-teal-400"
                >
                  Отметить прочитанным
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {total > 0 ? (
        <ListPagination
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={onPageChange}
          onPageSizeChange={(ps) => {
            onPageSizeChange(ps)
            onPageChange(1)
          }}
        />
      ) : null}
    </div>
  )
}

/** Unread badge for nav; uses a lightweight first-page fetch. */
export function useNotificationsUnreadCount(enabled: boolean) {
  const q = useQuery({
    queryKey: ['notifications', 'me', 'unread-badge'],
    queryFn: () => notificationsMyListApi({ page: 1, page_size: 10 }),
    enabled,
    staleTime: 30_000,
  })
  return q.data?.unread_count ?? 0
}

export function parseNotificationsPage(searchParams: URLSearchParams) {
  return {
    page: parsePage(searchParams.get('page')),
    pageSize: parsePageSize(searchParams.get('page_size')),
  }
}
