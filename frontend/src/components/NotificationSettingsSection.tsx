import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  clientNotificationChannelLinkApi,
  clientNotificationChannelUnlinkApi,
  clientNotificationSettingsGetApi,
  clientNotificationSettingsPatchApi,
} from '../api/client/notificationSettings'
import {
  masterNotificationChannelLinkApi,
  masterNotificationChannelUnlinkApi,
  masterNotificationSettingsGetApi,
  masterNotificationSettingsPatchApi,
} from '../api/master/notificationSettings'
import type { ExternalChannel, NotificationSettings, TopicChannelPrefs } from '../api/notificationSettings'
import { getUserFacingError } from '../lib/apiErrors'
import { surfacePanel } from '../lib/surface'

type Cabinet = 'client' | 'master'

const channelKeys = ['email', 'telegram', 'viber', 'sms'] as const
type ChannelKey = (typeof channelKeys)[number]

const checkboxClass =
  'mt-1 h-4 w-4 rounded border-stone-300 text-teal-600 focus:ring-teal-500 disabled:opacity-40'

function apiForCabinet(cabinet: Cabinet) {
  if (cabinet === 'client') {
    return {
      get: clientNotificationSettingsGetApi,
      patch: clientNotificationSettingsPatchApi,
      link: clientNotificationChannelLinkApi,
      unlink: clientNotificationChannelUnlinkApi,
    }
  }
  return {
    get: masterNotificationSettingsGetApi,
    patch: masterNotificationSettingsPatchApi,
    link: masterNotificationChannelLinkApi,
    unlink: masterNotificationChannelUnlinkApi,
  }
}

function channelMeta(
  settings: NotificationSettings,
  key: ChannelKey,
): { label: string; available: boolean; connected: boolean; comingSoon: string | null } {
  if (key === 'email') {
    const email = settings.channels.find((c) => c.kind === 'email')
    return {
      label: email?.label ?? 'Email',
      available: true,
      connected: true,
      comingSoon: null,
    }
  }
  const ext = settings.channels.find((c) => c.kind === key)
  return {
    label: ext?.label ?? key,
    available: ext?.available ?? false,
    connected: ext?.connected ?? false,
    comingSoon: ext?.coming_soon_label,
  }
}

const BOT_CHANNELS = new Set(['telegram', 'viber'])

function ChannelConnectRow({
  channel,
  cabinet,
  onLinked,
}: {
  channel: ExternalChannel
  cabinet: Cabinet
  onLinked: () => void
}) {
  const api = apiForCabinet(cabinet)
  const [error, setError] = useState<string | null>(null)
  const isBotChannel = BOT_CHANNELS.has(channel.kind)

  const link = useMutation({
    mutationFn: () => api.link(channel.kind, {}),
    onSuccess: () => {
      setError(null)
      onLinked()
    },
    onError: (err) => setError(getUserFacingError(err)),
  })

  const unlink = useMutation({
    mutationFn: () => api.unlink(channel.kind),
    onSuccess: () => {
      setError(null)
      onLinked()
    },
    onError: (err) => setError(getUserFacingError(err)),
  })

  if (!channel.available) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-lg border border-dashed border-stone-200 px-4 py-3 dark:border-stone-700">
        <div>
          <p className="text-sm font-medium text-stone-800 dark:text-stone-200">{channel.label}</p>
          <p className="text-sm text-stone-500 dark:text-stone-400">{channel.description}</p>
        </div>
        {channel.coming_soon_label ? (
          <span className="shrink-0 rounded-full bg-stone-100 px-2.5 py-0.5 text-xs font-medium text-stone-600 dark:bg-stone-800 dark:text-stone-400">
            {channel.coming_soon_label}
          </span>
        ) : null}
      </div>
    )
  }

  if (channel.kind === 'email') {
    return (
      <div className="rounded-lg border border-stone-200 px-4 py-3 dark:border-stone-700">
        <p className="text-sm font-medium text-stone-800 dark:text-stone-200">{channel.label}</p>
        <p className="mt-0.5 text-sm text-stone-500 dark:text-stone-400">{channel.description}</p>
        {channel.address ? (
          <p className="mt-2 text-sm text-stone-700 dark:text-stone-300">{channel.address}</p>
        ) : null}
      </div>
    )
  }

  if (channel.connected) {
    const connectedLabel =
      channel.kind === 'telegram'
        ? `Chat ID ${channel.address}`
        : channel.address
    return (
      <div className="rounded-lg border border-stone-200 px-4 py-3 dark:border-stone-700">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-stone-800 dark:text-stone-200">{channel.label}</p>
            <p className="mt-0.5 text-sm text-stone-500 dark:text-stone-400">Подключено ({connectedLabel})</p>
          </div>
          <button
            type="button"
            disabled={unlink.isPending}
            onClick={() => unlink.mutate()}
            className="text-sm font-medium text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-200"
          >
            {unlink.isPending ? 'Отключаем…' : 'Отключить'}
          </button>
        </div>
        {error ? <p className="mt-2 text-sm text-rose-600 dark:text-rose-400">{error}</p> : null}
      </div>
    )
  }

  const connectUrl = channel.connect_url

  return (
    <div className="rounded-lg border border-stone-200 px-4 py-3 dark:border-stone-700">
      <p className="text-sm font-medium text-stone-800 dark:text-stone-200">{channel.label}</p>
      <p className="mt-0.5 text-sm text-stone-500 dark:text-stone-400">{channel.description}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {!connectUrl ? (
          <button
            type="button"
            disabled={link.isPending || !isBotChannel}
            onClick={() => link.mutate()}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-60"
          >
            {link.isPending ? 'Готовим ссылку…' : 'Подключить'}
          </button>
        ) : (
          <a
            href={connectUrl}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500"
          >
            {channel.kind === 'telegram' ? 'Открыть @retention_studio_bot' : 'Открыть Viber'}
          </a>
        )}
        {connectUrl ? (
          <button
            type="button"
            disabled={link.isPending}
            onClick={() => link.mutate()}
            className="rounded-lg border border-stone-200 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 dark:border-stone-600 dark:text-stone-300 dark:hover:bg-stone-800"
          >
            Новая ссылка
          </button>
        ) : null}
      </div>
      {connectUrl ? (
        <p className="mt-2 text-xs text-stone-500 dark:text-stone-400">
          В боте нажмите Start. Страница обновит статус после подключения.
        </p>
      ) : null}
      {error ? <p className="mt-2 text-sm text-rose-600 dark:text-rose-400">{error}</p> : null}
    </div>
  )
}

