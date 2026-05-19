/** Values returned by the API; must match `BookingStatus` in the backend. */
export const BookingStatus = {
  SCHEDULED: 'SCHEDULED',
  COMPLETED: 'COMPLETED',
  NO_SHOW: 'NO_SHOW',
  CANCELLED: 'CANCELLED',
} as const

export type BookingStatusValue = (typeof BookingStatus)[keyof typeof BookingStatus]

export function blocksCalendar(status: string): boolean {
  return status === BookingStatus.SCHEDULED
}

export function isBookingUpcoming(booking: { status: string; end_at: string }, now = new Date()): boolean {
  return blocksCalendar(booking.status) && new Date(booking.end_at) >= now
}

export function bookingStatusLabel(status: string): string {
  if (status === BookingStatus.SCHEDULED) return 'запланирована'
  if (status === BookingStatus.COMPLETED) return 'завершена'
  if (status === BookingStatus.NO_SHOW) return 'неявка'
  if (status === BookingStatus.CANCELLED) return 'отменена'
  return status
}

/** Tailwind classes for status pills in tables and lists. */
export function bookingStatusBadgeClass(status: string): string {
  switch (status) {
    case BookingStatus.SCHEDULED:
      return 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200'
    case BookingStatus.COMPLETED:
      return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200'
    case BookingStatus.NO_SHOW:
      return 'bg-amber-100 text-amber-900 dark:bg-amber-950/80 dark:text-amber-200'
    case BookingStatus.CANCELLED:
      return 'bg-stone-200/80 text-stone-600 dark:bg-stone-800 dark:text-stone-400'
    default:
      return 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300'
  }
}

export function needsAttendanceConfirmation(booking: {
  status: string
  end_at: string
  attendance_confirmed_at?: string | null
}): boolean {
  if (booking.status !== BookingStatus.COMPLETED) {
    return false
  }
  if (booking.attendance_confirmed_at) {
    return false
  }
  return new Date(booking.end_at) < new Date()
}
