import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { BookingClientListItem } from '../../api/bookings'
import { VisitBookingActions } from '../booking/VisitBookingActions'
import {
  BookingStatus,
  bookingStatusBadgeClass,
  bookingStatusLabel,
} from '../../lib/bookingStatus'
import { cn } from '../../lib/forms'
import { surfaceCardClass } from '../../lib/surface'
import { visitCardAccentClass } from '../../lib/visitListCard'
import { formatSlotShort, visitActionComment } from './clientCabinetFormat'

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

export function ClientStatCard({ icon, value, label, sub, iconBg, iconColor, iconLinkTo, iconLinkLabel }: StatProps) {
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
    <div className={cn(surfaceCardClass, 'p-4')}>
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

export function ClientVisitRow({
  b,
  i,
  showActions,
  onReschedule,
  onCancel,
  timeZone,
}: {
  b: BookingClientListItem
  i: number
  showActions?: boolean
  onReschedule?: () => void
  onCancel?: () => void
  timeZone?: string
}) {
  const actionComment = visitActionComment(b)

  return (
    <li className={visitCardAccentClass(i, 'flex flex-col gap-2 py-3 pl-3 pr-3 sm:flex-row sm:items-center sm:gap-3')}>
      <div className="min-w-[7.5rem] shrink-0 text-xs font-medium text-stone-600 dark:text-stone-400">{formatSlotShort(b.start_at, timeZone)}</div>
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
            <span className="font-medium text-stone-700 dark:text-stone-300">Комментарий: </span>
            {actionComment}
          </p>
        ) : null}
      </div>
      {showActions && onReschedule && onCancel ? (
        <VisitBookingActions
          subjectLabel={`${b.master_display_name}, ${formatSlotShort(b.start_at, timeZone)}`}
          onReschedule={onReschedule}
          onCancel={onCancel}
        />
      ) : null}
    </li>
  )
}
