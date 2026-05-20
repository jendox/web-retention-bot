import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate, useOutletContext } from 'react-router-dom'

import { meApi } from '../api/auth'
import { masterMeUpdateApi } from '../api/masters'
import type { AppShellOutletContext } from '../app/appShellOutletContext'
import { NotificationSettingsSection } from '../components/NotificationSettingsSection'
import { cabinetFromPathname } from '../lib/appCabinet'
import { useMasterMe } from '../hooks/useMasterMe'
import { getUserFacingError } from '../lib/apiErrors'
import { cn } from '../lib/forms'
import { surfacePanel } from '../lib/surface'

const fieldClass =
  'w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:focus:border-stone-500'

const readOnlyFieldClass =
  'cursor-not-allowed bg-stone-100 text-stone-500 dark:bg-stone-800 dark:text-stone-400'

type FormState = {
  masterDisplayName: string
  publicSlug: string
  timezone: string
  currency: string
  contactEmail: string
  contactPhone: string
  telegram: string
  viber: string
  clientDisplayName: string
  clientPhone: string
}

function profileInitials(displayName: string | null | undefined, email: string) {
  const name = displayName?.trim()
  if (name) {
    const parts = name.split(/\s+/).filter(Boolean)
    if (parts.length >= 2) {
      return `${parts[0][0] ?? ''}${parts[1][0] ?? ''}`.toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }
  return email.slice(0, 2).toUpperCase()
}

export function SettingsPage() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const outletContext = useOutletContext<AppShellOutletContext>()
  const cabinet = outletContext.cabinet ?? cabinetFromPathname(pathname)
  const isClientCabinet = cabinet === 'client'
  const queryClient = useQueryClient()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useMasterMe(me.isSuccess)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const email = me.data?.email ?? ''
  const clientDisplayName = me.data?.client_display_name?.trim() ?? ''
  const clientPhone = me.data?.client_phone?.trim() ?? ''
  const defaultState = useMemo<FormState>(
    () => ({
      masterDisplayName: master.data?.display_name ?? '',
      publicSlug: master.data?.public_slug ?? '',
      timezone: master.data?.timezone ?? 'Europe/Minsk',
      currency: master.data?.default_currency ?? 'BYN',
      contactEmail: master.data?.contact_email ?? '',
      contactPhone: master.data?.contact_phone ?? '',
      telegram: master.data?.telegram ?? '',
      viber: master.data?.viber ?? '',
      clientDisplayName,
      clientPhone,
    }),
    [clientDisplayName, clientPhone, email, master.data],
  )
  const [draft, setDraft] = useState<Partial<FormState>>({})
  const form = { ...defaultState, ...draft }

  const saveMaster = useMutation({
    mutationFn: () =>
      masterMeUpdateApi({
        display_name: form.masterDisplayName.trim() || undefined,
        public_slug: form.publicSlug.trim() || null,
        timezone: form.timezone,
        default_currency: form.currency,
        contact_email: form.contactEmail.trim() || null,
        contact_phone: form.contactPhone.trim() || null,
        telegram: form.telegram.trim() || null,
        viber: form.viber.trim() || null,
      }),
    onSuccess: async () => {
      setDraft({})
      setSaveError(null)
      setSaved(true)
      await queryClient.invalidateQueries({ queryKey: ['master'] })
    },
    onError: (err) => setSaveError(getUserFacingError(err)),
  })

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  useEffect(() => {
    if (!saved) {
      return
    }
    const timer = window.setTimeout(() => setSaved(false), 3000)
    return () => window.clearTimeout(timer)
  }, [saved])

  if (me.isLoading || (!isClientCabinet && me.isSuccess && !master.isFetched)) {
    return <p className="text-sm text-stone-500 dark:text-stone-400">Загрузка…</p>
  }

  if (!me.data) {
    return null
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-10">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Настройки</h1>
          <p className="mt-1 max-w-2xl text-sm text-stone-600 dark:text-stone-400">
            {isClientCabinet
              ? 'Аккаунт и профиль клиента. Настройки студии — в кабинете мастера.'
              : 'Аккаунт и профиль студии. Контакты мастера сохраняются на сервере.'}
          </p>
        </div>
        {saved ? (
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
            Сохранено
          </span>
        ) : null}
      </div>

      <form
        className="space-y-5"
        onSubmit={(e) => {
          e.preventDefault()
          setSaveError(null)
          if (!isClientCabinet) {
            saveMaster.mutate()
          } else {
            setSaved(true)
          }
        }}
      >
        <section className={surfacePanel('p-6')}>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-teal-600 text-sm font-semibold text-white">
              {profileInitials(
                isClientCabinet ? me.data.client_display_name : master.data?.display_name,
                email,
              )}
            </div>
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Аккаунт</h2>
              <p className="truncate text-sm text-stone-500 dark:text-stone-400">{email}</p>
            </div>
          </div>
          <label className="mt-5 block">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Email для входа</span>
            <input value={email} readOnly className={cn(fieldClass, readOnlyFieldClass, 'mt-1')} />
          </label>
        </section>

        {!isClientCabinet ? (
          <section className={surfacePanel('p-6')}>
            <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Профиль мастера</h2>
            <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">
              Эти данные видны клиентам в приглашениях и личном кабинете.
            </p>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block sm:col-span-2">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Название или имя мастера</span>
                <input
                  value={form.masterDisplayName}
                  onChange={(e) => setDraft((prev) => ({ ...prev, masterDisplayName: e.target.value }))}
                  className={cn(fieldClass, 'mt-1')}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Публичная ссылка</span>
                <input
                  value={form.publicSlug}
                  onChange={(e) => setDraft((prev) => ({ ...prev, publicSlug: e.target.value }))}
                  placeholder="my-studio"
                  className={cn(fieldClass, 'mt-1')}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Часовой пояс</span>
                <select
                  value={form.timezone}
                  onChange={(e) => setDraft((prev) => ({ ...prev, timezone: e.target.value }))}
                  className={cn(fieldClass, 'mt-1')}
                >
                  <option value="Europe/Minsk">Europe/Minsk</option>
                  <option value="Europe/Moscow">Europe/Moscow</option>
                  <option value="Europe/Warsaw">Europe/Warsaw</option>
                </select>
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Валюта услуг</span>
                <select
                  value={form.currency}
                  onChange={(e) => setDraft((prev) => ({ ...prev, currency: e.target.value }))}
                  className={cn(fieldClass, 'mt-1')}
                >
                  <option value="BYN">BYN</option>
                  <option value="RUB">RUB</option>
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                </select>
              </label>
              <label className="block sm:col-span-2">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Email для клиентов</span>
                <input
                  type="email"
                  value={form.contactEmail}
                  onChange={(e) => setDraft((prev) => ({ ...prev, contactEmail: e.target.value }))}
                  placeholder="studio@example.com"
                  className={cn(fieldClass, 'mt-1')}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Телефон</span>
                <input
                  type="tel"
                  value={form.contactPhone}
                  onChange={(e) => setDraft((prev) => ({ ...prev, contactPhone: e.target.value }))}
                  className={cn(fieldClass, 'mt-1')}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Telegram</span>
                <input
                  value={form.telegram}
                  onChange={(e) => setDraft((prev) => ({ ...prev, telegram: e.target.value }))}
                  placeholder="@username"
                  className={cn(fieldClass, 'mt-1')}
                />
              </label>
              <label className="block sm:col-span-2">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Viber</span>
                <input
                  value={form.viber}
                  onChange={(e) => setDraft((prev) => ({ ...prev, viber: e.target.value }))}
                  className={cn(fieldClass, 'mt-1')}
                />
              </label>
            </div>
            {saveError ? <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">{saveError}</p> : null}
          </section>
        ) : null}

        {isClientCabinet ? (
          <section className={surfacePanel('p-6')}>
            <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Профиль клиента</h2>
            <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">
              Имя и телефон из вашей карточки у мастера. Редактирование на сервере появится позже.
            </p>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Имя</span>
                <input
                  value={form.clientDisplayName}
                  readOnly
                  className={cn(fieldClass, readOnlyFieldClass, 'mt-1')}
                  placeholder="Укажите при принятии приглашения"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Телефон</span>
                <input
                  value={form.clientPhone}
                  readOnly
                  type="tel"
                  className={cn(fieldClass, readOnlyFieldClass, 'mt-1')}
                  placeholder="Не указан"
                />
              </label>
            </div>
          </section>
        ) : null}

        <NotificationSettingsSection cabinet={cabinet} />

        <div className="flex justify-end pt-3">
          <button
            type="submit"
            disabled={!isClientCabinet && saveMaster.isPending}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-500 disabled:opacity-60"
          >
            {!isClientCabinet && saveMaster.isPending ? 'Сохраняем…' : 'Сохранить'}
          </button>
        </div>
      </form>
    </div>
  )
}
