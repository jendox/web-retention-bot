import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { meApi } from '../api/auth'
import { ApiError } from '../api/client'
import { getScheduleApi, putScheduleApi, type SchedulePayload } from '../api/masters'
import { getUserFacingError } from '../lib/apiErrors'
import { cn } from '../lib/forms'
import { queryClient } from '../lib/query'

type TimeRange = {
  start: string
  end: string
}

type WeekdayRule = {
  weekday: number
  label: string
  short: string
  isWorking: boolean
  ranges: TimeRange[]
}

type DayOverride = {
  date: string
  isWorking: boolean
  ranges: TimeRange[]
  note?: string
}

type ScheduleTab = 'calendar' | 'template'

const fieldClass =
  'rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none transition [color-scheme:light] focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:[color-scheme:dark] dark:focus:border-stone-500'

const initialWeek: WeekdayRule[] = [
  { weekday: 0, label: 'Понедельник', short: 'Пн', isWorking: true, ranges: [{ start: '10:00', end: '18:00' }] },
  { weekday: 1, label: 'Вторник', short: 'Вт', isWorking: true, ranges: [{ start: '10:00', end: '18:00' }] },
  { weekday: 2, label: 'Среда', short: 'Ср', isWorking: true, ranges: [{ start: '10:00', end: '18:00' }] },
  { weekday: 3, label: 'Четверг', short: 'Чт', isWorking: true, ranges: [{ start: '10:00', end: '18:00' }] },
  { weekday: 4, label: 'Пятница', short: 'Пт', isWorking: true, ranges: [{ start: '10:00', end: '17:00' }] },
  { weekday: 5, label: 'Суббота', short: 'Сб', isWorking: false, ranges: [] },
  { weekday: 6, label: 'Воскресенье', short: 'Вс', isWorking: false, ranges: [] },
]

function toDateInputValue(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseDateInput(value: string) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function addDays(date: Date, days: number) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function startOfLocalDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function mondayFirstWeekday(date: Date) {
  return (date.getDay() + 6) % 7
}

function normalizeRussianYearSuffix(value: string) {
  return value.replace(' Г.', ' г.')
}

function formatDateLong(value: string) {
  const formatted = new Intl.DateTimeFormat('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
    .format(parseDateInput(value))
  return normalizeRussianYearSuffix(formatted)
}

function formatMonth(date: Date) {
  const formatted = new Intl.DateTimeFormat('ru-RU', {
    month: 'long',
    year: 'numeric',
  })
    .format(date)
  return normalizeRussianYearSuffix(formatted)
}

function getMonthDays(anchor: Date) {
  const monthStart = new Date(anchor.getFullYear(), anchor.getMonth(), 1)
  const gridStart = addDays(monthStart, -mondayFirstWeekday(monthStart))
  return Array.from({ length: 35 }, (_, index) => addDays(gridStart, index))
}

function describeRanges(ranges: TimeRange[]) {
  if (ranges.length === 0) {
    return 'Нет рабочих часов'
  }
  return ranges.map((range) => `${range.start}-${range.end}`).join(', ')
}

function rangeOrDefault(ranges: TimeRange[]) {
  return ranges.length > 0 ? ranges : [{ start: '10:00', end: '18:00' }]
}

function minutesToClock(totalMinutes: number) {
  const normalized = Math.max(0, Math.min(totalMinutes, 24 * 60))
  const hour = Math.floor(normalized / 60)
  const minute = normalized % 60
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
}

function clockToMinutes(value: string) {
  const [hour = 0, minute = 0] = value.split(':').map(Number)
  return hour * 60 + minute
}

function nextRangeAfter(ranges: TimeRange[]) {
  const last = ranges[ranges.length - 1]
  if (!last?.end) {
    return { start: '10:00', end: '11:00' }
  }
  const startMinutes = clockToMinutes(last.end)
  const endMinutes = Math.min(startMinutes + 60, 24 * 60)
  const fallbackStart = Math.max(0, startMinutes - 60)
  return {
    start: minutesToClock(endMinutes > startMinutes ? startMinutes : fallbackStart),
    end: minutesToClock(endMinutes > startMinutes ? endMinutes : startMinutes),
  }
}

function rangeValidationMessage(ranges: TimeRange[]) {
  const indexed = ranges
    .map((range, index) => ({
      index,
      start: clockToMinutes(range.start),
      end: clockToMinutes(range.end),
    }))
    .sort((a, b) => a.start - b.start)

  for (const range of indexed) {
    if (range.start >= range.end) {
      return 'Начало интервала должно быть раньше окончания.'
    }
  }
  for (let index = 1; index < indexed.length; index += 1) {
    if (indexed[index].start < indexed[index - 1].end) {
      return 'Интервалы рабочего времени не должны пересекаться.'
    }
  }
  return undefined
}

function hasRangeValidationErrors(ranges: TimeRange[]) {
  return rangeValidationMessage(ranges) != null
}

function canEditDate(dateValue: string, minEditableDate: string) {
  return dateValue >= minEditableDate
}

function formatHours(value: number) {
  return value.toFixed(2)
}

function scheduleToWeekRules(schedule: SchedulePayload | undefined) {
  if (!schedule) {
    return initialWeek
  }
  return initialWeek.map((day) => {
    const saved = schedule.weekly_days.find((rule) => rule.weekday === day.weekday)
    if (!saved) {
      return {
        ...day,
        isWorking: false,
        ranges: [],
      }
    }
    return {
      ...day,
      isWorking: !saved.is_closed,
      ranges: saved.intervals.map((interval) => ({ start: interval.start_time, end: interval.end_time })),
    }
  })
}

function scheduleToOverrides(schedule: SchedulePayload | undefined) {
  return (
    schedule?.date_overrides.map((override) => ({
      date: override.schedule_date,
      isWorking: !override.is_closed,
      ranges: override.intervals.map((interval) => ({ start: interval.start_time, end: interval.end_time })),
      note: override.note ?? undefined,
    })) ?? []
  )
}

function buildSchedulePayload(weekRules: WeekdayRule[], overrides: DayOverride[]): SchedulePayload {
  return {
    weekly_days: weekRules.map((rule) => ({
      weekday: rule.weekday,
      is_closed: !rule.isWorking,
      intervals: rule.isWorking
        ? rule.ranges.map((range) => ({
          start_time: range.start,
          end_time: range.end,
        }))
        : [],
      note: null,
    })),
    date_overrides: overrides.map((override) => ({
      schedule_date: override.date,
      is_closed: !override.isWorking,
      intervals: override.isWorking
        ? override.ranges.map((range) => ({
          start_time: range.start,
          end_time: range.end,
        }))
        : [],
      note: override.note?.trim() || null,
    })),
  }
}

function schedulePayloadKey(payload: SchedulePayload) {
  return JSON.stringify(payload)
}

function IconPlus(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
    </svg>
  )
}

function IconTrash(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  )
}

