import type { BookingClientListItem } from '../../api/bookings'

function dateKeyInTimeZone(date: Date, timeZone?: string) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

function monthKeyInTimeZone(date: Date, timeZone?: string) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
  }).format(date)
}

export function isSameLocalDay(iso: string, ref: Date, timeZone?: string) {
  return dateKeyInTimeZone(new Date(iso), timeZone) === dateKeyInTimeZone(ref, timeZone)
}

export function formatRuGreetingDate(d: Date, timeZone?: string) {
  const formatted = new Intl.DateTimeFormat('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone,
  }).format(d)
  return formatted.replace(' Г.', ' г.')
}

export function formatSlotShort(iso: string, timeZone?: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(new Date(iso))
}

export function clientFirstName(clientDisplayName: string | null | undefined, email: string) {
  const name = clientDisplayName?.trim()
  if (name) {
    return name.split(/\s+/)[0] ?? name
  }
  return email.split('@')[0] || 'Вы'
}

export function computeOverviewStats(
  upcomingItems: BookingClientListItem[],
  upcomingTotal: number,
  timeZone?: string,
) {
  const nowInner = new Date()
  const today = upcomingItems.filter((b) => isSameLocalDay(b.start_at, nowInner, timeZone))
  const currentMonth = monthKeyInTimeZone(nowInner, timeZone)
  const inMonth = upcomingItems.filter((b) => monthKeyInTimeZone(new Date(b.start_at), timeZone) === currentMonth)
  const next = upcomingItems[0]

  return {
    upcomingCount: upcomingTotal,
    nextBooking: next,
    monthCount: inMonth.length,
    todayCount: today.length,
    topUpcoming: upcomingItems.slice(0, 6),
  }
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
