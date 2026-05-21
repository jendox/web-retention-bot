import { useMemo, useState, type ReactNode } from 'react'

import { SegmentTabs } from '../components/ui/SegmentTabs'
import { cn } from '../lib/forms'
import { surfaceCard, surfacePanel } from '../lib/surface'

type Period = 'month' | 'last30' | 'previous'

type TrendPoint = {
  label: string
  revenue: number
  visits: number
}

type ServiceMetric = {
  name: string
  revenue: number
  visits: number
  averageCheck: number
  share: number
  missed: number
}

type ReturnClient = {
  name: string
  lastVisit: string
  visits: number
  revenue: number
  note: string
}

type AnalyticsSnapshot = {
  label: string
  summary: {
    revenue: number
    completed: number
    averageCheck: number
    newClients: number
    repeatClients: number
    cancelled: number
    noShow: number
    occupancy: number
    lostRevenue: number
  }
  revenueByDay: TrendPoint[]
  services: ServiceMetric[]
  clientsToReturn: ReturnClient[]
}

const periodTabs: { value: Period; label: string }[] = [
  { value: 'month', label: 'Текущий месяц' },
  { value: 'last30', label: '30 дней' },
  { value: 'previous', label: 'Прошлый месяц' },
]

const snapshots: Record<Period, AnalyticsSnapshot> = {
  month: {
    label: '1-21 мая',
    summary: {
      revenue: 2840,
      completed: 37,
      averageCheck: 77,
      newClients: 9,
      repeatClients: 21,
      cancelled: 5,
      noShow: 2,
      occupancy: 68,
      lostRevenue: 180,
    },
    revenueByDay: [
      { label: '1', revenue: 120, visits: 2 },
      { label: '2', revenue: 0, visits: 0 },
      { label: '3', revenue: 260, visits: 4 },
      { label: '4', revenue: 180, visits: 2 },
      { label: '5', revenue: 320, visits: 5 },
      { label: '6', revenue: 90, visits: 1 },
      { label: '7', revenue: 210, visits: 3 },
      { label: '8', revenue: 280, visits: 4 },
      { label: '9', revenue: 160, visits: 2 },
      { label: '10', revenue: 340, visits: 5 },
      { label: '11', revenue: 110, visits: 2 },
      { label: '12', revenue: 230, visits: 3 },
      { label: '13', revenue: 0, visits: 0 },
      { label: '14', revenue: 290, visits: 4 },
      { label: '15', revenue: 250, visits: 3 },
    ],
    services: [
      { name: 'Окрашивание и уход', revenue: 920, visits: 8, averageCheck: 115, share: 32, missed: 1 },
      { name: 'Стрижка женская', revenue: 690, visits: 10, averageCheck: 69, share: 24, missed: 0 },
      { name: 'Маникюр с покрытием', revenue: 580, visits: 11, averageCheck: 53, share: 20, missed: 2 },
      { name: 'Коррекция бровей', revenue: 310, visits: 6, averageCheck: 52, share: 11, missed: 0 },
    ],
    clientsToReturn: [
      { name: 'Анна Кравцова', lastVisit: '46 дней назад', visits: 5, revenue: 420, note: 'часто выбирала окрашивание' },
      { name: 'Мария Соколова', lastVisit: '58 дней назад', visits: 3, revenue: 210, note: 'последний визит без новой записи' },
      { name: 'Екатерина Ли', lastVisit: '72 дня назад', visits: 4, revenue: 300, note: 'высокий средний чек' },
    ],
  },
  last30: {
    label: 'последние 30 дней',
    summary: {
      revenue: 4120,
      completed: 54,
      averageCheck: 76,
      newClients: 13,
      repeatClients: 31,
      cancelled: 8,
      noShow: 3,
      occupancy: 72,
      lostRevenue: 265,
    },
    revenueByDay: [
      { label: '1', revenue: 160, visits: 2 },
      { label: '3', revenue: 220, visits: 3 },
      { label: '5', revenue: 310, visits: 4 },
      { label: '7', revenue: 150, visits: 2 },
      { label: '9', revenue: 430, visits: 6 },
      { label: '11', revenue: 260, visits: 3 },
      { label: '13', revenue: 380, visits: 5 },
      { label: '15', revenue: 190, visits: 2 },
      { label: '17', revenue: 360, visits: 5 },
      { label: '19', revenue: 250, visits: 4 },
      { label: '21', revenue: 510, visits: 7 },
      { label: '23', revenue: 290, visits: 4 },
      { label: '25', revenue: 340, visits: 4 },
      { label: '27', revenue: 180, visits: 2 },
      { label: '29', revenue: 680, visits: 9 },
    ],
    services: [
      { name: 'Окрашивание и уход', revenue: 1420, visits: 12, averageCheck: 118, share: 34, missed: 1 },
      { name: 'Стрижка женская', revenue: 1020, visits: 15, averageCheck: 68, share: 25, missed: 1 },
      { name: 'Маникюр с покрытием', revenue: 830, visits: 16, averageCheck: 52, share: 20, missed: 2 },
      { name: 'Коррекция бровей', revenue: 390, visits: 8, averageCheck: 49, share: 9, missed: 0 },
    ],
    clientsToReturn: [
      { name: 'Анна Кравцова', lastVisit: '46 дней назад', visits: 5, revenue: 420, note: 'часто выбирала окрашивание' },
      { name: 'Ольга Нестерова', lastVisit: '51 день назад', visits: 6, revenue: 360, note: 'регулярные записи по пятницам' },
      { name: 'Екатерина Ли', lastVisit: '72 дня назад', visits: 4, revenue: 300, note: 'высокий средний чек' },
    ],
  },
  previous: {
    label: 'апрель',
    summary: {
      revenue: 3680,
      completed: 48,
      averageCheck: 77,
      newClients: 11,
      repeatClients: 28,
      cancelled: 6,
      noShow: 4,
      occupancy: 64,
      lostRevenue: 340,
    },
    revenueByDay: [
      { label: '1', revenue: 210, visits: 3 },
      { label: '3', revenue: 170, visits: 2 },
      { label: '5', revenue: 300, visits: 4 },
      { label: '7', revenue: 120, visits: 2 },
      { label: '9', revenue: 260, visits: 3 },
      { label: '11', revenue: 410, visits: 5 },
      { label: '13', revenue: 280, visits: 4 },
      { label: '15', revenue: 190, visits: 2 },
      { label: '17', revenue: 340, visits: 4 },
      { label: '19', revenue: 220, visits: 3 },
      { label: '21', revenue: 390, visits: 5 },
      { label: '23', revenue: 180, visits: 2 },
      { label: '25', revenue: 260, visits: 3 },
      { label: '27', revenue: 450, visits: 6 },
      { label: '29', revenue: 300, visits: 4 },
    ],
    services: [
      { name: 'Окрашивание и уход', revenue: 1280, visits: 11, averageCheck: 116, share: 35, missed: 2 },
      { name: 'Стрижка женская', revenue: 890, visits: 13, averageCheck: 68, share: 24, missed: 1 },
      { name: 'Маникюр с покрытием', revenue: 760, visits: 15, averageCheck: 51, share: 21, missed: 1 },
      { name: 'Коррекция бровей', revenue: 360, visits: 7, averageCheck: 51, share: 10, missed: 0 },
    ],
    clientsToReturn: [
      { name: 'Мария Соколова', lastVisit: '58 дней назад', visits: 3, revenue: 210, note: 'последний визит без новой записи' },
      { name: 'Ирина Павлова', lastVisit: '63 дня назад', visits: 4, revenue: 245, note: 'две отмены подряд' },
      { name: 'Екатерина Ли', lastVisit: '72 дня назад', visits: 4, revenue: 300, note: 'высокий средний чек' },
    ],
  },
}