export function NotificationSettingsSection({ cabinet }: { cabinet: Cabinet }) {
  const queryClient = useQueryClient()
  const api = apiForCabinet(cabinet)
  const queryKey = ['notification-settings', cabinet] as const

  const settingsQuery = useQuery({
    queryKey,
    queryFn: api.get,
    retry: false,
    refetchInterval: (query) => {
      const hasPendingBot = query.state.data?.channels.some(
        (c) => BOT_CHANNELS.has(c.kind) && !c.connected && c.connect_url,
      )
      return hasPendingBot ? 3000 : false
    },
  })

  const patchSettings = useMutation({
    mutationFn: api.patch,
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data)
    },
  })

  const [patchError, setPatchError] = useState<string | null>(null)

  if (settingsQuery.isLoading) {
    return (
      <section className={surfacePanel('p-6')}>
        <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Уведомления</h2>
        <p className="mt-3 text-sm text-stone-500 dark:text-stone-400">Загрузка…</p>
      </section>
    )
  }

  if (settingsQuery.isError || !settingsQuery.data) {
    return (
      <section className={surfacePanel('p-6')}>
        <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Уведомления</h2>
        <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">
          {settingsQuery.isError ? getUserFacingError(settingsQuery.error) : 'Не удалось загрузить настройки.'}
        </p>
      </section>
    )
  }

  const settings = settingsQuery.data

  const toggleTopicChannel = (topicId: string, channelKey: ChannelKey, enabled: boolean) => {
    setPatchError(null)
    patchSettings.mutate(
      {
        topics: [
          {
            id: topicId,
            channels: { [channelKey]: enabled },
          },
        ],
      },
      { onError: (err) => setPatchError(getUserFacingError(err)) },
    )
  }

  return (
    <section className={surfacePanel('p-6')}>
      <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Уведомления</h2>
      <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">
        В приложении уведомления всегда включены. Ниже — доставка на email и мессенджеры.
      </p>

      <div className="mt-5 rounded-lg bg-stone-50 px-4 py-3 dark:bg-stone-900/50">
        <p className="text-sm font-medium text-stone-800 dark:text-stone-200">{settings.in_app.label}</p>
        <p className="text-sm text-stone-500 dark:text-stone-400">{settings.in_app.description}</p>
      </div>

      <h3 className="mt-6 text-sm font-semibold text-stone-800 dark:text-stone-200">Каналы доставки</h3>
      <div className="mt-3 space-y-3">
        {settings.channels.map((channel) => (
          <ChannelConnectRow
            key={channel.kind}
            channel={channel}
            cabinet={cabinet}
            onLinked={() => queryClient.invalidateQueries({ queryKey })}
          />
        ))}
      </div>

      <h3 className="mt-6 text-sm font-semibold text-stone-800 dark:text-stone-200">По темам</h3>
      <div className="mt-4 space-y-6">
        {settings.topics.map((topic) => (
          <div key={topic.id}>
            <p className="text-sm font-medium text-stone-800 dark:text-stone-200">{topic.label}</p>
            <p className="text-sm text-stone-500 dark:text-stone-400">{topic.description}</p>
            <div className="mt-3 space-y-2">
              {channelKeys.map((key) => {
                const meta = channelMeta(settings, key)
                const checked = topic.channels[key as keyof TopicChannelPrefs]
                const disabled =
                  patchSettings.isPending ||
                  !meta.available ||
                  (key !== 'email' && !meta.connected)
                return (
                  <label key={key} className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={(e) => toggleTopicChannel(topic.id, key, e.target.checked)}
                      className={checkboxClass}
                    />
                    <span>
                      <span className="block text-sm font-medium text-stone-800 dark:text-stone-200">
                        {meta.label}
                        {meta.comingSoon ? (
                          <span className="ml-2 text-xs font-normal text-stone-500">({meta.comingSoon})</span>
                        ) : null}
                      </span>
                      {key !== 'email' && meta.available && !meta.connected ? (
                        <span className="block text-xs text-stone-500 dark:text-stone-400">
                          Сначала подключите канал выше.
                        </span>
                      ) : null}
                    </span>
                  </label>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {patchError ? <p className="mt-4 text-sm text-rose-600 dark:text-rose-400">{patchError}</p> : null}
    </section>
  )
}
