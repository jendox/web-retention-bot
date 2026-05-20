import { apiFetch } from '../client'
import type {
  LinkNotificationChannelIn,
  NotificationSettings,
  NotificationSettingsPatch,
} from '../notificationSettings'

export type {
  ExternalChannel,
  InAppChannel,
  LinkNotificationChannelIn,
  NotificationSettings,
  NotificationSettingsPatch,
  NotificationTopic,
  TopicChannelPrefs,
} from '../notificationSettings'

export async function clientNotificationSettingsGetApi() {
  return apiFetch<NotificationSettings>('/api/client/notification-settings/me')
}

export async function clientNotificationSettingsPatchApi(payload: NotificationSettingsPatch) {
  return apiFetch<NotificationSettings>('/api/client/notification-settings/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function clientNotificationChannelLinkApi(channelKind: string, payload: LinkNotificationChannelIn) {
  return apiFetch<NotificationSettings>(`/api/client/notification-settings/channels/${channelKind}/link`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function clientNotificationChannelUnlinkApi(channelKind: string) {
  return apiFetch<NotificationSettings>(`/api/client/notification-settings/channels/${channelKind}`, {
    method: 'DELETE',
  })
}
