import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate, useOutletContext } from 'react-router-dom'

import { changePasswordApi, meApi } from '../api/auth'
import { clientProfilePatchApi } from '../api/client/profile'
import { masterMeUpdateApi } from '../api/masters'
import type { AppShellOutletContext } from '../app/appShellOutletContext'
import { NotificationSettingsSection } from '../components/NotificationSettingsSection'
import { cabinetFromPathname } from '../lib/appCabinet'
import { useMasterMe } from '../hooks/useMasterMe'
import { getUserFacingError } from '../lib/apiErrors'
import { cn } from '../lib/forms'
import { surfacePanel } from '../lib/surface'
import { DEFAULT_TIMEZONE, formatTimeZoneOption, normalizeTimeZone, supportedTimeZones } from '../lib/timezones'
import { validatePassword } from '../lib/validators'

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
  clientDisplayName: string
  clientPhone: string
  clientTimezone: string
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

function ChangePasswordSection() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const mutation = useMutation({
    mutationFn: () => changePasswordApi({ current_password: currentPassword, new_password: newPassword }),
    onSuccess: () => {
      setError(null)
      setCurrentPassword('')
      setNewPassword('')
      setFieldError(null)
      setSuccess(true)
    },
    onError: (err) => {
      setSuccess(false)
      setError(getUserFacingError(err))
    },
  })

  useEffect(() => {
    if (!success) return
    const timer = window.setTimeout(() => setSuccess(false), 3000)
    return () => window.clearTimeout(timer)
  }, [success])

  return (
    <section className={surfacePanel('p-6')}>
      <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Смена пароля</h2>
      <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">
        Введите текущий пароль и задайте новый.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Текущий пароль</span>
          <input
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className={cn(fieldClass, 'mt-1')}
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Новый пароль</span>
          <input
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => {
              setNewPassword(e.target.value)
              setFieldError(null)
            }}
            className={cn(fieldClass, 'mt-1')}
          />
          {fieldError ? <p className="mt-1 text-sm text-rose-600 dark:text-rose-400">{fieldError}</p> : null}
        </label>
      </div>
      {error ? <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">{error}</p> : null}
      {success ? (
        <p className="mt-3 text-sm font-medium text-emerald-700 dark:text-emerald-300">Пароль изменён.</p>
      ) : null}
      <div className="mt-4 flex justify-end">
        <button
          type="button"
          disabled={mutation.isPending || !currentPassword || !newPassword}
          onClick={() => {
            setError(null)
            setSuccess(false)
            const result = validatePassword(newPassword)
            if (result !== true) {
              setFieldError(result)
              return
            }
            setFieldError(null)
            mutation.mutate()
          }}
          className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-500 disabled:opacity-60"
        >
          {mutation.isPending ? 'Сохраняем…' : 'Сменить пароль'}
        </button>
      </div>
    </section>
  )
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
  const timezoneOptions = useMemo(
    () => supportedTimeZones().map((timezone) => ({ value: timezone, label: formatTimeZoneOption(timezone) })),
    [],
  )
  const defaultState = useMemo<FormState>(
    () => ({
      masterDisplayName: master.data?.display_name ?? '',
      publicSlug: master.data?.public_slug ?? '',
      timezone: master.data?.timezone ?? DEFAULT_TIMEZONE,
      currency: master.data?.default_currency ?? 'BYN',
      contactEmail: master.data?.contact_email ?? '',
      contactPhone: master.data?.contact_phone ?? '',
      telegram: master.data?.telegram ?? '',
      clientDisplayName,
      clientPhone,
      clientTimezone: normalizeTimeZone(me.data?.client_timezone),
    }),
    [clientDisplayName, clientPhone, me.data?.client_timezone, master.data],
  )
  const [draft, setDraft] = useState<Partial<FormState>>({})
  const form = { ...defaultState, ...draft }

  const hasClientProfile = Boolean(me.data?.client_display_name?.trim() || me.data?.client_phone?.trim())

  const saveClient = useMutation({
    mutationFn: () =>
      clientProfilePatchApi({
        display_name: form.clientDisplayName.trim() || undefined,
        phone: form.clientPhone.trim() || null,
        timezone: form.clientTimezone,
      }),
    onSuccess: (profile) => {
      queryClient.setQueryData<typeof me.data>(['me'], (current) =>
        current
          ? {
              ...current,
              client_display_name: profile.display_name,
              client_phone: profile.phone,
              client_timezone: profile.timezone,
            }
          : current,
      )
      setDraft({})
      setSaveError(null)
      setSaved(true)
    },
    onError: (err) => setSaveError(getUserFacingError(err)),
  })

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
      }),
    onSuccess: (profile) => {
      queryClient.setQueryData(['master'], profile)
      setDraft({})
      setSaveError(null)
      setSaved(true)
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
          } else if (hasClientProfile) {
            saveClient.mutate()
          } else {
            setSaveError('Примите приглашение мастера, чтобы заполнить профиль клиента.')
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
                  {timezoneOptions.map((timezone) => (
                    <option key={timezone.value} value={timezone.value}>
                      {timezone.label}
                    </option>
                  ))}
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
            </div>
            {saveError ? <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">{saveError}</p> : null}
          </section>
        ) : null}

        {isClientCabinet ? (
          <section className={surfacePanel('p-6')}>
            <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Профиль клиента</h2>
            <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">
              Имя и телефон видны мастерам в ваших карточках. Изменения сохраняются для всех связей.
            </p>
            {!hasClientProfile ? (
              <p className="mt-3 text-sm text-amber-700 dark:text-amber-300">
                Профиль появится после принятия приглашения от мастера.
              </p>
            ) : null}
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Имя</span>
                <input
                  value={form.clientDisplayName}
                  onChange={(e) => setDraft((prev) => ({ ...prev, clientDisplayName: e.target.value }))}
                  disabled={!hasClientProfile}
                  className={cn(fieldClass, !hasClientProfile && readOnlyFieldClass, 'mt-1')}
                  placeholder="Укажите при принятии приглашения"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Телефон</span>
                <input
                  value={form.clientPhone}
                  onChange={(e) => setDraft((prev) => ({ ...prev, clientPhone: e.target.value }))}
                  disabled={!hasClientProfile}
                  type="tel"
                  className={cn(fieldClass, !hasClientProfile && readOnlyFieldClass, 'mt-1')}
                  placeholder="Не указан"
                />
              </label>
              <label className="block sm:col-span-2">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Часовой пояс</span>
                <select
                  value={form.clientTimezone}
                  onChange={(e) => setDraft((prev) => ({ ...prev, clientTimezone: e.target.value }))}
                  disabled={!hasClientProfile}
                  className={cn(fieldClass, !hasClientProfile && readOnlyFieldClass, 'mt-1')}
                >
                  {timezoneOptions.map((timezone) => (
                    <option key={timezone.value} value={timezone.value}>
                      {timezone.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {saveError && isClientCabinet ? (
              <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">{saveError}</p>
            ) : null}
          </section>
        ) : null}

        <NotificationSettingsSection cabinet={cabinet} />

        <ChangePasswordSection />

        <div className="flex justify-end pt-3">
          <button
            type="submit"
            disabled={
              (!isClientCabinet && saveMaster.isPending) ||
              (isClientCabinet && (saveClient.isPending || !hasClientProfile))
            }
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-500 disabled:opacity-60"
          >
            {!isClientCabinet && saveMaster.isPending
              ? 'Сохраняем…'
              : isClientCabinet && saveClient.isPending
                ? 'Сохраняем…'
                : 'Сохранить'}
          </button>
        </div>
      </form>
    </div>
  )
}
