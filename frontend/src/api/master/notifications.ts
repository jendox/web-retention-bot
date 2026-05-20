import { apiFetch } from '../client'
import type { UserNotification, UserNotificationsList } from '../notifications'

export type { UserNotification, UserNotificationsList }

export async function notificationsMyListApi(params: { page: number; page_size: number }) {
  const q = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.page_size),
  })
  return apiFetch<UserNotificationsList>(`/api/master/notifications/me?${q}`)
}

export async function notificationsMarkReadApi(notificationId: string) {
  return apiFetch<UserNotification>(`/api/master/notifications/${notificationId}/read`, {
    method: 'POST',
  })
}
