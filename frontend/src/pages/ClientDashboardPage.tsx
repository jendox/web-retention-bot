import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

import { meApi } from '../api/auth'
import { bookingsMyListApi, type BookingClientListItem } from '../api/bookings'
import { clientsMyMastersApi } from '../api/clients'
import {
  IconCalendar,
  IconChevronRight,
  IconClipboard,
  IconOverview,
  IconUsers,
} from '../components/layout/navIcons'
import { blocksCalendar, BookingStatus, isBookingUpcoming } from '../lib/bookingStatus'
import { cn } from '../lib/forms'
import { ClientDemoBookingModal } from '../components/client/ClientDemoBookingModal'
import {
  buildClientCabinetMocks,
  clientDashboardUsesMocks,
  type ClientMasterView,
  type ClientNotificationMock,
  type MockBookableService,
  type MockTelegramBotInfo,
} from '../mocks/clientCabinetMocks'

function isSameLocalDay(iso: string, ref: Date) {
  const d = new Date(iso)
  return d.getFullYear() === ref.getFullYear() && d.getMonth() === ref.getMonth() && d.getDate() === ref.getDate()
}

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

function formatRelativeDay(iso: string) {
  const dt = new Date(iso)
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(dt)
}

const accentBar = ['border-l-teal-600', 'border-l-amber-500', 'border-l-rose-400', 'border-l-sky-500'] as const

const EMPTY_BOOKINGS: BookingClientListItem[] = []
const EMPTY_MASTERS: ClientMasterView[] = []

type TabId = 'overview' | 'masters' | 'visits' | 'notifications' | 'help'
type VisitFilter = 'upcoming' | 'past' | 'cancelled'

const tabs: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Обзор' },
  { id: 'masters', label: 'Мои мастера' },
  { id: 'visits', label: 'Записи' },
  { id: 'notifications', label: 'Уведомления' },
  { id: 'help', label: 'Как это работает' },
]

type StatProps = {
  icon: ReactNode
  value: string | number
  label: string
  sub?: string
  iconBg: string
  iconColor: string
}

function StatCard({ icon, value, label, sub, iconBg, iconColor }: StatProps) {
  return (
    <div className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
      <div className="flex items-start gap-3">
        <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-lg', iconBg, iconColor)}>{icon}</div>
        <div className="min-w-0">
          <p className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">{value}</p>
          <p className="text-sm text-stone-600 dark:text-stone-400">{label}</p>
          {sub ? <p className="mt-0.5 text-xs text-stone-500 dark:text-stone-500">{sub}</p> : null}
        </div>
      </div>
    </div>
  )
}

function VisitRow({ b, i }: { b: BookingClientListItem; i: number }) {
  return (
    <li
      key={b.id}
      className={cn(
        'flex flex-col gap-1 rounded-lg border border-stone-100 bg-stone-50/80 py-3 pl-3 pr-3 sm:flex-row sm:items-center sm:gap-3 dark:border-stone-800 dark:bg-stone-950/40',
        'border-l-4',
        accentBar[i % accentBar.length],
      )}
    >
      <div className="min-w-[7.5rem] shrink-0 text-xs font-medium text-stone-600 dark:text-stone-400">{formatSlotShort(b.start_at)}</div>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-stone-900 dark:text-stone-100">{b.master_display_name}</p>
        <p className="text-xs text-stone-500 dark:text-stone-500">
          {b.service_name} · {b.duration_min} мин · {b.price_snapshot} {b.currency_snapshot}
          {b.status === BookingStatus.CANCELLED ? (
            <span className="ml-2 rounded-md bg-stone-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-stone-700 dark:bg-stone-700 dark:text-stone-200">
              отменена
            </span>
          ) : null}
        </p>
      </div>
    </li>
  )
}

