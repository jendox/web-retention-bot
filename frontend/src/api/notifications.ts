import { apiFetch } from './client'

export type UserNotification = {
  id: string
  event_type: string
  title: string
  body: string
  link_url: string | null
  read_at: string | null
  created_at: string
}

export type UserNotificationsList = {
  items: UserNotification[]
  total: number
  page: number
  page_size: number
  unread_count: number
}

export async function notificationsMyListApi(params: { page: number; page_size: number }) {
  const q = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.page_size),
  })
  return apiFetch<UserNotificationsList>(`/api/notifications/me?${q}`)
}

export async function notificationsMarkReadApi(notificationId: string) {
  return apiFetch<UserNotification>(`/api/notifications/${notificationId}/read`, {
    method: 'POST',
  })
}
