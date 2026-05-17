import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

import { meApi } from '../api/auth'
import { bookingsMyListApi, type BookingClientListItem } from '../api/bookings'
import { clientsMyMastersApi, type ClientMyMasterItem } from '../api/clients'
import {
  IconCalendar,
  IconChevronRight,
  IconClipboard,
  IconOverview,
  IconUsers,
} from '../components/layout/navIcons'
import { cn } from '../lib/forms'

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

const accentBar = ['border-l-teal-600', 'border-l-amber-500', 'border-l-rose-400', 'border-l-sky-500'] as const

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

export function ClientDashboardPage() {
  const navigate = useNavigate()
  const [inviteCopyHint, setInviteCopyHint] = useState(false)

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const bookings = useQuery({
    queryKey: ['bookings', 'me'],
    queryFn: bookingsMyListApi,
    enabled: me.isSuccess,
    retry: false,
  })
  const myMasters = useQuery({
    queryKey: ['clients', 'me', 'masters'],
    queryFn: clientsMyMastersApi,
    enabled: me.isSuccess,
    retry: false,
  })

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  const firstName = useMemo(() => me.data?.email?.split('@')[0] ?? 'Вы', [me.data?.email])

  const stats = useMemo(() => {
    const nowInner = new Date()
    const list = bookings.data ?? []
    const scheduled = list.filter((b) => b.status === 'scheduled')
    const upcoming = scheduled
      .filter((b) => new Date(b.start_at) >= nowInner)
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
      monthCount: inMonth.length,
      todayCount: today.length,
      mastersUpcoming,
      topUpcoming: upcoming.slice(0, 6),
      totalScheduled: scheduled.length,
    }
  }, [bookings.data])

  const linkedMasterCount = myMasters.data?.length

  if (me.isLoading || !me.data) {
    return <p className="text-stone-500 dark:text-stone-400">Загрузка…</p>
  }

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50 sm:text-3xl">
          Здравствуйте, {firstName}! <span aria-hidden>👋</span>
        </h1>
        <p className="text-sm text-stone-500 dark:text-stone-400">{formatRuGreetingDate(new Date())}</p>
        <p className="max-w-2xl text-sm text-stone-600 dark:text-stone-400">
          Личный кабинет: ваши записи к мастерам. Расписание студии и учёт клиентов — только в режиме мастера.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          value={stats.upcomingCount}
          label="Предстоящих визитов"
          sub={stats.nextLabel ? `Ближайший · ${stats.nextLabel}` : undefined}
          iconBg="bg-teal-100 dark:bg-teal-950/50"
          iconColor="text-teal-700 dark:text-teal-300"
          icon={<IconCalendar className="h-5 w-5 shrink-0 overflow-visible" />}
        />
        <StatCard
          value={myMasters.isLoading ? '—' : (linkedMasterCount ?? 0)}
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
          value={stats.todayCount}
          label="Записей сегодня"
          iconBg="bg-amber-100/90 dark:bg-amber-950/35"
          iconColor="text-amber-800 dark:text-amber-200"
          icon={<IconOverview className="h-5 w-5 shrink-0 overflow-visible" />}
        />
        <StatCard
          value={stats.monthCount}
          label="В этом месяце"
          sub="Активные записи"
          iconBg="bg-violet-100/90 dark:bg-violet-950/40"
          iconColor="text-violet-700 dark:text-violet-300"
          icon={<IconClipboard className="h-5 w-5 shrink-0 overflow-visible" />}
        />
      </section>

      <section className="rounded-xl border border-stone-200/90 bg-white p-5 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
        <div className="mb-4 flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Ваши мастера</h2>
        </div>
        {myMasters.isLoading ? (
          <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем…</p>
        ) : myMasters.isError ? (
          <p className="text-sm text-rose-600 dark:text-rose-300">Не удалось загрузить список мастеров.</p>
        ) : !myMasters.data?.length ? (
          <p className="text-sm text-stone-500 dark:text-stone-400">
            Пока нет привязанных мастеров. Примите приглашение по ссылке от мастера — он появится здесь, даже без записи.
          </p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {myMasters.data.map((m: ClientMyMasterItem) => (
              <li
                key={m.link_id}
                className="flex flex-col gap-0.5 rounded-lg border border-stone-100 bg-stone-50/80 px-4 py-3 dark:border-stone-800 dark:bg-stone-950/40"
              >
                <p className="font-medium text-stone-900 dark:text-stone-100">{m.display_name}</p>
                {m.alias ? (
                  <p className="text-xs text-stone-500 dark:text-stone-400">Как вас зовут у мастера: {m.alias}</p>
                ) : null}
                <p className="text-xs text-stone-500 dark:text-stone-400">
                  Ваша карточка: {m.client_display_name}
                  {m.invitation_status && m.invitation_status !== 'LINKED' ? ` · ${m.invitation_status}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-5">
        <div className="rounded-xl border border-stone-200/90 bg-white p-5 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80 lg:col-span-3">
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Ближайшие визиты</h2>
          </div>
          {bookings.isLoading ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем записи…</p>
          ) : stats.topUpcoming.length === 0 ? (
            <p className="text-sm text-stone-500 dark:text-stone-400">
              Пока нет предстоящих визитов. После приглашения от мастера запись можно оформить по ссылке из письма или сообщения.
            </p>
          ) : (
            <ul className="space-y-2">
              {stats.topUpcoming.map((b: BookingClientListItem, i: number) => (
                <li
                  key={b.id}
                  className={cn(
                    'flex flex-col gap-1 rounded-lg border border-stone-100 bg-stone-50/80 py-3 pl-3 pr-3 sm:flex-row sm:items-center sm:gap-3 dark:border-stone-800 dark:bg-stone-950/40',
                    'border-l-4',
                    accentBar[i % accentBar.length],
                  )}
                >
                  <div className="min-w-[7.5rem] shrink-0 text-xs font-medium text-stone-600 dark:text-stone-400">
                    {formatSlotShort(b.start_at)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-stone-900 dark:text-stone-100">{b.master_display_name}</p>
                    <p className="text-xs text-stone-500 dark:text-stone-500">
                      {b.service_name} · {b.duration_min} мин · {b.price_snapshot} {b.currency_snapshot}
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
                Если вы открывали приглашение в этом браузере, URL мог сохраниться (см. также историю вкладки).
              </p>
              {inviteCopyHint ? (
                <p className="px-3 text-xs text-teal-700 dark:text-teal-300" role="status">
                  Скопировано в буфер.
                </p>
              ) : null}
            </li>
            <li>
              <Link
                to="/client"
                className="flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium text-stone-800 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800/60"
              >
                Обновить данные
                <IconChevronRight className="h-4 w-4 text-stone-400" />
              </Link>
            </li>
            <li className="rounded-lg border border-dashed border-stone-200 px-3 py-3 text-xs text-stone-500 dark:border-stone-600 dark:text-stone-400">
              Перенос и отмена записи пока согласуйте с мастером; самообслуживание добавим отдельно.
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
  )
}