function IconCopy(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V5a2 2 0 012-2h7a2 2 0 012 2v9a2 2 0 01-2 2h-2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 7h7a2 2 0 012 2v10H5a2 2 0 01-2-2V9a2 2 0 012-2z" />
    </svg>
  )
}

type RangeEditorProps = {
  ranges: TimeRange[]
  disabled?: boolean
  onChange: (ranges: TimeRange[]) => void
}

function RangeEditor({ ranges, disabled, onChange }: RangeEditorProps) {
  const visibleRanges = rangeOrDefault(ranges)
  const errorMessage = rangeValidationMessage(visibleRanges)

  return (
    <div className="space-y-2">
      {visibleRanges.map((range, index) => (
        <div key={`${index}-${range.start}-${range.end}`} className="flex items-center gap-2">
          <input
            type="time"
            value={range.start}
            disabled={disabled}
            onChange={(event) => {
              const next = [...visibleRanges]
              next[index] = { ...range, start: event.target.value }
              onChange(next)
            }}
            className={cn(
              fieldClass,
              'min-w-0 flex-1 disabled:opacity-50',
              errorMessage && 'border-red-300 focus:border-red-500 focus:ring-red-500/15 dark:border-red-800',
            )}
          />
          <span className="text-stone-400 dark:text-stone-500">-</span>
          <input
            type="time"
            value={range.end}
            disabled={disabled}
            onChange={(event) => {
              const next = [...visibleRanges]
              next[index] = { ...range, end: event.target.value }
              onChange(next)
            }}
            className={cn(
              fieldClass,
              'min-w-0 flex-1 disabled:opacity-50',
              errorMessage && 'border-red-300 focus:border-red-500 focus:ring-red-500/15 dark:border-red-800',
            )}
          />
          <button
            type="button"
            aria-label="Удалить интервал"
            disabled={disabled || visibleRanges.length === 1}
            onClick={() => onChange(visibleRanges.filter((_, itemIndex) => itemIndex !== index))}
            className="rounded-lg border border-stone-200 p-2 text-stone-500 transition hover:bg-stone-100 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-40 dark:border-stone-700 dark:text-stone-400 dark:hover:bg-stone-800 dark:hover:text-red-300"
          >
            <IconTrash className="h-4 w-4" />
          </button>
        </div>
      ))}
      {errorMessage ? <p className="text-xs text-red-700 dark:text-red-300">{errorMessage}</p> : null}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange([...visibleRanges, nextRangeAfter(visibleRanges)])}
        className="inline-flex items-center gap-2 rounded-lg border border-stone-200 px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
      >
        <IconPlus className="h-4 w-4" />
        Добавить интервал
      </button>
    </div>
  )
}

