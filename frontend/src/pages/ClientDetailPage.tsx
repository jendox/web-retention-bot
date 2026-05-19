import { useEffect, useId, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { meApi } from '../api/auth'
import { bookingsListApi, type Booking } from '../api/bookings'
import { clientsGetApi, clientsPatchApi } from '../api/clients'
import { servicesListApi } from '../api/services'
import { bookingStatusLabel } from '../lib/bookingStatus'
import { cn } from '../lib/forms'
import { getUserFacingError } from '../lib/apiErrors'
import { ALLOWED_PAGE_SIZES } from '../lib/pagination'
import { queryClient } from '../lib/query'

const fieldClass =
  'w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-stone-900 shadow-sm outline-none focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:focus:border-stone-500'

const sectionCard =
  'rounded-2xl border border-stone-200/90 bg-white p-6 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80'

const sectionTitle = 'text-base font-semibold text-stone-900 dark:text-stone-50'
const sectionHint = 'mt-1 text-sm text-stone-500 dark:text-stone-400'
const LOOKUP_PAGE_SIZE = ALLOWED_PAGE_SIZES[ALLOWED_PAGE_SIZES.length - 1]

type FormValues = {
  display_name: string
  phone: string
  email: string
  alias: string
  notes: string
}

function EmailStatus({
  clientEmail,
  linkedAccountEmail,
  mismatch,
}: {
  clientEmail: string | null | undefined
  linkedAccountEmail: string | null | undefined
  mismatch: boolean
}) {
  if (mismatch) {
    return (
      <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
        Email отличается от аккаунта клиента: {linkedAccountEmail ?? '—'}.
      </p>
    )
  }
  if (linkedAccountEmail && clientEmail) {
    return (
      <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-300">
        Email подтвержден аккаунтом клиента и не редактируется.
      </p>
    )
  }
  if (clientEmail) {
    return <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">Email указан вручную.</p>
  }
  return <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">Email не указан.</p>
}

function NameStatus({ locked }: { locked: boolean }) {
  if (!locked) {
    return <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">Имя указано в карточке мастера.</p>
  }
  return (
    <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-300">
      Имя подтверждено аккаунтом клиента и не редактируется.
    </p>
  )
}

function formatBookingWhen(isoLocal: string) {
  const d = new Date(isoLocal)
  if (Number.isNaN(d.getTime())) {
    return isoLocal
  }
  return new Intl.DateTimeFormat('ru-RU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
}

function bookingPrice(booking: Booking) {
  return `${booking.price_snapshot} ${booking.currency_snapshot}`
}

export function ClientDetailPage() {
  const { id: clientId = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const panelId = useId()
  const [showSavedNotice, setShowSavedNotice] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const detail = useQuery({
    queryKey: ['client', clientId],
    queryFn: () => clientsGetApi(clientId),
    enabled: me.isSuccess && Boolean(clientId),
    retry: false,
  })
  const bookingsUpcoming = useQuery({
    queryKey: ['bookings', 'upcoming', clientId, 1, LOOKUP_PAGE_SIZE],
    queryFn: () =>
      bookingsListApi({ scope: 'upcoming', page: 1, page_size: LOOKUP_PAGE_SIZE, client_id: clientId }),
    enabled: me.isSuccess && Boolean(clientId),
  })
  const bookingsHistory = useQuery({
    queryKey: ['bookings', 'history', clientId, 1, LOOKUP_PAGE_SIZE],
    queryFn: () =>
      bookingsListApi({ scope: 'history', page: 1, page_size: LOOKUP_PAGE_SIZE, client_id: clientId }),
    enabled: me.isSuccess && Boolean(clientId),
  })
  const services = useQuery({
    queryKey: ['services', 'client-detail-booking-names', 1, LOOKUP_PAGE_SIZE],
    queryFn: () => servicesListApi({ page: 1, page_size: LOOKUP_PAGE_SIZE }),
    enabled: me.isSuccess,
  })

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  useEffect(() => {
    if (!showSavedNotice) {
      return
    }
    const t = window.setTimeout(() => setShowSavedNotice(false), 4000)
    return () => window.clearTimeout(t)
  }, [showSavedNotice])

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<FormValues>({
    defaultValues: {
      display_name: '',
      phone: '',
      email: '',
      alias: '',
      notes: '',
    },
  })

  useEffect(() => {
    if (!detail.data) {
      return
    }
    reset({
      display_name: detail.data.client.display_name,
      phone: detail.data.client.phone ?? '',
      email: detail.data.client.email ?? '',
      alias: detail.data.link.alias ?? '',
      notes: detail.data.link.notes ?? '',
    })
  }, [detail.data, reset])

  const save = useMutation({
    mutationFn: (vals: FormValues) =>
      clientsPatchApi(clientId, {
        display_name: vals.display_name.trim(),
        phone: vals.phone.trim() || null,
        email: vals.email.trim() || null,
        alias: vals.alias.trim() || null,
        notes: vals.notes.trim() || null,
      }),
    onMutate: () => setShowSavedNotice(false),
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({ queryKey: ['clients'] })
      queryClient.setQueryData(['client', clientId], data)
      setShowSavedNotice(true)
    },
  })

  const serviceNameById = useMemo(() => {
    const m = new Map<string, string>()
    for (const service of services.data?.items ?? []) {
      m.set(service.id, service.name)
    }
    return m
  }, [services.data])
  const clientBookings = useMemo(
    () => ({
      upcoming: bookingsUpcoming.data?.items ?? [],
      history: bookingsHistory.data?.items ?? [],
    }),
    [bookingsHistory.data, bookingsUpcoming.data],
  )
  const bookingsLoading = bookingsUpcoming.isLoading || bookingsHistory.isLoading
  const bookingsError = bookingsUpcoming.error ?? bookingsHistory.error

  if (me.isLoading || detail.isLoading) {
    return (
      <div className="p-6">
        <p className="text-sm text-stone-500">Загрузка…</p>
      </div>
    )
  }

  if (detail.isError) {
    const msg = getUserFacingError(detail.error)
    return (
      <div className="space-y-4 p-6">
        <p className="text-sm text-red-700 dark:text-red-300">{msg}</p>
        <Link
          to="/clients"
          className="inline-block text-sm font-medium text-teal-700 underline hover:text-teal-600 dark:text-teal-400"
        >
          ← К списку клиентов
        </Link>
      </div>
    )
  }

  const invitationLabel =
    detail.data?.link.invitation_status === 'LINKED'
      ? 'Привязан'
      : detail.data?.link.invitation_status === 'PENDING'
        ? 'Ожидает'
        : detail.data?.link.invitation_status === 'REVOKED'
          ? 'Отозван'
          : (detail.data?.link.invitation_status ?? '—')
  const emailLocked = Boolean(detail.data?.client.user_id && !detail.data.link.invite_email_mismatch)
  const nameLocked = Boolean(detail.data?.client.user_id)

  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-10">
      <div>
        <Link
          to="/clients"
          className="text-sm font-medium text-teal-700 hover:text-teal-600 dark:text-teal-400 dark:hover:text-teal-300"
        >
          ← Клиенты
        </Link>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">
          {detail.data?.client.display_name ?? 'Карточка клиента'}
        </h1>
        <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
          Статус приглашения:{' '}
          <span className="font-medium text-stone-800 dark:text-stone-200">{invitationLabel}</span>
        </p>
      </div>

        {detail.data?.link.invite_email_mismatch ? (
          <div
            className="rounded-xl border border-amber-200/90 bg-amber-50/90 p-4 text-sm text-amber-950 shadow-sm dark:border-amber-900/50 dark:bg-amber-950/35 dark:text-amber-100"
            role="status"
          >
            <p className="font-medium">Расхождение email</p>
            <p className="mt-1 text-amber-900/90 dark:text-amber-200">
              Клиент зашёл как <span className="font-mono">{detail.data.link.linked_account_email ?? '—'}</span>, в
              карточке указан другой контакт. Обновите email ниже, чтобы клиент гарантированно получал уведомления.
              Предупреждение исчезнет после совпадения адресов.
            </p>
          </div>
        ) : null}

        <form className="space-y-6" onSubmit={handleSubmit((vals) => save.mutate(vals))}>
        {showSavedNotice ? (
          <div
            className="flex items-center gap-2 rounded-xl border border-teal-200/80 bg-teal-50 px-4 py-3 text-sm text-teal-900 shadow-sm dark:border-teal-800/60 dark:bg-teal-950/50 dark:text-teal-100"
            role="status"
            aria-live="polite"
          >
            <span
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-600 text-white dark:bg-teal-500"
              aria-hidden
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </span>
            <span>
              <span className="font-medium">Сохранено.</span> Изменения в карточке применены.
            </span>
          </div>
        ) : null}

        <div className="overflow-hidden rounded-2xl border border-stone-200/90 bg-white shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
          <button
            type="button"
            id={`${panelId}-heading`}
            aria-expanded={detailsOpen}
            aria-controls={panelId}
            className="flex w-full items-start gap-3 px-6 py-4 text-left transition hover:bg-stone-50/90 dark:hover:bg-stone-800/40"
            onClick={() => setDetailsOpen((v) => !v)}
          >
            <span className="min-w-0 flex-1">
              <span className={cn(sectionTitle, 'block')}>Данные клиента</span>
              <span className={cn(sectionHint, 'mt-1 block')}>
                Контакты, псевдоним и заметки.{' '}
                {!detailsOpen && isDirty ? (
                  <span className="font-medium text-amber-700 dark:text-amber-400">Есть несохранённые изменения.</span>
                ) : null}
              </span>
            </span>
            <span
              className="mt-0.5 shrink-0 rounded-lg p-1.5 text-stone-500 dark:text-stone-400"
              aria-hidden
            >
              <svg
                className={cn('h-5 w-5 transition-transform', detailsOpen && 'rotate-180')}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </span>
          </button>

          {detailsOpen ? (
            <div
              id={panelId}
              role="region"
              aria-labelledby={`${panelId}-heading`}
              className="border-t border-stone-200 px-6 pb-6 pt-2 dark:border-stone-700"
            >
              <div className="space-y-4 pt-2">
                <label className="block">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">
                    Имя клиента <span className="text-red-600 dark:text-red-400">*</span>
                  </span>
                  <input
                    {...register('display_name', { required: true })}
                    readOnly={nameLocked}
                    aria-readonly={nameLocked}
                    className={cn(
                      fieldClass,
                      'mt-1',
                      nameLocked &&
                        'cursor-not-allowed bg-stone-100 text-stone-500 dark:bg-stone-800 dark:text-stone-400',
                    )}
                    aria-required="true"
                  />
                  {errors.display_name ? (
                    <span className="mt-1 block text-xs text-red-700 dark:text-red-300">Укажите имя</span>
                  ) : null}
                  <NameStatus locked={nameLocked} />
                </label>

                <label className="block">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Телефон</span>
                  <input {...register('phone')} type="tel" className={cn(fieldClass, 'mt-1')} />
                </label>

                <label className="block">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Email</span>
                  <input
                    {...register('email')}
                    type="email"
                    readOnly={emailLocked}
                    aria-readonly={emailLocked}
                    className={cn(
                      fieldClass,
                      'mt-1',
                      emailLocked &&
                        'cursor-not-allowed bg-stone-100 text-stone-500 dark:bg-stone-800 dark:text-stone-400',
                    )}
                  />
                  {detail.data ? (
                    <EmailStatus
                      clientEmail={detail.data.client.email}
                      linkedAccountEmail={detail.data.link.linked_account_email}
                      mismatch={Boolean(detail.data.link.invite_email_mismatch)}
                    />
                  ) : null}
                </label>

                <label className="block">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Псевдоним у вас</span>
                  <input {...register('alias')} className={cn(fieldClass, 'mt-1')} />
                </label>

                <label className="block">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Заметки</span>
                  <textarea {...register('notes')} rows={4} className={cn(fieldClass, 'mt-1 resize-y')} />
                </label>
              </div>

              {save.isError ? (
                <p className="mt-4 text-sm text-red-700 dark:text-red-300" role="alert">
                  {getUserFacingError(save.error)}
                </p>
              ) : null}

              <div className="mt-6 flex justify-end">
                <button
                  type="submit"
                  disabled={save.isPending || !isDirty}
                  title={!isDirty ? 'Измените поля, чтобы сохранить' : undefined}
                  className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-500 disabled:cursor-not-allowed disabled:opacity-45 dark:bg-teal-600 dark:hover:bg-teal-500"
                >
                  {save.isPending ? 'Сохранение…' : 'Сохранить изменения'}
                </button>
              </div>
            </div>
          ) : null}
        </div>

        {!detailsOpen && save.isError ? (
          <p className="text-sm text-red-700 dark:text-red-300" role="alert">
            {getUserFacingError(save.error)}
          </p>
        ) : null}
      </form>

      <div className={sectionCard}>
        <h2 className={sectionTitle}>Текущие записи</h2>
        <p className={sectionHint}>Будущие активные записи этого клиента.</p>
        {bookingsLoading ? (
          <p className="mt-4 text-sm text-stone-500 dark:text-stone-400">Загружаем записи...</p>
        ) : bookingsError ? (
          <p className="mt-4 text-sm text-red-700 dark:text-red-300">{getUserFacingError(bookingsError)}</p>
        ) : clientBookings.upcoming.length === 0 ? (
          <p className="mt-4 text-sm text-stone-500 dark:text-stone-400">Активных будущих записей нет.</p>
        ) : (
          <ul className="mt-4 divide-y divide-stone-100 dark:divide-stone-800">
            {clientBookings.upcoming.map((booking) => (
              <li key={booking.id} className="flex flex-wrap items-baseline justify-between gap-2 py-3 first:pt-0">
                <div>
                  <p className="font-medium text-stone-900 dark:text-stone-100">
                    {serviceNameById.get(booking.service_id) ?? 'Услуга'}
                  </p>
                  <p className="text-sm text-stone-500 dark:text-stone-400">
                    {formatBookingWhen(booking.start_at)} · {booking.duration_min} мин
                  </p>
                </div>
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">
                  {bookingPrice(booking)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className={sectionCard}>
        <h2 className={sectionTitle}>История записей</h2>
        <p className={sectionHint}>Прошедшие и отмененные записи этого клиента.</p>
        {bookingsLoading ? (
          <p className="mt-4 text-sm text-stone-500 dark:text-stone-400">Загружаем историю...</p>
        ) : bookingsError ? (
          <p className="mt-4 text-sm text-red-700 dark:text-red-300">{getUserFacingError(bookingsError)}</p>
        ) : clientBookings.history.length === 0 ? (
          <p className="mt-4 text-sm text-stone-500 dark:text-stone-400">Истории записей пока нет.</p>
        ) : (
          <ul className="mt-4 divide-y divide-stone-100 dark:divide-stone-800">
            {clientBookings.history.map((booking) => (
              <li key={booking.id} className="flex flex-wrap items-baseline justify-between gap-2 py-3 first:pt-0">
                <div>
                  <p className="font-medium text-stone-700 dark:text-stone-200">
                    {serviceNameById.get(booking.service_id) ?? 'Услуга'}
                  </p>
                  <p className="text-sm text-stone-500 dark:text-stone-400">
                    {formatBookingWhen(booking.start_at)} · {bookingStatusLabel(booking.status)}
                  </p>
                </div>
                <span className="text-sm text-stone-600 dark:text-stone-400">{bookingPrice(booking)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
