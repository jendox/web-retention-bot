import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

import { meApi } from '../api/auth'
import { bookingsListApi, type Booking } from '../api/bookings'
import { clientsListApi } from '../api/clients'
import { invitationsCreateApi } from '../api/invitations'
import { useMasterMe } from '../hooks/useMasterMe'
import { servicesListApi } from '../api/services'
import { IconBriefcase, IconClipboard, IconUsers } from '../components/layout/navIcons'
import { blocksCalendar } from '../lib/bookingStatus'
import { cn } from '../lib/forms'
import { ALLOWED_PAGE_SIZES } from '../lib/pagination'
import { visitCardAccentClass } from '../lib/visitListCard'

function isSameLocalDay(iso: string, ref: Date) {
  const d = new Date(iso)
  return d.getFullYear() === ref.getFullYear() && d.getMonth() === ref.getMonth() && d.getDate() === ref.getDate()
}

const CLIENTS_PAGE_SIZE_CAP = ALLOWED_PAGE_SIZES[ALLOWED_PAGE_SIZES.length - 1]

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

function endOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59, 999)
}

function formatRuGreetingDate(d: Date) {
  const formatted = new Intl.DateTimeFormat('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(d)
  return formatted.replace(' Г.', ' г.')
}

function formatSlotShort(iso: string) {
  const dt = new Date(iso)
  return new Intl.DateTimeFormat('ru-RU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(dt)
}

type StatProps = {
  icon: ReactNode
  value: string | number
  label: string
  sub?: string
  iconBg: string
  iconColor: string
  iconLinkTo?: string
  iconLinkLabel?: string
}

function StatCard({ icon, value, label, sub, iconBg, iconColor, iconLinkTo, iconLinkLabel }: StatProps) {
  const iconShellClass = cn(
    'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
    iconBg,
    iconColor,
  )

  const iconShell =
    iconLinkTo != null && iconLinkTo.length > 0 ? (
      <Link
        to={iconLinkTo}
        className={cn(
          iconShellClass,
          'transition hover:brightness-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:hover:brightness-110',
        )}
        aria-label={iconLinkLabel ?? `Перейти: ${label}`}
      >
        {icon}
      </Link>
    ) : (
      <div className={iconShellClass}>{icon}</div>
    )

  return (
    <div className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
      <div className="flex items-start gap-3">
        {iconShell}
        <div className="min-w-0">
          <p className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">{value}</p>
          <p className="text-sm text-stone-600 dark:text-stone-400">{label}</p>
          {sub ? <p className="mt-0.5 text-xs text-stone-500 dark:text-stone-500">{sub}</p> : null}
        </div>
      </div>
    </div>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [inviteMessage, setInviteMessage] = useState<string>()
  const [inviteCopyDone, setInviteCopyDone] = useState(false)

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useMasterMe(me.isSuccess)
  const clients = useQuery({
    queryKey: ['clients', 'dashboard-summary', 1, CLIENTS_PAGE_SIZE_CAP],
    queryFn: () => clientsListApi({ page: 1, page_size: CLIENTS_PAGE_SIZE_CAP }),
    enabled: me.isSuccess,
  })
  const bookings = useQuery({
    queryKey: ['bookings', 'upcoming', 1, CLIENTS_PAGE_SIZE_CAP],
    queryFn: () => bookingsListApi({ scope: 'upcoming', page: 1, page_size: CLIENTS_PAGE_SIZE_CAP }),
    enabled: me.isSuccess,
  })
  const servicesActive = useQuery({
    queryKey: ['services', 'dashboard-summary', 1, CLIENTS_PAGE_SIZE_CAP, 'active'],
    queryFn: () => servicesListApi({ page: 1, page_size: CLIENTS_PAGE_SIZE_CAP, is_active: true }),
    enabled: me.isSuccess,
  })
  const servicesForNames = useQuery({
    queryKey: ['services', 'dashboard-booking-names', 1, CLIENTS_PAGE_SIZE_CAP],
    queryFn: () => servicesListApi({ page: 1, page_size: CLIENTS_PAGE_SIZE_CAP }),
    enabled: me.isSuccess,
  })

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  const createInvite = useMutation({
    mutationFn: () => invitationsCreateApi({}),
    onSuccess: (payload) => {
      const relative = `/invite/${payload.token}`
      setInviteMessage(`${window.location.origin}${relative}`)
      setInviteCopyDone(false)
    },
  })

  const copyInviteLink = async () => {
    if (!inviteMessage) {
      return
    }
    try {
      await navigator.clipboard.writeText(inviteMessage)
      setInviteCopyDone(true)
      window.setTimeout(() => setInviteCopyDone(false), 2000)
    } catch {
      setInviteCopyDone(false)
    }
  }

  const clientNameById = useMemo(() => {
    const m = new Map<string, string>()
    for (const row of clients.data?.items ?? []) {
      m.set(row.client.id, row.client.display_name)
    }
    return m
  }, [clients.data])

  const serviceNameById = useMemo(() => {
    const m = new Map<string, string>()
    for (const service of servicesForNames.data?.items ?? []) {
      m.set(service.id, service.name)
    }
    return m
  }, [servicesForNames.data])

  const stats = useMemo(() => {
    const nowInner = new Date()
    const list = bookings.data?.items ?? []
    const scheduled = list.filter((b) => blocksCalendar(b.status))
    const today = scheduled.filter((b) => isSameLocalDay(b.start_at, nowInner))
    today.sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
    const nextToday = today[0]

    const monthStart = startOfMonth(nowInner)
    const monthEnd = endOfMonth(nowInner)
    const inMonth = scheduled.filter((b) => {
      const t = new Date(b.start_at)
      return t >= monthStart && t <= monthEnd
    })
    let revenue = 0
    for (const b of inMonth) {
      const n = Number.parseFloat(b.price_snapshot)
      if (!Number.isNaN(n)) {
        revenue += n
      }
    }

    const upcoming = scheduled
      .filter((b) => new Date(b.start_at) >= nowInner)
      .sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
      .slice(0, 5)

    return {
      clientCount: clients.data?.total ?? 0,
      serviceCount: servicesActive.data?.total ?? 0,
      todayCount: today.length,
      nextTodayLabel: nextToday ? formatSlotShort(nextToday.start_at) : undefined,
      revenueMonth: revenue,
      upcoming,
    }
  }, [bookings.data, clients.data, servicesActive.data])

  const firstName = useMemo(() => {
    const n = master.data?.display_name?.trim()
    if (!n) {
      return me.data?.email?.split('@')[0] ?? 'Вы'
    }
    return n.split(/\s+/)[0] ?? n
  }, [master.data?.display_name, me.data?.email])

  if (me.isLoading || !me.data) {
    return <p className="text-stone-500 dark:text-stone-400">Загрузка…</p>
  }

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50 sm:text-3xl">
          Добро пожаловать, {firstName}! <span aria-hidden>👋</span>
        </h1>
        <p className="text-sm text-stone-500 dark:text-stone-400">{formatRuGreetingDate(new Date())}</p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          value={stats.clientCount}
          label="Клиентов в базе"
          iconBg="bg-teal-100 dark:bg-teal-950/50"
          iconColor="text-teal-700 dark:text-teal-300"
          iconLinkTo="/clients"
          iconLinkLabel="Открыть раздел «Клиенты»"
          icon={<IconUsers className="h-5 w-5 shrink-0 overflow-visible" />}
        />
        <StatCard
          value={stats.serviceCount}
          label="Активных услуг"
          iconBg="bg-emerald-100/90 dark:bg-emerald-950/40"
          iconColor="text-emerald-700 dark:text-emerald-300"
          iconLinkTo="/services"
          iconLinkLabel="Открыть раздел «Услуги»"
          icon={<IconBriefcase className="h-5 w-5 shrink-0 overflow-visible" />}
        />
        <StatCard
          value={stats.todayCount}
          label="Записей сегодня"
          sub={stats.nextTodayLabel ? `Ближайшая · ${stats.nextTodayLabel}` : undefined}
          iconBg="bg-amber-100/90 dark:bg-amber-950/35"
          iconColor="text-amber-800 dark:text-amber-200"
          iconLinkTo="/bookings"
          iconLinkLabel="Открыть раздел «Записи»"
          icon={<IconClipboard className="h-5 w-5 shrink-0 overflow-visible" />}
        />
        <StatCard
          value={stats.revenueMonth > 0 ? `${stats.revenueMonth.toLocaleString('ru-RU')}` : '—'}
          label="Выручка за месяц"
          sub="По активным записям"
          iconBg="bg-violet-100/90 dark:bg-violet-950/40"
          iconColor="text-violet-700 dark:text-violet-300"
          icon={
            <svg
              className="h-5 w-5 overflow-visible"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.75"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-5">
        <div className="rounded-xl border border-stone-200/90 bg-white p-5 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80 lg:col-span-3">
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Ближайшие записи</h2>
            <Link
              to="/bookings"
              className="text-sm font-medium text-teal-700 hover:text-teal-600 dark:text-teal-400 dark:hover:text-teal-300"
            >
              Записи
            </Link>
          </div>
          {stats.upcoming.length === 0 ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">Пока нет предстоящих записей.</p>
          ) : (
            <ul className="space-y-2">
              {stats.upcoming.map((b: Booking, i: number) => (
                <li key={b.id} className={visitCardAccentClass(i, 'flex gap-3 py-3 pl-3 pr-3')}>
                  <div className="min-w-[7.5rem] shrink-0 text-xs font-medium text-stone-600 dark:text-stone-400">
                    {formatSlotShort(b.start_at)}
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-stone-900 dark:text-stone-100">
                      {clientNameById.get(b.client_id) ?? 'Клиент'}
                    </p>
                    <p className="text-xs text-stone-500 dark:text-stone-500">
                      {serviceNameById.get(b.service_id) ?? 'Услуга'} · {b.duration_min} мин · {b.price_snapshot}{' '}
                      {b.currency_snapshot}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-stone-200/90 bg-white p-5 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80 lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold text-stone-900 dark:text-stone-50">Быстрые действия</h2>
          <ul className="space-y-1">
            {[
              { to: '/clients', label: 'Добавить клиента' },
              { to: '/bookings', label: 'Новая запись' },
              { to: '/services', label: 'Добавить услугу' },
              { to: '/schedule', label: 'Открыть расписание' },
            ].map((item) => (
              <li key={item.to}>
                <Link
                  to={item.to}
                  className="block rounded-lg px-3 py-2.5 text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
                >
                  {item.label}
                </Link>
              </li>
            ))}
            <li>
              <button
                type="button"
                onClick={() => createInvite.mutate()}
                disabled={createInvite.isPending}
                className="w-full rounded-lg px-3 py-2.5 text-left text-sm font-medium text-stone-800 transition hover:bg-stone-100 disabled:opacity-50 dark:text-stone-200 dark:hover:bg-stone-800/60"
              >
                Ссылка-приглашение для клиента
              </button>
            </li>
          </ul>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-stone-200/90 bg-white p-5 dark:border-stone-700/90 dark:bg-stone-900/80">
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Учётная запись</p>
          <p className="mt-2 text-lg font-semibold text-stone-900 dark:text-stone-50">{me.data.email}</p>
          <p className="mt-1 text-xs text-stone-500">
            {me.data.email_verified ? 'Email подтверждён' : 'Подтвердите email'}
          </p>
        </div>
        <div className="rounded-xl border border-stone-200/90 bg-white p-5 dark:border-stone-700/90 dark:bg-stone-900/80">
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Профиль мастера</p>
          {master.data ? (
            <>
              <p className="mt-2 text-lg font-semibold text-stone-900 dark:text-stone-50">{master.data.display_name}</p>
              <p className="text-xs text-stone-500">Часовой пояс: {master.data.timezone}</p>
            </>
          ) : (
            <p className="mt-2 text-sm text-stone-500">Профиль не загружен</p>
          )}
        </div>
      </section>

      {inviteMessage ? (
        <div className="rounded-xl border border-teal-200/80 bg-teal-50/90 p-4 text-sm text-stone-800 dark:border-teal-900/50 dark:bg-teal-950/30 dark:text-stone-100">
          <p className="font-medium text-teal-900 dark:text-teal-100">Ссылка для клиента</p>
          <p className="mt-2 break-all font-mono text-xs">
            <button
              type="button"
              onClick={() => void copyInviteLink()}
              className="text-left underline decoration-teal-600/50 decoration-dotted hover:text-teal-900 dark:hover:text-teal-100"
              title="Скопировать"
            >
              {inviteMessage}
            </button>
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void copyInviteLink()}
              className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-500 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400"
            >
              {inviteCopyDone ? 'Скопировано' : 'Копировать'}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
