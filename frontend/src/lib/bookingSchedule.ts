import { toDateInputValueInTimeZone } from './timezones'

export const BOOKING_MAX_ADVANCE_DAYS = 90

export const bookingDateFieldClass =
  'w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none transition focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:focus:border-stone-500'

export function toDateInputValue(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function addDays(date: Date, days: number) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

export function bookingDateBounds(timeZone?: string) {
  const today = new Date()
  return {
    min: timeZone ? toDateInputValueInTimeZone(today, timeZone) : toDateInputValue(today),
    max: timeZone
      ? toDateInputValueInTimeZone(addDays(today, BOOKING_MAX_ADVANCE_DAYS), timeZone)
      : toDateInputValue(addDays(today, BOOKING_MAX_ADVANCE_DAYS)),
  }
}

export function formatSlotTime(value: string, timeZone?: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(new Date(value))
}

export function formatSlotDateTime(value: string, timeZone?: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(new Date(value))
}

export function formatBookingDateTime(value: string, timeZone?: string) {
  const date = new Date(value)
  const dateFormatter = new Intl.DateTimeFormat('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone,
  })
  return `${dateFormatter.format(date)}, ${formatSlotTime(value, timeZone)}`
}