export function SchedulePage() {
  const navigate = useNavigate()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const schedule = useQuery({
    queryKey: ['schedule'],
    queryFn: getScheduleApi,
    enabled: me.isSuccess,
  })
  const [activeTab, setActiveTab] = useState<ScheduleTab>('calendar')
  const [draftWeekRules, setDraftWeekRules] = useState<WeekdayRule[] | null>(null)
  const [draftOverrides, setDraftOverrides] = useState<DayOverride[] | null>(null)
  const [selectedDate, setSelectedDate] = useState(() => toDateInputValue(addDays(startOfLocalDay(new Date()), 1)))
  const [monthAnchor, setMonthAnchor] = useState(() => startOfLocalDay(new Date()))
  const [saveError, setSaveError] = useState<string>()
  const [conflictDialogOpen, setConflictDialogOpen] = useState(false)
  const minEditableDate = useMemo(() => toDateInputValue(addDays(startOfLocalDay(new Date()), 1)), [])

  useEffect(() => {
    if (me.isError) navigate('/login')
  }, [me.isError, navigate])

  const serverWeekRules = useMemo(() => scheduleToWeekRules(schedule.data), [schedule.data])
  const serverOverrides = useMemo(() => scheduleToOverrides(schedule.data), [schedule.data])
  const weekRules = draftWeekRules ?? serverWeekRules
  const overrides = draftOverrides ?? serverOverrides

  const save = useMutation({
    mutationFn: () => putScheduleApi(buildSchedulePayload(weekRules, overrides)),
    onSuccess: async (data) => {
      setSaveError(undefined)
      setConflictDialogOpen(false)
      setDraftWeekRules(null)
      setDraftOverrides(null)
      await queryClient.invalidateQueries({ queryKey: ['schedule'] })
      queryClient.setQueryData(['schedule'], data)
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        setSaveError(undefined)
        setConflictDialogOpen(true)
        return
      }
      setConflictDialogOpen(false)
      setSaveError(getUserFacingError(error))
    },
  })

  const futureOverrides = useMemo(
    () => overrides.filter((override) => override.date >= minEditableDate),
    [minEditableDate, overrides],
  )

  const overridesByDate = useMemo(() => {
    const map = new Map<string, DayOverride>()
    for (const override of futureOverrides) {
      map.set(override.date, override)
    }
    return map
  }, [futureOverrides])

  const selectedWeekday = mondayFirstWeekday(parseDateInput(selectedDate))
  const selectedTemplate = weekRules[selectedWeekday]
  const selectedOverride = overridesByDate.get(selectedDate)
  const selectedEffective = selectedOverride ?? {
    date: selectedDate,
    isWorking: selectedTemplate.isWorking,
    ranges: selectedTemplate.ranges,
  }
  const selectedDateEditable = canEditDate(selectedDate, minEditableDate)
  const monthDays = useMemo(() => getMonthDays(monthAnchor), [monthAnchor])
  const workingTemplateDays = weekRules.filter((rule) => rule.isWorking).length
  const weeklyHours = weekRules.reduce((total, rule) => {
    if (!rule.isWorking) {
      return total
    }
    return (
      total +
      rule.ranges.reduce((dayTotal, range) => {
        const [startHour, startMinute] = range.start.split(':').map(Number)
        const [endHour, endMinute] = range.end.split(':').map(Number)
        return dayTotal + (endHour * 60 + endMinute - startHour * 60 - startMinute) / 60
      }, 0)
    )
  }, 0)
  const savedPayload = useMemo(
    () => buildSchedulePayload(serverWeekRules, serverOverrides),
    [serverOverrides, serverWeekRules],
  )
  const draftPayload = useMemo(() => buildSchedulePayload(weekRules, overrides), [overrides, weekRules])
  const hasChanges = schedulePayloadKey(savedPayload) !== schedulePayloadKey(draftPayload)
  const hasValidationErrors =
    weekRules.some((rule) => rule.isWorking && hasRangeValidationErrors(rule.ranges)) ||
    overrides.some((override) => override.isWorking && hasRangeValidationErrors(override.ranges))

  const upsertOverride = (next: DayOverride) => {
    setDraftOverrides((currentDraft) => {
      const current = currentDraft ?? overrides
      const exists = current.some((override) => override.date === next.date)
      if (exists) {
        return current.map((override) => (override.date === next.date ? next : override))
      }
      return [...current, next].sort((a, b) => a.date.localeCompare(b.date))
    })
  }

  const updateWeekday = (weekday: number, next: Partial<WeekdayRule>) => {
    setDraftWeekRules((currentDraft) => {
      const current = currentDraft ?? weekRules
      return current.map((rule) => (rule.weekday === weekday ? { ...rule, ...next } : rule))
    })
  }

  if (me.isLoading || schedule.isLoading || !me.data) {
    return <p className="text-stone-500 dark:text-stone-400">Загрузка...</p>
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50 sm:text-3xl">
            Расписание
          </h1>
          <p className="max-w-2xl text-sm leading-6 text-stone-600 dark:text-stone-400">
            Настройте шаблон недели и исключения по конкретным датам. Изменения не сохранятся, если затрагивают уже
            назначенные будущие записи.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 rounded-xl border border-stone-200 bg-white p-2 shadow-sm dark:border-stone-700 dark:bg-stone-900/80">
          <div className="min-w-20 px-3 py-2">
            <p className="text-lg font-semibold text-stone-900 dark:text-stone-50">{workingTemplateDays}</p>
            <p className="text-xs text-stone-500 dark:text-stone-400">дней</p>
          </div>
          <div className="min-w-20 border-x border-stone-200 px-3 py-2 dark:border-stone-700">
            <p className="text-lg font-semibold text-stone-900 dark:text-stone-50">{formatHours(weeklyHours)}</p>
            <p className="text-xs text-stone-500 dark:text-stone-400">часов</p>
          </div>
          <div className="min-w-20 px-3 py-2">
            <p className="text-lg font-semibold text-stone-900 dark:text-stone-50">{futureOverrides.length}</p>
            <p className="text-xs text-stone-500 dark:text-stone-400">искл.</p>
          </div>
        </div>
      </header>

      {saveError ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
          {saveError}
        </p>
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="inline-flex rounded-xl border border-stone-200 bg-white p-1 shadow-sm dark:border-stone-700 dark:bg-stone-900/80">
          {[
            ['calendar', 'Календарь'],
            ['template', 'Шаблон недели'],
          ].map(([tab, label]) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab as ScheduleTab)}
              className={cn(
                'rounded-lg px-4 py-2 text-sm font-medium transition',
                activeTab === tab
                  ? 'bg-teal-100 text-teal-900 dark:bg-teal-950/60 dark:text-teal-100'
                  : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-stone-800 dark:hover:text-stone-50',
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => save.mutate()}
          disabled={!hasChanges || hasValidationErrors || save.isPending}
          className={cn(
            'rounded-xl border px-4 py-2 text-sm font-semibold shadow-sm transition disabled:cursor-not-allowed',
            hasChanges
              ? 'border-teal-600 bg-teal-600 text-white shadow-teal-900/15 hover:bg-teal-700 disabled:opacity-60 dark:border-teal-500 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400'
              : 'border-stone-200 bg-white text-stone-400 shadow-stone-900/5 dark:border-stone-700 dark:bg-stone-900/80 dark:text-stone-500',
          )}
        >
          {save.isPending ? 'Сохранение...' : 'Сохранить'}
        </button>
      </div>

      {hasValidationErrors ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
          Проверьте интервалы рабочего времени перед сохранением.
        </p>
      ) : null}

      {activeTab === 'calendar' ? (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(22rem,0.75fr)]">
          <section className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">
                {formatMonth(monthAnchor)}
              </h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setMonthAnchor(new Date(monthAnchor.getFullYear(), monthAnchor.getMonth() - 1, 1))}
                  className="rounded-lg border border-stone-200 px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
                >
                  Назад
                </button>
                <button
                  type="button"
                  onClick={() => setMonthAnchor(new Date(monthAnchor.getFullYear(), monthAnchor.getMonth() + 1, 1))}
                  className="rounded-lg border border-stone-200 px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
                >
                  Вперед
                </button>
              </div>
            </div>

            <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold uppercase text-stone-500 dark:text-stone-400">
              {initialWeek.map((day) => (
                <div key={day.weekday} className="py-2">
                  {day.short}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {monthDays.map((date) => {
                const dateValue = toDateInputValue(date)
                const dayOverride = overridesByDate.get(dateValue)
                const template = weekRules[mondayFirstWeekday(date)]
                const effectiveWorking = dayOverride?.isWorking ?? template.isWorking
                const isCurrentMonth = date.getMonth() === monthAnchor.getMonth()
                const isSelected = dateValue === selectedDate

                return (
                  <button
                    key={dateValue}
                    type="button"
                    onClick={() => setSelectedDate(dateValue)}
                    className={cn(
                      'min-h-20 rounded-lg border p-2 text-left transition',
                      isSelected
                        ? 'border-teal-600 bg-teal-50 ring-2 ring-teal-600/15 dark:border-teal-400 dark:bg-teal-950/30'
                        : dayOverride
                          ? 'border-amber-300 bg-amber-50 hover:border-amber-400 dark:border-amber-800/80 dark:bg-amber-950/20 dark:hover:border-amber-600'
                          : 'border-stone-200 bg-stone-50 hover:border-stone-300 hover:bg-white dark:border-stone-800 dark:bg-stone-950/50 dark:hover:border-stone-600 dark:hover:bg-stone-900',
                      !isCurrentMonth && 'opacity-45',
                    )}
                  >
                    <span className="block text-sm font-semibold text-stone-900 dark:text-stone-100">
                      {date.getDate()}
                    </span>
                    <span
                      className={cn(
                        'mt-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium',
                        effectiveWorking
                          ? 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200'
                          : 'bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-300',
                      )}
                    >
                      {effectiveWorking ? 'Раб.' : 'Вых.'}
                    </span>
                  </button>
                )
              })}
            </div>
          </section>

          <aside className="space-y-4">
            <section className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">
                    {formatDateLong(selectedDate)}
                  </h2>
                  <p className="text-sm text-stone-500 dark:text-stone-400">
                    {selectedOverride ? 'Переопределение даты' : `По шаблону: ${selectedTemplate.label}`}
                  </p>
                  {!selectedDateEditable ? (
                    <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
                      Редактирование доступно начиная с завтра.
                    </p>
                  ) : null}
                </div>
                {selectedOverride ? (
                  <button
                    type="button"
                    disabled={!selectedDateEditable}
                    onClick={() =>
                      setDraftOverrides((currentDraft) => {
                        const current = currentDraft ?? overrides
                        return current.filter((override) => override.date !== selectedDate)
                      })
                    }
                    className="rounded-lg border border-stone-200 px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
                  >
                    Сбросить
                  </button>
                ) : null}
              </div>

              <div className="space-y-4">
                <label className="flex items-center justify-between gap-3 rounded-lg border border-stone-200 bg-stone-50 px-3 py-3 dark:border-stone-700 dark:bg-stone-950/50">
                  <span>
                    <span className="block text-sm font-medium text-stone-900 dark:text-stone-100">Рабочий день</span>
                    <span className="text-xs text-stone-500 dark:text-stone-400">Переопределяет шаблон недели</span>
                  </span>
                  <input
                    type="checkbox"
                    checked={selectedEffective.isWorking}
                    disabled={!selectedDateEditable}
                    onChange={(event) =>
                      upsertOverride({
                        date: selectedDate,
                        isWorking: event.target.checked,
                        ranges: event.target.checked ? rangeOrDefault(selectedEffective.ranges) : [],
                        note: selectedOverride?.note,
                      })
                    }
                    className="h-5 w-5 accent-teal-600 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                </label>

                <RangeEditor
                  disabled={!selectedEffective.isWorking || !selectedDateEditable}
                  ranges={selectedEffective.ranges}
                  onChange={(ranges) =>
                    upsertOverride({
                      date: selectedDate,
                      isWorking: true,
                      ranges,
                      note: selectedOverride?.note,
                    })
                  }
                />

                <label className="block">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Заметка</span>
                  <input
                    value={selectedOverride?.note ?? ''}
                    disabled={!selectedDateEditable}
                    onChange={(event) =>
                      upsertOverride({
                        date: selectedDate,
                        isWorking: selectedEffective.isWorking,
                        ranges: selectedEffective.ranges,
                        note: event.target.value,
                      })
                    }
                    placeholder="Например: отпуск, учеба, дополнительный день"
                    className={cn(fieldClass, 'mt-1 w-full disabled:opacity-50')}
                  />
                </label>
              </div>
            </section>

            <section className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Исключения</h2>
                  <p className="text-xs text-stone-500 dark:text-stone-400">Только будущие даты</p>
                </div>
                <span className="rounded-full bg-stone-100 px-2 py-1 text-xs font-medium text-stone-600 dark:bg-stone-800 dark:text-stone-300">
                  {futureOverrides.length}
                </span>
              </div>
              <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
                {futureOverrides.map((override) => (
                  <button
                    key={override.date}
                    type="button"
                    onClick={() => {
                      const date = parseDateInput(override.date)
                      setSelectedDate(override.date)
                      setMonthAnchor(new Date(date.getFullYear(), date.getMonth(), 1))
                    }}
                    className="flex w-full items-center justify-between gap-3 rounded-lg border border-stone-200 px-3 py-2 text-left transition hover:bg-stone-50 dark:border-stone-700 dark:hover:bg-stone-800/60"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-stone-900 dark:text-stone-100">
                        {formatDateLong(override.date)}
                      </span>
                      <span className="block truncate text-xs text-stone-500 dark:text-stone-400">
                        {override.note ?? describeRanges(override.ranges)}
                      </span>
                    </span>
                    <span
                      className={cn(
                        'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                        override.isWorking
                          ? 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200'
                          : 'bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-300',
                      )}
                    >
                      {override.isWorking ? describeRanges(override.ranges) : 'Выходной'}
                    </span>
                  </button>
                ))}
                {futureOverrides.length === 0 ? (
                  <p className="rounded-lg border border-dashed border-stone-200 px-3 py-6 text-center text-sm text-stone-500 dark:border-stone-700 dark:text-stone-400">
                    Будущих исключений пока нет.
                  </p>
                ) : null}
              </div>
            </section>
          </aside>
        </div>
      ) : (
        <section className="space-y-3">
          {weekRules.map((rule) => (
            <div
              key={rule.weekday}
              className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80"
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex min-w-48 items-center gap-3">
                  <div
                    className={cn(
                      'flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-sm font-semibold',
                      rule.isWorking
                        ? 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200'
                        : 'bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-300',
                    )}
                  >
                    {rule.short}
                  </div>
                  <div>
                    <h2 className="font-semibold text-stone-900 dark:text-stone-50">{rule.label}</h2>
                    <p className="text-sm text-stone-500 dark:text-stone-400">
                      {rule.isWorking ? describeRanges(rule.ranges) : 'Выходной по умолчанию'}
                    </p>
                  </div>
                </div>

                <div className="flex-1 space-y-3">
                  <label className="inline-flex items-center gap-2 text-sm font-medium text-stone-700 dark:text-stone-300">
                    <input
                      type="checkbox"
                      checked={rule.isWorking}
                      onChange={(event) =>
                        updateWeekday(rule.weekday, {
                          isWorking: event.target.checked,
                          ranges: event.target.checked ? rangeOrDefault(rule.ranges) : [],
                        })
                      }
                      className="h-5 w-5 accent-teal-600"
                    />
                    Рабочий день
                  </label>
                  <RangeEditor
                    disabled={!rule.isWorking}
                    ranges={rule.ranges}
                    onChange={(ranges) => updateWeekday(rule.weekday, { ranges })}
                  />
                </div>

                <button
                  type="button"
                  onClick={() => updateWeekday(rule.weekday, { isWorking: true, ranges: [{ start: '10:00', end: '18:00' }] })}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-stone-200 px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
                >
                  <IconCopy className="h-4 w-4" />
                  10-18
                </button>
              </div>
            </div>
          ))}
        </section>
      )}

      {conflictDialogOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
          role="dialog"
          aria-modal="true"
          aria-labelledby="schedule-conflict-title"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setConflictDialogOpen(false)
            }
          }}
        >
          <div className="w-full max-w-md rounded-xl border border-stone-200 bg-white p-5 shadow-xl dark:border-stone-700 dark:bg-stone-900">
            <h2 id="schedule-conflict-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
              Есть записи вне нового расписания
            </h2>
            <p className="mt-2 text-sm leading-6 text-stone-600 dark:text-stone-400">
              Эти изменения затрагивают уже назначенные будущие записи. Сначала договоритесь с клиентами и перенесите
              записи, после этого расписание можно будет сохранить.
            </p>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => setConflictDialogOpen(false)}
                className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400"
              >
                Понятно
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
