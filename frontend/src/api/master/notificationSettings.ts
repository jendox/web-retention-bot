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

export async function masterNotificationSettingsGetApi() {
  return apiFetch<NotificationSettings>('/api/master/notification-settings/me')
}

export async function masterNotificationSettingsPatchApi(payload: NotificationSettingsPatch) {
  return apiFetch<NotificationSettings>('/api/master/notification-settings/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function masterNotificationChannelLinkApi(channelKind: string, payload: LinkNotificationChannelIn) {
  return apiFetch<NotificationSettings>(`/api/master/notification-settings/channels/${channelKind}/link`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function masterNotificationChannelUnlinkApi(channelKind: string) {
  return apiFetch<NotificationSettings>(`/api/master/notification-settings/channels/${channelKind}`, {
    method: 'DELETE',
  })
}