function computeVisitStats(bookings: BookingClientListItem[]) {
  const nowInner = new Date()
  const scheduled = bookings.filter((b) => blocksCalendar(b.status))
  const upcoming = scheduled
    .filter((b) => isBookingUpcoming(b, nowInner))
    .sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
  const next = upcoming[0]
  const monthStart = startOfMonth(nowInner)
  const monthEnd = endOfMonth(nowInner)
  const inMonth = scheduled.filter((b) => {
    const t = new Date(b.start_at)
    return t >= monthStart && t <= monthEnd
  })
  const today = scheduled.filter((b) => isSameLocalDay(b.start_at, nowInner))
  const mastersUpcoming = new Set(upcoming.map((b) => b.master_id)).size

  return {
    upcomingCount: upcoming.length,
    nextLabel: next ? formatSlotShort(next.start_at) : undefined,
    nextMaster: next?.master_display_name,
    nextBooking: next,
    monthCount: inMonth.length,
    todayCount: today.length,
    mastersUpcoming,
    topUpcoming: upcoming.slice(0, 6),
    totalScheduled: scheduled.length,
  }
}

export function ClientDashboardPage() {
  const navigate = useNavigate()
  const useMocks = clientDashboardUsesMocks()
  const mockBundle = useMemo(() => (useMocks ? buildClientCabinetMocks() : null), [useMocks])

  const [tab, setTab] = useState<TabId>('overview')
  const [visitFilter, setVisitFilter] = useState<VisitFilter>('upcoming')
  const [masterSearch, setMasterSearch] = useState('')
  const [inviteCopyHint, setInviteCopyHint] = useState(false)
  const [mockBookingExtras, setMockBookingExtras] = useState<BookingClientListItem[]>([])
  const [bookingModalOpen, setBookingModalOpen] = useState(false)
  const [bookingModalMasterId, setBookingModalMasterId] = useState<string | null>(null)
  const [bookingModalNonce, setBookingModalNonce] = useState(0)
  const [demoBookingNotice, setDemoBookingNotice] = useState(false)
  const [demoTelegram, setDemoTelegram] = useState<{
    linked: boolean
    username: string | null
    reminders: boolean
  }>(() => ({
    linked: false,
    username: null,
    reminders: true,
  }))

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const bookingsLive = useQuery({
    queryKey: ['bookings', 'me'],
    queryFn: bookingsMyListApi,
    enabled: !useMocks && me.isSuccess,
    retry: false,
  })
  const myMastersLive = useQuery({
    queryKey: ['clients', 'me', 'masters'],
    queryFn: clientsMyMastersApi,
    enabled: !useMocks && me.isSuccess,
    retry: false,
  })

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  const bookingsLiveData = bookingsLive.data
  const myMastersLiveData = myMastersLive.data

  const bookings = useMemo(() => {
    const base = useMocks ? (mockBundle?.bookings ?? EMPTY_BOOKINGS) : (bookingsLiveData ?? EMPTY_BOOKINGS)
    if (!useMocks) {
      return base
    }
    return [...base, ...mockBookingExtras]
  }, [bookingsLiveData, mockBookingExtras, mockBundle, useMocks])

  const masters = useMemo(() => {
    if (useMocks) {
      return mockBundle?.masters ?? EMPTY_MASTERS
    }
    return (myMastersLiveData ?? EMPTY_MASTERS) as ClientMasterView[]
  }, [mockBundle, myMastersLiveData, useMocks])

  const notifications: ClientNotificationMock[] = useMocks ? (mockBundle?.notifications ?? []) : []
  const bookableServices: MockBookableService[] = useMocks ? (mockBundle?.bookableServices ?? []) : []
  const telegramBot: MockTelegramBotInfo | undefined = mockBundle?.telegramBot

  const openDemoBookingModal = (masterId: string | null) => {
    setBookingModalNonce((n) => n + 1)
    setBookingModalMasterId(masterId)
    setBookingModalOpen(true)
  }

  const firstName = useMemo(() => me.data?.email?.split('@')[0] ?? 'Вы', [me.data?.email])

  const stats = useMemo(() => computeVisitStats(bookings), [bookings])

  const filteredMasters = useMemo(() => {
    const q = masterSearch.trim().toLowerCase()
    if (!q) {
      return masters
    }
    return masters.filter(
      (m) =>
        m.display_name.toLowerCase().includes(q) ||
        m.client_display_name.toLowerCase().includes(q) ||
        (m.alias?.toLowerCase().includes(q) ?? false),
    )
  }, [masters, masterSearch])

  const visitsForFilter = useMemo(() => {
    const now = new Date()
    const list = [...bookings]
    if (visitFilter === 'upcoming') {
      return list
        .filter((b) => isBookingUpcoming(b, now))
        .sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
    }
    if (visitFilter === 'past') {
      return list
        .filter((b) => b.status !== BookingStatus.CANCELLED && !isBookingUpcoming(b, now))
        .sort((a, b) => new Date(b.start_at).getTime() - new Date(a.start_at).getTime())
    }
    return list
      .filter((b) => b.status === BookingStatus.CANCELLED)
      .sort((a, b) => new Date(b.start_at).getTime() - new Date(a.start_at).getTime())
  }, [bookings, visitFilter])

  const dataLoading = !useMocks && (bookingsLive.isLoading || myMastersLive.isLoading)
  const dataError = !useMocks && (bookingsLive.isError || myMastersLive.isError)

  const linkedMasterCount = masters.length

  if (me.isLoading || !me.data) {
    return <p className="text-stone-500 dark:text-stone-400">Загрузка…</p>
  }

  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50 sm:text-3xl">
              Здравствуйте, {firstName}! <span aria-hidden>👋</span>
            </h1>
            <p className="text-sm text-stone-500 dark:text-stone-400">{formatRuGreetingDate(new Date())}</p>
          </div>
          {useMocks ? (
            <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
              Демо-данные · API выключен
            </span>
          ) : null}
        </div>
        <p className="max-w-2xl text-sm text-stone-600 dark:text-stone-400">
          Личный кабинет: записи к мастерам и напоминания. Расписание студии и учёт клиентов — в режиме мастера.
        </p>

        <div
          role="tablist"
          aria-label="Разделы личного кабинета"
          className="flex flex-wrap gap-2 border-b border-stone-200 pb-2 dark:border-stone-700"
        >
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                tab === t.id
                  ? 'bg-teal-600 text-white shadow-sm shadow-teal-900/15 dark:bg-teal-500 dark:text-stone-950'
                  : 'text-stone-600 hover:bg-stone-100 dark:text-stone-400 dark:hover:bg-stone-800/70',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </header>

      {demoBookingNotice ? (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100"
        >
          Запись добавлена в демо-список на этом экране. После перезагрузки страницы изменения не сохранятся.
        </div>
      ) : null}

      {!useMocks && dataError ? (
        <p className="text-sm text-rose-600 dark:text-rose-300">Не удалось загрузить данные. Обновите страницу или попробуйте позже.</p>
      ) : null}

      {tab === 'overview' ? (
        <div className="space-y-8">
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              value={dataLoading ? '—' : stats.upcomingCount}
              label="Предстоящих визитов"
              sub={stats.nextLabel ? `Ближайший · ${stats.nextLabel}` : undefined}
              iconBg="bg-teal-100 dark:bg-teal-950/50"
              iconColor="text-teal-700 dark:text-teal-300"
              icon={<IconCalendar className="h-5 w-5 shrink-0 overflow-visible" />}
            />
            <StatCard
              value={dataLoading ? '—' : linkedMasterCount}
              label="Мастеров в кабинете"
              sub={
                stats.mastersUpcoming > 0
                  ? `С предстоящей записью: ${stats.mastersUpcoming}`
                  : 'Пока без предстоящих визитов'
              }
              iconBg="bg-emerald-100/90 dark:bg-emerald-950/40"
              iconColor="text-emerald-700 dark:text-emerald-300"
              icon={<IconUsers className="h-5 w-5 shrink-0 overflow-visible" />}
            />
            <StatCard
              value={dataLoading ? '—' : stats.todayCount}
              label="Записей сегодня"
              iconBg="bg-amber-100/90 dark:bg-amber-950/35"
              iconColor="text-amber-800 dark:text-amber-200"
              icon={<IconOverview className="h-5 w-5 shrink-0 overflow-visible" />}
            />
            <StatCard
              value={dataLoading ? '—' : stats.monthCount}
              label="В этом месяце"
              sub="Активные записи"
              iconBg="bg-violet-100/90 dark:bg-violet-950/40"
              iconColor="text-violet-700 dark:text-violet-300"
              icon={<IconClipboard className="h-5 w-5 shrink-0 overflow-visible" />}
            />
          </section>

          {stats.nextBooking ? (
            <section className="rounded-xl border border-teal-200/80 bg-gradient-to-br from-teal-50/90 to-white p-5 shadow-sm dark:border-teal-900/40 dark:from-teal-950/25 dark:to-stone-900/80">
              <p className="text-xs font-semibold uppercase tracking-wide text-teal-800 dark:text-teal-200">Следующий визит</p>
              <p className="mt-2 text-xl font-semibold text-stone-900 dark:text-stone-50">{stats.nextBooking.master_display_name}</p>
              <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
                {stats.nextBooking.service_name} · {formatSlotShort(stats.nextBooking.start_at)}
              </p>
              <p className="mt-3 text-xs text-stone-500 dark:text-stone-400">
                Перенос и отмена — по договорённости с мастером; самообслуживание появится позже.
              </p>
              <button
                type="button"
                onClick={() => setTab('visits')}
                className="mt-4 text-sm font-medium text-teal-800 underline decoration-teal-600/40 decoration-dotted hover:text-teal-900 dark:text-teal-300 dark:hover:text-teal-200"
              >
                Все записи →
              </button>
            </section>
          ) : null}

          <section className="grid gap-6 lg:grid-cols-5">
            <div className="rounded-xl border border-stone-200/90 bg-white p-5 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80 lg:col-span-3">
              <div className="mb-4 flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Ближайшие визиты</h2>
                <button
                  type="button"
                  onClick={() => setTab('visits')}
                  className="text-sm font-medium text-teal-700 hover:text-teal-600 dark:text-teal-400 dark:hover:text-teal-300"
                >
                  Раздел «Записи» →
                </button>
              </div>
              {dataLoading ? (
                <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем записи…</p>
              ) : stats.topUpcoming.length === 0 ? (
                <p className="text-sm text-stone-500 dark:text-stone-400">
                  Пока нет предстоящих визитов. После приглашения от мастера запись можно оформить по ссылке из письма или сообщения.
                </p>
              ) : (
                <ul className="space-y-2">
                  {stats.topUpcoming.map((b: BookingClientListItem, i: number) => (
                    <VisitRow key={b.id} b={b} i={i} />
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl border border-stone-200/90 bg-white p-5 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80 lg:col-span-2">
              <h2 className="mb-4 text-lg font-semibold text-stone-900 dark:text-stone-50">Быстрые действия</h2>
              <ul className="space-y-1">
                {useMocks ? (
                  <li>
                    <button
                      type="button"
                      onClick={() => openDemoBookingModal(null)}
                      className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
                    >
                      Записаться к мастеру (демо)
                      <IconChevronRight className="h-4 w-4 text-stone-400" />
                    </button>
                  </li>
                ) : null}
                <li>
                  <button
                    type="button"
                    onClick={() => setTab('masters')}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
                  >
                    Мои мастера
                    <IconChevronRight className="h-4 w-4 text-stone-400" />
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={() => setTab('notifications')}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
                  >
                    Уведомления
                    <IconChevronRight className="h-4 w-4 text-stone-400" />
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={async () => {
                      const invite = sessionStorage.getItem('last_invite_url')
                      if (invite) {
                        try {
                          await navigator.clipboard.writeText(invite)
                          setInviteCopyHint(true)
                          window.setTimeout(() => setInviteCopyHint(false), 2500)
                        } catch {
                          setInviteCopyHint(false)
                        }
                      }
                    }}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
                  >
                    Скопировать последнюю ссылку приглашения
                    <IconChevronRight className="h-4 w-4 text-stone-400" />
                  </button>
                  <p className="px-3 pb-1 text-xs text-stone-500 dark:text-stone-400">
                    Если вы открывали приглашение в этом браузере, URL мог сохраниться.
                  </p>
                  {inviteCopyHint ? (
                    <p className="px-3 text-xs text-teal-700 dark:text-teal-300" role="status">
                      Скопировано в буфер.
                    </p>
                  ) : null}
                </li>
                <li className="rounded-lg border border-dashed border-stone-200 px-3 py-3 text-xs text-stone-500 dark:border-stone-600 dark:text-stone-400">
                  Нужна помощь по шагам — откройте вкладку «Как это работает».
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
              <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Визиты</p>
              <p className="mt-2 text-lg font-semibold text-stone-900 dark:text-stone-50">{stats.totalScheduled}</p>
              <p className="mt-1 text-xs text-stone-500">Всего активных записей в списке (не отменённые).</p>
            </div>
          </section>
        </div>
      ) : null}

      {tab === 'masters' ? (
        <section className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Ваши мастера</h2>
            <label className="block max-w-md flex-1">
              <span className="sr-only">Поиск</span>
              <input
                value={masterSearch}
                onChange={(e) => setMasterSearch(e.target.value)}
                placeholder="Поиск по имени мастера или карточке"
                className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100"
              />
            </label>
          </div>
          {dataLoading ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем…</p>
          ) : filteredMasters.length === 0 ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">
              {masters.length === 0
                ? 'Пока нет привязанных мастеров. Примите приглашение по ссылке — мастер появится здесь.'
                : 'Ничего не найдено. Измените запрос.'}
            </p>
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2">
              {filteredMasters.map((m: ClientMasterView) => (
                <li
                  key={m.link_id}
                  className="flex flex-col gap-2 rounded-xl border border-stone-100 bg-stone-50/80 px-4 py-4 dark:border-stone-800 dark:bg-stone-950/40"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-semibold text-stone-900 dark:text-stone-100">{m.display_name}</p>
                      {m.public_slug ? (
                        <p className="text-xs text-stone-500 dark:text-stone-400">@{m.public_slug}</p>
                      ) : null}
                    </div>
                    <span className="shrink-0 rounded-md bg-white px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-teal-800 shadow-sm dark:bg-stone-900 dark:text-teal-200">
                      активна
                    </span>
                  </div>
                  {m.alias ? (
                    <p className="text-sm text-stone-600 dark:text-stone-400">Как вас зовут у мастера: {m.alias}</p>
                  ) : null}
                  <p className="text-xs text-stone-500 dark:text-stone-400">Карточка: {m.client_display_name}</p>
                  {m.contact_hint ? (
                    <p className="text-xs text-stone-600 dark:text-stone-300">{m.contact_hint}</p>
                  ) : (
                    <p className="text-xs text-stone-500 dark:text-stone-400">Связь — по контактам из напоминания или уточните у мастера.</p>
                  )}
                  <div className="flex flex-wrap gap-2 pt-1">
                    <button
                      type="button"
                      disabled={!useMocks}
                      onClick={() => openDemoBookingModal(m.master_id)}
                      className={cn(
                        'rounded-lg px-3 py-1.5 text-xs font-medium',
                        useMocks
                          ? 'border border-teal-600 bg-teal-600 text-white hover:bg-teal-500 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400'
                          : 'cursor-not-allowed border border-stone-200 text-stone-400 dark:border-stone-600',
                      )}
                      title={!useMocks ? 'Доступно в демо-режиме кабинета' : undefined}
                    >
                      Записаться
                    </button>
                    <button
                      type="button"
                      disabled
                      className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-400 dark:border-stone-600"
                      title="Скоро"
                    >
                      Написать
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {tab === 'visits' ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {(
              [
                { id: 'upcoming' as const, label: 'Предстоящие' },
                { id: 'past' as const, label: 'Прошедшие' },
                { id: 'cancelled' as const, label: 'Отменённые' },
              ] satisfies { id: VisitFilter; label: string }[]
            ).map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setVisitFilter(f.id)}
                className={cn(
                  'rounded-full px-3 py-1.5 text-sm font-medium transition-colors',
                  visitFilter === f.id
                    ? 'bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900'
                    : 'bg-stone-100 text-stone-600 hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          {dataLoading ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем записи…</p>
          ) : visitsForFilter.length === 0 ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">В этой категории пока пусто.</p>
          ) : (
            <ul className="space-y-2">
              {visitsForFilter.map((b, i) => (
                <VisitRow key={b.id} b={b} i={i} />
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {tab === 'notifications' ? (
        <section className="space-y-6">
          <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Уведомления</h2>

          {useMocks && telegramBot ? (
            <div className="rounded-xl border border-sky-200/90 bg-gradient-to-br from-sky-50/90 to-white p-5 shadow-sm dark:border-sky-900/40 dark:from-sky-950/30 dark:to-stone-900/80">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-sky-800 dark:text-sky-200">Telegram</p>
                  <h3 className="mt-1 text-base font-semibold text-stone-900 dark:text-stone-50">Бот для напоминаний</h3>
                  <p className="mt-2 max-w-xl text-sm text-stone-600 dark:text-stone-400">
                    Чтобы получать уведомления в Telegram, нужен бот сервиса: он отправляет сообщения от своего имени. Вы один раз
                    открываете бота и нажимаете Start — так мы узнаём ваш чат и сможем слать напоминания о записях.
                  </p>
                </div>
              </div>

              {!demoTelegram.linked ? (
                <div className="mt-4 space-y-4 border-t border-sky-100 pt-4 dark:border-sky-900/40">
                  <ol className="list-decimal space-y-2 pl-5 text-sm text-stone-600 dark:text-stone-400">
                    <li>
                      Откройте бота по ссылке и нажмите <span className="font-medium text-stone-800 dark:text-stone-200">Start</span>.
                    </li>
                    <li>Вернитесь сюда и подтвердите привязку — в продукте шаг подтвердится автоматически после ответа бота.</li>
                  </ol>
                  <div className="flex flex-wrap gap-2">
                    <a
                      href={telegramBot.deep_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 dark:bg-sky-500 dark:text-stone-950 dark:hover:bg-sky-400"
                    >
                      Открыть @{telegramBot.username}
                    </a>
                    <button
                      type="button"
                      onClick={() =>
                        setDemoTelegram((prev) => ({
                          ...prev,
                          linked: true,
                          username: '@demo_elena_linked',
                        }))
                      }
                      className="rounded-lg border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 dark:border-stone-600 dark:bg-stone-900 dark:text-stone-100 dark:hover:bg-stone-800"
                    >
                      Я нажала Start (имитация привязки)
                    </button>
                  </div>
                  <p className="text-xs text-stone-500 dark:text-stone-400">
                    Ссылка и бот вымышленные — для демонстрации интерфейса.
                  </p>
                </div>
              ) : (
                <div className="mt-4 space-y-4 border-t border-sky-100 pt-4 dark:border-sky-900/40">
                  <p className="text-sm text-stone-700 dark:text-stone-300">
                    Привязано:{' '}
                    <span className="font-mono font-medium text-stone-900 dark:text-stone-50">{demoTelegram.username}</span>
                  </p>
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      checked={demoTelegram.reminders}
                      onChange={(e) => setDemoTelegram((prev) => ({ ...prev, reminders: e.target.checked }))}
                      className="mt-1 h-4 w-4 rounded border-stone-300 text-teal-600 focus:ring-teal-500"
                    />
                    <span className="text-sm text-stone-600 dark:text-stone-400">
                      <span className="font-medium text-stone-900 dark:text-stone-100">Напоминания о визитах</span>
                      <span className="block text-xs text-stone-500 dark:text-stone-500">За сутки и за два часа до записи (как в продукте).</span>
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      setDemoTelegram({
                        linked: false,
                        username: null,
                        reminders: true,
                      })
                    }
                    className="text-sm font-medium text-rose-700 hover:underline dark:text-rose-400"
                  >
                    Отвязать Telegram
                  </button>
                </div>
              )}
            </div>
          ) : null}

          {!useMocks ? (
            <div className="rounded-xl border border-dashed border-stone-300 bg-white/80 p-6 dark:border-stone-600 dark:bg-stone-900/60">
              <p className="text-sm text-stone-600 dark:text-stone-400">
                Лента уведомлений в приложении появится позже. Сейчас важные сообщения приходят на email.
              </p>
              <Link
                to="/settings"
                className="mt-4 inline-flex text-sm font-medium text-teal-700 hover:text-teal-600 dark:text-teal-400"
              >
                Настройки почты →
              </Link>
            </div>
          ) : notifications.length === 0 ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">В демо-ленте пока нет записей.</p>
          ) : (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-stone-700 dark:text-stone-300">Лента</h3>
            <ul className="space-y-2">
              {notifications.map((n) => (
                <li
                  key={n.id}
                  className={cn(
                    'rounded-xl border border-stone-100 bg-white px-4 py-3 shadow-sm dark:border-stone-800 dark:bg-stone-900/80',
                    n.unread ? 'ring-1 ring-teal-500/25' : '',
                  )}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <p className="font-medium text-stone-900 dark:text-stone-50">{n.title}</p>
                    <time className="text-xs text-stone-500 dark:text-stone-400" dateTime={n.created_at}>
                      {formatRelativeDay(n.created_at)}
                    </time>
                  </div>
                  <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{n.body}</p>
                </li>
              ))}
            </ul>
            </div>
          )}
        </section>
      ) : null}

      {tab === 'help' ? (
        <section className="space-y-6 rounded-xl border border-stone-200/90 bg-white p-6 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
          <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Как устроен личный кабинет клиента</h2>
          <ol className="list-decimal space-y-4 pl-5 text-sm text-stone-600 dark:text-stone-400">
            <li>
              <span className="font-medium text-stone-800 dark:text-stone-200">Приглашение.</span> Мастер отправляет ссылку —
              вы принимаете её и связываете аккаунт с его студией.
            </li>
            <li>
              <span className="font-medium text-stone-800 dark:text-stone-200">Запись.</span> В демо-режиме можно оформить визит во
              вкладке «Мои мастера» или через быстрое действие на обзоре; в продакшене слоты проверяются по расписанию мастера.
            </li>
            <li>
              <span className="font-medium text-stone-800 dark:text-stone-200">Напоминания.</span> Письма на email и, при
              подключении, сообщения от Telegram-бота сервиса (во вкладке «Уведомления» — блок про бота).
            </li>
            <li>
              <span className="font-medium text-stone-800 dark:text-stone-200">Изменения.</span> Перенос и отмена пока
              согласуются напрямую с мастером; онлайн-самообслуживание запланировано отдельно.
            </li>
          </ol>
          <p className="text-xs text-stone-500 dark:text-stone-400">
            Тот же логин может открывать кабинет мастера — переключатель находится в меню, когда доступны оба режима.
          </p>
        </section>
      ) : null}

      {useMocks && bookingModalOpen ? (
        <ClientDemoBookingModal
          key={bookingModalNonce}
          onClose={() => setBookingModalOpen(false)}
          masters={masters}
          services={bookableServices}
          existingBookings={bookings}
          initialMasterId={bookingModalMasterId}
          onConfirm={(b) => {
            setMockBookingExtras((prev) => [...prev, b])
            setDemoBookingNotice(true)
            window.setTimeout(() => setDemoBookingNotice(false), 4500)
          }}
        />
      ) : null}
    </div>
  )
}
