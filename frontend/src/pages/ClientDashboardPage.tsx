import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { meApi } from '../api/auth'
import { bookingsMyListApi, type BookingClientListItem, type BookingListScope } from '../api/bookings'
import { clientsMyMastersApi, type ClientMyMasterItem } from '../api/clients'
import {
  IconCalendar,
  IconClipboard,
  IconOverview,
  IconUsers,
} from '../components/layout/navIcons'
import {
  blocksCalendar,
  BookingStatus,
  bookingStatusBadgeClass,
  bookingStatusLabel,
  isBookingUpcoming,
} from '../lib/bookingStatus'
import { getUserFacingError } from '../lib/apiErrors'
import { cn } from '../lib/forms'
import { VisitBookingActions } from '../components/booking/VisitBookingActions'
import { ClientBookingModal } from '../components/client/ClientBookingModal'
import { ClientDemoBookingModal } from '../components/client/ClientDemoBookingModal'
import { ClientVisitManageModal } from '../components/client/ClientVisitManageModal'
import { useNotificationsUnreadCount } from '../components/notifications/NotificationsListSection'
import { ListPagination } from '../components/ui/ListPagination'
import { SegmentTabs } from '../components/ui/SegmentTabs'
import { parsePage, parsePageSize, type PageSize } from '../lib/pagination'
import { visitCardAccentClass } from '../lib/visitListCard'
import {
  buildClientCabinetMocks,
  clientDashboardUsesMocks,
  type ClientMasterView,
  type MockBookableService,
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

const EMPTY_BOOKINGS: BookingClientListItem[] = []
const EMPTY_MASTERS: ClientMasterView[] = []

type TabId = 'overview' | 'masters' | 'visits' | 'help'
type VisitScope = 'upcoming' | 'past'

const TAB_IDS: TabId[] = ['overview', 'masters', 'visits', 'help']

function tabFromParams(params: URLSearchParams): TabId {
  const raw = params.get('tab')
  if (raw === 'notifications') {
    return 'overview'
  }
  return TAB_IDS.includes(raw as TabId) ? (raw as TabId) : 'overview'
}

function visitScopeFromParams(params: URLSearchParams): VisitScope {
  return params.get('visit_scope') === 'past' ? 'past' : 'upcoming'
}

function visitScopeToApi(scope: VisitScope): BookingListScope {
  return scope === 'upcoming' ? 'upcoming' : 'history'
}

const tabs: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Обзор' },
  { id: 'masters', label: 'Мои мастера' },
  { id: 'visits', label: 'Записи' },
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

function VisitRow({
  b,
  i,
  showActions,
  onReschedule,
  onCancel,
}: {
  b: BookingClientListItem
  i: number
  showActions?: boolean
  onReschedule?: () => void
  onCancel?: () => void
}) {
  return (
    <li className={visitCardAccentClass(i, 'flex flex-col gap-2 py-3 pl-3 pr-3 sm:flex-row sm:items-center sm:gap-3')}>
      <div className="min-w-[7.5rem] shrink-0 text-xs font-medium text-stone-600 dark:text-stone-400">{formatSlotShort(b.start_at)}</div>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-stone-900 dark:text-stone-100">{b.master_display_name}</p>
        <p className="text-xs text-stone-500 dark:text-stone-500">
          {b.service_name} · {b.duration_min} мин · {b.price_snapshot} {b.currency_snapshot}
          {b.status !== BookingStatus.SCHEDULED ? (
            <span
              className={cn(
                'ml-2 rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                bookingStatusBadgeClass(b.status),
              )}
            >
              {bookingStatusLabel(b.status)}
            </span>
          ) : null}
        </p>
      </div>
      {showActions && onReschedule && onCancel ? (
        <VisitBookingActions
          subjectLabel={`${b.master_display_name}, ${formatSlotShort(b.start_at)}`}
          onReschedule={onReschedule}
          onCancel={onCancel}
        />
      ) : null}
    </li>
  )
}

function computeOverviewStats(upcomingItems: BookingClientListItem[], upcomingTotal: number) {
  const nowInner = new Date()
  const today = upcomingItems.filter((b) => isSameLocalDay(b.start_at, nowInner))
  const monthStart = startOfMonth(nowInner)
  const monthEnd = endOfMonth(nowInner)
  const inMonth = upcomingItems.filter((b) => {
    const t = new Date(b.start_at)
    return t >= monthStart && t <= monthEnd
  })
  const mastersUpcoming = new Set(upcomingItems.map((b) => b.master_id)).size
  const next = upcomingItems[0]

  return {
    upcomingCount: upcomingTotal,
    nextLabel: next ? formatSlotShort(next.start_at) : undefined,
    nextMaster: next?.master_display_name,
    nextBooking: next,
    monthCount: inMonth.length,
    todayCount: today.length,
    mastersUpcoming,
    topUpcoming: upcomingItems.slice(0, 6),
  }
}

export function ClientDashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const useMocks = clientDashboardUsesMocks()
  const mockBundle = useMemo(() => (useMocks ? buildClientCabinetMocks() : null), [useMocks])

  const tab = tabFromParams(searchParams)
  const visitScope = visitScopeFromParams(searchParams)
  const visitPage = parsePage(searchParams.get('visit_page'))
  const visitPageSize = parsePageSize(searchParams.get('visit_page_size'))

  const setTab = (id: TabId) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      if (id === 'overview') {
        n.delete('tab')
      } else {
        n.set('tab', id)
      }
      return n
    })
  }

  const setVisitScope = (scope: VisitScope) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('tab', 'visits')
      n.set('visit_scope', scope)
      n.set('visit_page', '1')
      n.set('visit_page_size', String(visitPageSize))
      return n
    })
  }

  const setVisitPage = (p: number) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('tab', 'visits')
      n.set('visit_page', String(p))
      n.set('visit_page_size', String(visitPageSize))
      if (!n.get('visit_scope')) {
        n.set('visit_scope', visitScope)
      }
      return n
    })
  }

  const setVisitPageSize = (ps: PageSize) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('tab', 'visits')
      n.set('visit_scope', visitScope)
      n.set('visit_page', '1')
      n.set('visit_page_size', String(ps))
      return n
    })
  }

  const [masterSearch, setMasterSearch] = useState('')
  const [mockBookingExtras, setMockBookingExtras] = useState<BookingClientListItem[]>([])
  const [bookingModalOpen, setBookingModalOpen] = useState(false)
  const [bookingModalMasterId, setBookingModalMasterId] = useState<string | null>(null)
  const [bookingModalNonce, setBookingModalNonce] = useState(0)
  const [demoBookingNotice, setDemoBookingNotice] = useState(false)
  const [visitManage, setVisitManage] = useState<{
    booking: BookingClientListItem
    mode: 'reschedule' | 'cancel'
  } | null>(null)
  const [bookingSuccessNotice, setBookingSuccessNotice] = useState(false)

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const bookingsOverview = useQuery({
    queryKey: ['bookings', 'me', 'overview', 'upcoming'],
    queryFn: () => bookingsMyListApi({ scope: 'upcoming', page: 1, page_size: 10 }),
    enabled: !useMocks && me.isSuccess,
    retry: false,
  })
  const visitsLive = useQuery({
    queryKey: ['bookings', 'me', visitScope, visitPage, visitPageSize],
    queryFn: () =>
      bookingsMyListApi({
        scope: visitScopeToApi(visitScope),
        page: visitPage,
        page_size: visitPageSize,
      }),
    enabled: !useMocks && me.isSuccess && tab === 'visits',
    retry: false,
  })
  const myMastersLive = useQuery({
    queryKey: ['clients', 'me', 'masters'],
    queryFn: clientsMyMastersApi,
    enabled: !useMocks && me.isSuccess,
    retry: false,
  })
  const invalidateCabinetData = () => {
    void queryClient.invalidateQueries({ queryKey: ['bookings', 'me'] })
    void queryClient.invalidateQueries({ queryKey: ['notifications', 'me'] })
    void queryClient.invalidateQueries({ queryKey: ['availability'] })
  }

  useEffect(() => {
    if (!visitsLive.isSuccess || !visitsLive.data) {
      return
    }
    const totalPages = Math.max(1, Math.ceil(visitsLive.data.total / visitPageSize))
    if (visitPage > totalPages) {
      setVisitPage(totalPages)
    }
  }, [visitsLive.isSuccess, visitsLive.data, visitPage, visitPageSize])

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  useEffect(() => {
    if (searchParams.get('tab') === 'notifications') {
      navigate('/notifications', { replace: true })
    }
  }, [navigate, searchParams])

  const myMastersLiveData = myMastersLive.data

  const mockBookings = useMemo(() => {
    const base = mockBundle?.bookings ?? EMPTY_BOOKINGS
    return [...base, ...mockBookingExtras]
  }, [mockBookingExtras, mockBundle])

  const mockVisitsForScope = useMemo(() => {
    const now = new Date()
    if (visitScope === 'upcoming') {
      return mockBookings.filter((b) => isBookingUpcoming(b, now))
    }
    return mockBookings.filter((b) => !isBookingUpcoming(b, now))
  }, [mockBookings, visitScope])

  const masters = useMemo((): ClientMasterView[] | ClientMyMasterItem[] => {
    if (useMocks) {
      return mockBundle?.masters ?? EMPTY_MASTERS
    }
    return myMastersLiveData ?? EMPTY_MASTERS
  }, [mockBundle, myMastersLiveData, useMocks])

  const bookableServices: MockBookableService[] = useMocks ? (mockBundle?.bookableServices ?? []) : []

  const openBookingModal = (masterId: string | null) => {
    setBookingModalNonce((n) => n + 1)
    setBookingModalMasterId(masterId)
    setBookingModalOpen(true)
  }

  const canManageVisit = (b: BookingClientListItem) => isBookingUpcoming(b, new Date())

  const firstName = useMemo(() => {
    const name = me.data?.client_display_name?.trim()
    if (name) {
      return name.split(/\s+/)[0] ?? name
    }
    return me.data?.email?.split('@')[0] ?? 'Вы'
  }, [me.data?.client_display_name, me.data?.email])

  const stats = useMemo(() => {
    if (useMocks) {
      return computeOverviewStats(
        mockBookings.filter((b) => isBookingUpcoming(b, new Date())),
        mockBookings.filter((b) => blocksCalendar(b.status)).length,
      )
    }
    const items = (bookingsOverview.data?.items ?? []).slice(0, 6)
    return computeOverviewStats(items, bookingsOverview.data?.total ?? 0)
  }, [bookingsOverview.data, mockBookings, useMocks])

  const filteredMasters = useMemo(() => {
    const q = masterSearch.trim().toLowerCase()
    if (!q) {
      return masters
    }
    return masters.filter(
      (m) =>
        m.display_name.toLowerCase().includes(q) ||
        (m.alias?.toLowerCase().includes(q) ?? false) ||
        m.contact_email.toLowerCase().includes(q),
    )
  }, [masters, masterSearch])

  const visitItems = useMocks ? mockVisitsForScope : (visitsLive.data?.items ?? [])
  const visitTotal = useMocks ? mockVisitsForScope.length : (visitsLive.data?.total ?? 0)

  const overviewLoading = !useMocks && (bookingsOverview.isLoading || myMastersLive.isLoading)
  const visitsLoading = !useMocks && visitsLive.isLoading
  const dataError = !useMocks && (bookingsOverview.isError || myMastersLive.isError)

  const linkedMasterCount = masters.length
  const unreadNotificationCount = useNotificationsUnreadCount(!useMocks && me.isSuccess)

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

        <SegmentTabs
          tabs={tabs.map((t) => ({ value: t.id, label: t.label }))}
          value={tab}
          onChange={setTab}
          ariaLabel="Разделы личного кабинета"
          className="flex-wrap"
        />
      </header>

      {bookingSuccessNotice ? (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100"
        >
          Запись сохранена.
        </div>
      ) : null}

      {demoBookingNotice ? (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100"
        >
          Запись добавлена в демо-список на этом экране. После перезагрузки страницы изменения не сохранятся.
        </div>
      ) : null}

      {!useMocks && !me.data.email_verified ? (
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100"
        >
          Подтвердите email по ссылке из письма — после этого станут доступны записи, уведомления и запись к мастеру.
        </div>
      ) : null}

      {!useMocks && dataError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200">
          <p>Не удалось загрузить данные. Обновите страницу или попробуйте позже.</p>
          {bookingsOverview.isError ? (
            <p className="mt-1 text-xs opacity-90">Записи: {getUserFacingError(bookingsOverview.error)}</p>
          ) : null}
          {myMastersLive.isError ? (
            <p className="mt-1 text-xs opacity-90">Мастера: {getUserFacingError(myMastersLive.error)}</p>
          ) : null}
        </div>
      ) : null}

      {tab === 'overview' ? (
        <div className="space-y-8">
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              value={overviewLoading ? '—' : stats.upcomingCount}
              label="Предстоящих визитов"
              sub={stats.nextLabel ? `Ближайший · ${stats.nextLabel}` : undefined}
              iconBg="bg-teal-100 dark:bg-teal-950/50"
              iconColor="text-teal-700 dark:text-teal-300"
              icon={<IconCalendar className="h-5 w-5 shrink-0 overflow-visible" />}
            />
            <StatCard
              value={overviewLoading ? '—' : linkedMasterCount}
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
              value={overviewLoading ? '—' : stats.todayCount}
              label="Записей сегодня"
              iconBg="bg-amber-100/90 dark:bg-amber-950/35"
              iconColor="text-amber-800 dark:text-amber-200"
              icon={<IconOverview className="h-5 w-5 shrink-0 overflow-visible" />}
            />
            <StatCard
              value={overviewLoading ? '—' : stats.monthCount}
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
              {!useMocks && canManageVisit(stats.nextBooking) ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setVisitManage({ booking: stats.nextBooking!, mode: 'reschedule' })}
                    className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium hover:bg-white dark:border-stone-600 dark:hover:bg-stone-800"
                  >
                    Перенести
                  </button>
                  <button
                    type="button"
                    onClick={() => setVisitManage({ booking: stats.nextBooking!, mode: 'cancel' })}
                    className="rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-800 dark:border-rose-900/50 dark:text-rose-300"
                  >
                    Отменить
                  </button>
                </div>
              ) : null}
              <button
                type="button"
                onClick={() => setTab('visits')}
                className="mt-4 text-sm font-medium text-teal-800 underline decoration-teal-600/40 decoration-dotted hover:text-teal-900 dark:text-teal-300 dark:hover:text-teal-200"
              >
                Все записи
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
                  Раздел «Записи»
                </button>
              </div>
              {overviewLoading ? (
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
                {masters.length > 0 ? (
                  <li>
                    <button
                      type="button"
                      onClick={() => openBookingModal(null)}
                      className="w-full rounded-lg px-3 py-2.5 text-left text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
                    >
                      {useMocks ? 'Записаться к мастеру (демо)' : 'Записаться к мастеру'}
                    </button>
                  </li>
                ) : null}
                <li>
                  <button
                    type="button"
                    onClick={() => setTab('masters')}
                    className="w-full rounded-lg px-3 py-2.5 text-left text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
                  >
                    Мои мастера
                  </button>
                </li>
                <li>
                  <Link
                    to="/notifications"
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
                  >
                    Уведомления
                    {unreadNotificationCount > 0 ? (
                      <span className="rounded-full bg-teal-600 px-2 py-0.5 text-[10px] font-semibold text-white dark:bg-teal-500 dark:text-stone-950">
                        {unreadNotificationCount}
                      </span>
                    ) : null}
                  </Link>
                </li>
                <li className="rounded-lg border border-dashed border-stone-200 px-3 py-3 text-xs text-stone-500 dark:border-stone-600 dark:text-stone-400">
                  Нужна помощь по шагам — откройте вкладку «Как это работает».
                </li>
              </ul>
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
                placeholder="Поиск по имени мастера"
                className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100"
              />
            </label>
          </div>
          {overviewLoading ? (
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
                  <p className="text-sm text-stone-600 dark:text-stone-300">
                    <span className="text-stone-500 dark:text-stone-400">Email: </span>
                    <a
                      href={`mailto:${m.contact_email}`}
                      className="font-medium text-teal-800 hover:underline dark:text-teal-300"
                    >
                      {m.contact_email}
                    </a>
                  </p>
                  <div className="flex flex-wrap gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => openBookingModal(m.master_id)}
                      className="rounded-lg border border-teal-600 bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-500 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400"
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
          <SegmentTabs
            tabs={[
              { value: 'upcoming', label: 'Предстоящие' },
              { value: 'past', label: 'Прошедшие' },
            ]}
            value={visitScope}
            onChange={setVisitScope}
            ariaLabel="Фильтр записей"
          />
          <p className="text-sm text-stone-500 dark:text-stone-400">
            {visitScope === 'past'
              ? 'Завершённые, отменённые и прошедшие визиты. Отменённые отмечены в списке.'
              : 'Активные записи, которые ещё предстоят.'}
          </p>
          {visitsLoading ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем записи…</p>
          ) : visitItems.length === 0 ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">В этой категории пока пусто.</p>
          ) : (
            <>
              <ul className="space-y-2">
                {visitItems.map((b, i) => (
                  <VisitRow
                    key={b.id}
                    b={b}
                    i={i}
                    showActions={!useMocks && visitScope === 'upcoming' && canManageVisit(b)}
                    onReschedule={() => setVisitManage({ booking: b, mode: 'reschedule' })}
                    onCancel={() => setVisitManage({ booking: b, mode: 'cancel' })}
                  />
                ))}
              </ul>
              {!useMocks && visitTotal > 0 ? (
                <ListPagination
                  page={visitPage}
                  pageSize={visitPageSize}
                  total={visitTotal}
                  onPageChange={setVisitPage}
                  onPageSizeChange={setVisitPageSize}
                />
              ) : null}
            </>
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
              <span className="font-medium text-stone-800 dark:text-stone-200">Напоминания.</span> Письма на email и лента в разделе
              «Уведомления» в меню слева.
            </li>
            <li>
              <span className="font-medium text-stone-800 dark:text-stone-200">Изменения.</span> Предстоящие записи можно
              перенести или отменить во вкладке «Записи»; отменённые попадают в «Прошедшие».
            </li>
          </ol>
          <p className="text-xs text-stone-500 dark:text-stone-400">
            Тот же логин может открывать кабинет мастера — переключатель находится в меню, когда доступны оба режима.
          </p>
        </section>
      ) : null}

      {bookingModalOpen && useMocks ? (
        <ClientDemoBookingModal
          key={bookingModalNonce}
          onClose={() => setBookingModalOpen(false)}
          masters={masters as ClientMasterView[]}
          services={bookableServices}
          existingBookings={mockBookings}
          initialMasterId={bookingModalMasterId}
          onConfirm={(b) => {
            setMockBookingExtras((prev) => [...prev, b])
            setDemoBookingNotice(true)
            window.setTimeout(() => setDemoBookingNotice(false), 4500)
          }}
        />
      ) : null}

      {bookingModalOpen && !useMocks && masters.length > 0 ? (
        <ClientBookingModal
          key={bookingModalNonce}
          onClose={() => setBookingModalOpen(false)}
          masters={masters as ClientMyMasterItem[]}
          initialMasterId={bookingModalMasterId}
          onSuccess={() => {
            invalidateCabinetData()
            setBookingSuccessNotice(true)
            window.setTimeout(() => setBookingSuccessNotice(false), 4500)
          }}
        />
      ) : null}

      {visitManage && !useMocks ? (
        <ClientVisitManageModal
          booking={visitManage.booking}
          mode={visitManage.mode}
          onClose={() => setVisitManage(null)}
          onSuccess={() => {
            invalidateCabinetData()
            setVisitManage(null)
          }}
        />
      ) : null}
    </div>
  )
}
