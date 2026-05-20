export type InAppChannel = {
  available: boolean
  connected: boolean
  label: string
  description: string
}

export type ExternalChannel = {
  kind: string
  label: string
  description: string
  available: boolean
  connectable: boolean
  connected: boolean
  address: string | null
  connect_url: string | null
  coming_soon_label: string | null
}

export type TopicChannelPrefs = {
  email: boolean
  telegram: boolean
  sms: boolean
}

export type NotificationTopic = {
  id: string
  label: string
  description: string
  channels: TopicChannelPrefs
}

export type NotificationSettings = {
  in_app: InAppChannel
  channels: ExternalChannel[]
  topics: NotificationTopic[]
}

export type TopicChannelPrefsPatch = {
  email?: boolean
  telegram?: boolean
  sms?: boolean
}

export type NotificationSettingsPatch = {
  topics: Array<{ id: string; channels: TopicChannelPrefsPatch }>
}

export type LinkNotificationChannelIn = {
  address?: string | null
}
