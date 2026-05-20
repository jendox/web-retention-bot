import { Link } from 'react-router-dom'

import {
  IconCalendar,
  IconClipboard,
  IconOverview,
  IconUsers,
} from '../../components/layout/navIcons'
import { useClientCabinet } from '../../components/client/ClientCabinetContext'
import {
  ClientStatCard,
  ClientVisitRow,
  formatRuGreetingDate,
  formatSlotShort,
} from '../../components/client/clientCabinetUi'
import { useNotificationsUnreadCount } from '../../components/notifications/NotificationsListSection'
import { surfaceCardClass } from '../../lib/surface'
import { cn } from '../../lib/forms'

export function ClientOverviewPage() {
  const {
    useMocks,
    me,
    firstName,
    masters,
    stats,
    overviewLoading,
    linkedMasterCount,
    openBookingModal,
    canManageVisit,
    setVisitManage,
  } = useClientCabinet()

  const unreadNotificationCount = useNotificationsUnreadCount(!useMocks && Boolean(me))

  return (
    <>
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
      </header>

      <div className="space-y-8">
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <ClientStatCard
            value={overviewLoading ? '—' : stats.upcomingCount}
            label="Предстоящих визитов"
            iconBg="bg-teal-100 dark:bg-teal-950/50"
            iconColor="text-teal-700 dark:text-teal-300"
            icon={<IconCalendar className="h-5 w-5 shrink-0 overflow-visible" />}
          />
          <ClientStatCard
            value={overviewLoading ? '—' : linkedMasterCount}
            label="Мастеров в кабинете"
            iconBg="bg-emerald-100/90 dark:bg-emerald-950/40"
            iconColor="text-emerald-700 dark:text-emerald-300"
            icon={<IconUsers className="h-5 w-5 shrink-0 overflow-visible" />}
          />
          <ClientStatCard
            value={overviewLoading ? '—' : stats.todayCount}
            label="Записей сегодня"
            iconBg="bg-amber-100/90 dark:bg-amber-950/35"
            iconColor="text-amber-800 dark:text-amber-200"
            icon={<IconOverview className="h-5 w-5 shrink-0 overflow-visible" />}
          />
          <ClientStatCard
            value={overviewLoading ? '—' : stats.monthCount}
            label="В этом месяце"
            iconBg="bg-violet-100/90 dark:bg-violet-950/40"
            iconColor="text-violet-700 dark:text-violet-300"
            icon={<IconClipboard className="h-5 w-5 shrink-0 overflow-visible" />}
          />
        </section>

        {stats.nextBooking ? (
          <section className="rounded-xl border border-teal-300 bg-gradient-to-br from-teal-50/90 to-white p-5 shadow-[0_1px_3px_0_rgba(28,25,23,0.08),0_4px_12px_-2px_rgba(28,25,23,0.06)] dark:border-teal-900/40 dark:from-teal-950/25 dark:to-stone-900/80 dark:shadow-sm">
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
            <Link
              to="/client/visits"
              className="mt-4 inline-block text-sm font-medium text-teal-800 underline decoration-teal-600/40 decoration-dotted hover:text-teal-900 dark:text-teal-300 dark:hover:text-teal-200"
            >
              Все записи
            </Link>
          </section>
        ) : null}

        <section className="grid gap-6 lg:grid-cols-5">
          <div className={cn(surfaceCardClass, 'p-5 lg:col-span-3')}>
            <div className="mb-4 flex items-center justify-between gap-2">
              <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Ближайшие визиты</h2>
              <Link
                to="/client/visits"
                className="text-sm font-medium text-teal-700 hover:text-teal-600 dark:text-teal-400 dark:hover:text-teal-300"
              >
                Все записи
              </Link>
            </div>
            {overviewLoading ? (
              <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем записи…</p>
            ) : stats.topUpcoming.length === 0 ? (
              <p className="text-sm text-stone-500 dark:text-stone-400">
                Пока нет предстоящих визитов. После приглашения от мастера запись можно оформить по ссылке из письма или сообщения.
              </p>
            ) : (
              <ul className="space-y-2">
                {stats.topUpcoming.map((b, i) => (
                  <ClientVisitRow key={b.id} b={b} i={i} />
                ))}
              </ul>
            )}
          </div>

          <div className={cn(surfaceCardClass, 'p-5 lg:col-span-2')}>
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
                <Link
                  to="/client/masters"
                  className="block w-full rounded-lg px-3 py-2.5 text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
                >
                  Мои мастера
                </Link>
              </li>
              <li>
                <Link
                  to="/notifications"
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
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
                Нужна помощь по шагам —{' '}
                <Link to="/client/help" className="font-medium text-teal-800 hover:underline dark:text-teal-300">
                  как это работает
                </Link>
                .
              </li>
            </ul>
          </div>
        </section>
      </div>
    </>
  )
}
