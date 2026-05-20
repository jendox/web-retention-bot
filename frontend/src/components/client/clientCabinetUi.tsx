import type { ReactNode } from 'react'

import type { BookingClientListItem } from '../../api/bookings'
import { VisitBookingActions } from '../booking/VisitBookingActions'
import {
  BookingStatus,
  bookingStatusBadgeClass,
  bookingStatusLabel,
} from '../../lib/bookingStatus'
import { cn } from '../../lib/forms'
import { visitCardAccentClass } from '../../lib/visitListCard'

export function isSameLocalDay(iso: string, ref: Date) {
  const d = new Date(iso)
  return d.getFullYear() === ref.getFullYear() && d.getMonth() === ref.getMonth() && d.getDate() === ref.getDate()
}

export function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

export function endOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59, 999)
}

export function formatRuGreetingDate(d: Date) {
  const formatted = new Intl.DateTimeFormat('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(d)
  return formatted.replace(' Г.', ' г.')
}

export function formatSlotShort(iso: string) {
  const dt = new Date(iso)
  return new Intl.DateTimeFormat('ru-RU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(dt)
}

export function clientFirstName(clientDisplayName: string | null | undefined, email: string) {
  const name = clientDisplayName?.trim()
  if (name) {
    return name.split(/\s+/)[0] ?? name
  }
  return email.split('@')[0] || 'Вы'
}

export function computeOverviewStats(upcomingItems: BookingClientListItem[], upcomingTotal: number) {
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

type StatProps = {
  icon: ReactNode
  value: string | number
  label: string
  sub?: string
  iconBg: string
  iconColor: string
}

export function ClientStatCard({ icon, value, label, sub, iconBg, iconColor }: StatProps) {
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

export function visitActionComment(b: BookingClientListItem): string | null {
  if (b.status === 'CANCELLED' && b.cancel_comment) {
    return b.cancel_comment
  }
  if (b.status === 'SCHEDULED' && b.reschedule_comment) {
    return b.reschedule_comment
  }
  return null
}

export function ClientVisitRow({
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
  const actionComment = visitActionComment(b)

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
        {actionComment ? (
          <p className="mt-1 text-xs text-stone-600 dark:text-stone-400">
            <span className="font-medium text-stone-700 dark:text-stone-300">Комментарий мастера: </span>
            {actionComment}
          </p>
        ) : null}
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
