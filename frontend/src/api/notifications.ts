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

export type NotificationCabinet = 'client' | 'master'