function formatMoney(value: number) {
  return `${value.toLocaleString('ru-RU')} BYN`
}

function KpiCard({
  label,
  value,
  detail,
  tone,
}: {
  label: string
  value: string
  detail: string
  tone: 'teal' | 'emerald' | 'amber' | 'violet'
}) {
  const dotClass = {
    teal: 'bg-teal-500',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    violet: 'bg-violet-500',
  }[tone]

  return (
    <div className={surfaceCard('p-4')}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm text-stone-500 dark:text-stone-400">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-stone-950 dark:text-stone-50">{value}</p>
          <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">{detail}</p>
        </div>
        <span className={cn('mt-1 h-2.5 w-2.5 shrink-0 rounded-full', dotClass)} />
      </div>
    </div>
  )
}

function PanelHeader({ title, aside }: { title: string; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <h2 className="text-base font-semibold text-stone-950 dark:text-stone-50">{title}</h2>
      {aside ? <div className="text-sm text-stone-500 dark:text-stone-400">{aside}</div> : null}
    </div>
  )
}

function RevenueChart({ points }: { points: TrendPoint[] }) {
  const max = Math.max(...points.map((p) => p.revenue), 1)

  return (
    <div className="mt-6">
      <div className="flex h-56 items-end gap-2 rounded-lg border border-stone-200 bg-stone-50 px-3 py-4 dark:border-stone-700 dark:bg-stone-950/40">
        {points.map((point) => {
          const height = Math.max((point.revenue / max) * 100, point.revenue > 0 ? 8 : 2)
          return (
            <div key={point.label} className="flex min-w-0 flex-1 flex-col items-center gap-2">
              <div className="flex h-44 w-full items-end">
                <div
                  className="w-full rounded-t-md bg-teal-500/85 transition hover:bg-teal-600 dark:bg-teal-400/75 dark:hover:bg-teal-300"
                  style={{ height: `${height}%` }}
                  title={`${point.label}: ${formatMoney(point.revenue)}, визитов: ${point.visits}`}
                />
              </div>
              <span className="text-[11px] text-stone-500 dark:text-stone-400">{point.label}</span>
            </div>
          )
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-stone-500 dark:text-stone-400">
        <span>Пик: {formatMoney(max)}</span>
        <span>Дней с визитами: {points.filter((p) => p.visits > 0).length}</span>
      </div>
    </div>
  )
}

function ServicesTable({ services }: { services: ServiceMetric[] }) {
  return (
    <div className="mt-5 overflow-hidden rounded-lg border border-stone-200 dark:border-stone-700">
      <div className="grid grid-cols-[minmax(0,1.4fr)_0.8fr_0.7fr] gap-3 bg-stone-50 px-4 py-2 text-xs font-semibold uppercase text-stone-500 dark:bg-stone-950/50 dark:text-stone-400 sm:grid-cols-[minmax(0,1.4fr)_0.7fr_0.7fr_0.7fr]">
        <span>Услуга</span>
        <span>Выручка</span>
        <span>Визиты</span>
        <span className="hidden sm:block">Средний чек</span>
      </div>
      {services.map((service) => (
        <div
          key={service.name}
          className="grid grid-cols-[minmax(0,1.4fr)_0.8fr_0.7fr] gap-3 border-t border-stone-200 px-4 py-3 text-sm dark:border-stone-700 sm:grid-cols-[minmax(0,1.4fr)_0.7fr_0.7fr_0.7fr]"
        >
          <div className="min-w-0">
            <p className="truncate font-medium text-stone-900 dark:text-stone-100">{service.name}</p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-stone-200 dark:bg-stone-800">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${service.share}%` }} />
            </div>
            <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">{service.share}% выручки</p>
          </div>
          <span className="font-medium text-stone-900 dark:text-stone-100">{formatMoney(service.revenue)}</span>
          <span className="text-stone-600 dark:text-stone-300">{service.visits}</span>
          <span className="hidden text-stone-600 dark:text-stone-300 sm:block">{formatMoney(service.averageCheck)}</span>
        </div>
      ))}
    </div>
  )
}

function ReturnClients({ clients }: { clients: ReturnClient[] }) {
  return (
    <div className="mt-5 space-y-3">
      {clients.map((client) => (
        <div key={client.name} className="rounded-lg border border-stone-200 p-3 dark:border-stone-700">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="font-medium text-stone-900 dark:text-stone-100">{client.name}</p>
              <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">{client.note}</p>
            </div>
            <span className="shrink-0 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-900 dark:bg-amber-950/70 dark:text-amber-200">
              {client.lastVisit}
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-stone-500 dark:text-stone-400">
            <span>{client.visits} визитов</span>
            <span>{formatMoney(client.revenue)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

export function AnalyticsPage() {
  const [period, setPeriod] = useState<Period>('month')
  const data = snapshots[period]

  const totalVisits = useMemo(
    () => data.summary.completed + data.summary.cancelled + data.summary.noShow,
    [data],
  )

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-teal-700 dark:text-teal-300">Кабинет мастера</p>
          <h1 className="mt-1 text-2xl font-semibold text-stone-950 dark:text-stone-50 sm:text-3xl">Аналитика</h1>
          <p className="mt-2 max-w-2xl text-sm text-stone-500 dark:text-stone-400">
            Финансы, услуги и клиенты за выбранный период.
          </p>
        </div>
        <SegmentTabs tabs={periodTabs} value={period} onChange={setPeriod} ariaLabel="Период аналитики" />
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Выручка" value={formatMoney(data.summary.revenue)} detail={data.label} tone="teal" />
        <KpiCard label="Завершенные визиты" value={String(data.summary.completed)} detail={`из ${totalVisits} записей`} tone="emerald" />
        <KpiCard label="Средний чек" value={formatMoney(data.summary.averageCheck)} detail="по завершенным визитам" tone="violet" />
        <KpiCard label="Заполненность" value={`${data.summary.occupancy}%`} detail="моковый расчет доступных часов" tone="amber" />
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(320px,0.8fr)]">
        <div className={surfacePanel('p-5')}>
          <PanelHeader title="Динамика выручки" aside="BYN, по дате визита" />
          <RevenueChart points={data.revenueByDay} />
        </div>

        <div className={surfacePanel('p-5')}>
          <PanelHeader title="Клиенты" aside={data.label} />
          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-stone-50 p-4 dark:bg-stone-950/40">
              <p className="text-sm text-stone-500 dark:text-stone-400">Новые</p>
              <p className="mt-2 text-2xl font-semibold text-stone-950 dark:text-stone-50">{data.summary.newClients}</p>
            </div>
            <div className="rounded-lg bg-stone-50 p-4 dark:bg-stone-950/40">
              <p className="text-sm text-stone-500 dark:text-stone-400">Повторные</p>
              <p className="mt-2 text-2xl font-semibold text-stone-950 dark:text-stone-50">{data.summary.repeatClients}</p>
            </div>
          </div>
          <div className="mt-5 rounded-lg border border-stone-200 p-4 dark:border-stone-700">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm text-stone-500 dark:text-stone-400">Отмены</span>
              <span className="font-semibold text-stone-950 dark:text-stone-50">{data.summary.cancelled}</span>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <span className="text-sm text-stone-500 dark:text-stone-400">Неявки</span>
              <span className="font-semibold text-stone-950 dark:text-stone-50">{data.summary.noShow}</span>
            </div>
            <div className="mt-4 border-t border-stone-200 pt-4 dark:border-stone-700">
              <p className="text-sm text-stone-500 dark:text-stone-400">Потенциально потеряно</p>
              <p className="mt-1 text-xl font-semibold text-amber-800 dark:text-amber-200">{formatMoney(data.summary.lostRevenue)}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
        <div className={surfacePanel('p-5')}>
          <PanelHeader title="Услуги по выручке" aside="по snapshot-ценам записей" />
          <ServicesTable services={data.services} />
        </div>

        <div className={surfacePanel('p-5')}>
          <PanelHeader title="Клиенты на возврат" aside="моковый сегмент" />
          <ReturnClients clients={data.clientsToReturn} />
        </div>
      </section>
    </div>
  )
}
