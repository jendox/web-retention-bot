import type { Ref } from 'react'

import { formatBookingDateTime } from '../../lib/bookingSchedule'
import { cn } from '../../lib/forms'

function IconCheckCircle(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

export type BookingCreatedNoticeProps = {
  primaryLine: string
  startAt: string
  durationMin: number
  footnote?: string
  innerRef?: Ref<HTMLDivElement>
  className?: string
}

export function BookingCreatedNotice({
  primaryLine,
  startAt,
  durationMin,
  footnote,
  innerRef,
  className,
}: BookingCreatedNoticeProps) {
  return (
    <div
      ref={innerRef}
      role="status"
      className={cn(
        'scroll-mt-4 rounded-xl border border-teal-200/90 bg-teal-50/90 p-4 dark:border-teal-900/50 dark:bg-teal-950/40',
        className,
      )}
    >
      <div className="flex gap-3">
        <IconCheckCircle className="mt-0.5 h-5 w-5 shrink-0 text-teal-700 dark:text-teal-300" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-teal-950 dark:text-teal-50">Запись создана</p>
          <p className="mt-1 text-sm text-teal-900/90 dark:text-teal-100/90">{primaryLine}</p>
          <p className="mt-0.5 text-sm font-medium text-teal-800 dark:text-teal-200">
            {formatBookingDateTime(startAt)} · {durationMin} мин
          </p>
          {footnote ? <p className="mt-2 text-xs text-teal-800/90 dark:text-teal-200/90">{footnote}</p> : null}
        </div>
      </div>
    </div>
  )
}
