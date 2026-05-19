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
