import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useOutletContext } from 'react-router-dom'

import { meApi } from '../api/auth'
import type { AppShellOutletContext } from '../app/appShellOutletContext'
import { useMasterMe } from '../hooks/useMasterMe'
import { cn } from '../lib/forms'

const fieldClass =
  'w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:focus:border-stone-500'

const readOnlyFieldClass =
  'cursor-not-allowed bg-stone-100 text-stone-500 dark:bg-stone-800 dark:text-stone-400'

type FormState = {
  masterDisplayName: string
  publicSlug: string
  timezone: string
  currency: string
  clientDisplayName: string
  clientPhone: string
  locale: string
  notificationsEmail: boolean
  remindersEmail: boolean
}

function initials(email: string) {
  return email.slice(0, 2).toUpperCase()
}

export function SettingsPage() {
  const navigate = useNavigate()
  const { isClientOnly } = useOutletContext<AppShellOutletContext>()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useMasterMe(me.isSuccess)
  const [saved, setSaved] = useState(false)

  const email = me.data?.email ?? ''
  const defaultState = useMemo<FormState>(
    () => ({
      masterDisplayName: master.data?.display_name ?? '',
      publicSlug: master.data?.public_slug ?? '',
      timezone: master.data?.timezone ?? 'Europe/Minsk',
      currency: master.data?.default_currency ?? 'BYN',
      clientDisplayName: email.split('@')[0] || 'Клиент',
      clientPhone: '',
      locale: 'ru',
      notificationsEmail: true,
      remindersEmail: true,
    }),
    [email, master.data],
  )
  const [draft, setDraft] = useState<Partial<FormState>>({})
  const form = { ...defaultState, ...draft }

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

  if (me.isLoading || (me.isSuccess && !master.isFetched)) {
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
            Профили и параметры аккаунта. Сейчас это черновой интерфейс без сохранения на сервере.
          </p>
        </div>
        {saved ? (
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
            Черновик сохранён
          </span>
        ) : null}
      </div>

      <form
        className="space-y-5"
        onSubmit={(e) => {
          e.preventDefault()
          setSaved(true)
        }}
      >
        <section className="rounded-2xl border border-stone-200/90 bg-white p-6 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-teal-600 text-sm font-semibold text-white">
              {initials(email)}
            </div>
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Аккаунт</h2>
              <p className="truncate text-sm text-stone-500 dark:text-stone-400">{email}</p>
            </div>
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Email для входа</span>
              <input value={email} readOnly className={cn(fieldClass, readOnlyFieldClass, 'mt-1')} />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Язык интерфейса</span>
              <select
                value={form.locale}
                onChange={(e) => setDraft((prev) => ({ ...prev, locale: e.target.value }))}
                className={cn(fieldClass, 'mt-1')}
              >
                <option value="ru">Русский</option>
                <option value="en">English</option>
              </select>
            </label>
          </div>
        </section>

        {!isClientOnly ? (
          <section className="rounded-2xl border border-stone-200/90 bg-white p-6 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
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
            </div>
          </section>
        ) : null}

        <section className="rounded-2xl border border-stone-200/90 bg-white p-6 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
          <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Профиль клиента</h2>
          <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">
            Эти данные пригодятся при записи к мастерам и уведомлениях.
          </p>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Имя клиента</span>
              <input
                value={form.clientDisplayName}
                onChange={(e) => setDraft((prev) => ({ ...prev, clientDisplayName: e.target.value }))}
                className={cn(fieldClass, 'mt-1')}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Телефон</span>
              <input
                value={form.clientPhone}
                onChange={(e) => setDraft((prev) => ({ ...prev, clientPhone: e.target.value }))}
                type="tel"
                className={cn(fieldClass, 'mt-1')}
              />
            </label>
          </div>
        </section>

        <section className="rounded-2xl border border-stone-200/90 bg-white p-6 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
          <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Уведомления</h2>
          <div className="mt-4 space-y-3">
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={form.notificationsEmail}
                onChange={(e) => setDraft((prev) => ({ ...prev, notificationsEmail: e.target.checked }))}
                className="mt-1 h-4 w-4 rounded border-stone-300 text-teal-600 focus:ring-teal-500"
              />
              <span>
                <span className="block text-sm font-medium text-stone-800 dark:text-stone-200">Письма о приглашениях</span>
                <span className="block text-sm text-stone-500 dark:text-stone-400">Новые приглашения и изменения статуса.</span>
              </span>
            </label>
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={form.remindersEmail}
                onChange={(e) => setDraft((prev) => ({ ...prev, remindersEmail: e.target.checked }))}
                className="mt-1 h-4 w-4 rounded border-stone-300 text-teal-600 focus:ring-teal-500"
              />
              <span>
                <span className="block text-sm font-medium text-stone-800 dark:text-stone-200">Напоминания о записях</span>
                <span className="block text-sm text-stone-500 dark:text-stone-400">Письма перед визитом и после изменения записи.</span>
              </span>
            </label>
          </div>
        </section>

        <div className="flex justify-end pt-3">
          <button
            type="submit"
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-500"
          >
            Сохранить черновик
          </button>
        </div>
      </form>
    </div>
  )
}
