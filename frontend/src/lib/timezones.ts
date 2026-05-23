export const DEFAULT_TIMEZONE = 'Europe/Minsk'

const FALLBACK_TIMEZONES = [
  'Europe/Minsk',
  'Europe/Moscow',
  'Europe/Warsaw',
  'Europe/Vilnius',
  'Europe/Riga',
  'Europe/Tallinn',
  'Europe/Kyiv',
  'Europe/Berlin',
  'Europe/London',
  'UTC',
] as const

export function supportedTimeZones() {
  const intlWithSupportedValues = Intl as typeof Intl & {
    supportedValuesOf?: (key: 'timeZone') => string[]
  }
  if (typeof intlWithSupportedValues.supportedValuesOf === 'function') {
    return intlWithSupportedValues.supportedValuesOf('timeZone')
  }
  return [...FALLBACK_TIMEZONES]
}

export function normalizeTimeZone(value: string | null | undefined) {
  const timezone = value?.trim()
  return timezone || DEFAULT_TIMEZONE
}

function timeZoneOffsetMinutes(timeZone: string, date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  const localAsUtc = Date.UTC(
    Number(values.year),
    Number(values.month) - 1,
    Number(values.day),
    Number(values.hour),
    Number(values.minute),
    Number(values.second),
  )
  return Math.round((localAsUtc - date.getTime()) / 60_000)
}

function formatUtcOffset(minutes: number) {
  const sign = minutes >= 0 ? '+' : '-'
  const abs = Math.abs(minutes)
  const hours = String(Math.floor(abs / 60)).padStart(2, '0')
  const mins = String(abs % 60).padStart(2, '0')
  return `UTC${sign}${hours}:${mins}`
}

export function formatTimeZoneOption(timeZone: string, date = new Date()) {
  try {
    return `(${formatUtcOffset(timeZoneOffsetMinutes(timeZone, date))}) ${timeZone}`
  } catch {
    return timeZone
  }
}

export function toDateInputValueInTimeZone(date: Date, timeZone = DEFAULT_TIMEZONE) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const year = parts.find((part) => part.type === 'year')?.value
  const month = parts.find((part) => part.type === 'month')?.value
  const day = parts.find((part) => part.type === 'day')?.value
  return `${year}-${month}-${day}`
}
