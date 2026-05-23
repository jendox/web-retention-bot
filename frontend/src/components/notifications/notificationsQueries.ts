import { useQuery } from '@tanstack/react-query'

import type { NotificationCabinet } from '../../api/notifications'
import * as clientNotifications from '../../api/client/notifications'
import * as masterNotifications from '../../api/master/notifications'
import { parsePage, parsePageSize } from '../../lib/pagination'

export function useNotificationsUnreadCount(enabled: boolean, cabinet: NotificationCabinet) {
  const q = useQuery({
    queryKey: ['notifications', 'me', 'unread-badge', cabinet],
    queryFn: () => {
      const api = cabinet === 'client' ? clientNotifications : masterNotifications
      return api.notificationsMyListApi({ page: 1, page_size: 10 })
    },
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
