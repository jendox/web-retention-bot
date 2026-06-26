import { useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { masterAnalyticsApi, type AnalyticsPeriod } from '../api/master/analytics'
import { SegmentTabs } from '../components/ui/SegmentTabs'
import { cn } from '../lib/forms'
import { surfaceCard, surfacePanel } from '../lib/surface'

type TrendPoint = {
  label: string
  revenue: number
  visits: number
}

type ServiceMetric = {
  id: string
  name: string
  revenue: number
  visits: number
  averageCheck: number
  share: number
  missed: number
}

type ReturnClient = {
  id: string
  name: string
  lastVisit: string
  visits: number
  revenue: number
  note: string
}

type AnalyticsSnapshot = {
  label: string
  currency: string
  summary: {
    revenue: number
    completed: number
    averageCheck: number
    newClients: number
    repeatClients: number
    cancelled: number
    noShow: number
    occupancy: number
    bookedHours: number
    availableHours: number
    lostRevenue: number
  }
  revenueByDay: TrendPoint[]
  services: ServiceMetric[]
  clientsToReturn: ReturnClient[]
}

const periodTabs: { value: AnalyticsPeriod; label: string }[] = [
  { value: 'month', label: 'Текущий месяц' },
  { value: 'last30', label: '30 дней' },
  { value: 'previous', label: 'Прошлый месяц' },
]

function parseAmount(value: string | undefined) {
  const parsed = Number.parseFloat(value ?? '')
  return Number.isFinite(parsed) ? parsed : 0
}

function formatMoney(value: number, currency: string) {
  return `${value.toLocaleString('ru-RU')} ${currency}`
}

function pickCurrencyValue<T extends { currency: string }>(
  values: T[],
  currency: string,
  selector: (value: T) => string,
) {
  const selected = values.find((value) => value.currency === currency) ?? values[0]
  return selected ? parseAmount(selector(selected)) : 0
}

function toSnapshot(data: Awaited<ReturnType<typeof masterAnalyticsApi>>): AnalyticsSnapshot {
  const currency = data.display_currency
  const summaryMoney = data.money.find((money) => money.currency === currency) ?? data.money[0]

  return {
    label: data.period.label,
    currency,
    summary: {
      revenue: parseAmount(summaryMoney?.revenue),
      completed: data.summary.completed_count,
      averageCheck: parseAmount(summaryMoney?.average_check),
      newClients: data.summary.new_clients,
      repeatClients: data.summary.repeat_clients,
      cancelled: data.summary.cancelled_count,
      noShow: data.summary.no_show_count,
      occupancy: data.occupancy.percent,
      bookedHours: parseAmount(data.occupancy.booked_hours),
      availableHours: parseAmount(data.occupancy.available_hours),
      lostRevenue: parseAmount(summaryMoney?.lost_revenue),
    },
    revenueByDay: data.revenue_by_day.map((point) => ({
      label: point.label,
      revenue: pickCurrencyValue(point.money, currency, (money) => money.revenue),
      visits: point.completed_count,
    })),
    services: data.services.map((service) => ({
      id: service.service_id,
      name: service.name,
      revenue: pickCurrencyValue(service.money, currency, (money) => money.revenue),
      visits: service.completed_count,
      averageCheck: pickCurrencyValue(service.money, currency, (money) => money.average_check),
      share: service.revenue_share_percent,
      missed: service.cancelled_count + service.no_show_count,
    })),
    clientsToReturn: data.clients_to_return.map((client) => ({
      id: client.client_id,
      name: client.display_name,
      lastVisit: `${client.days_since_last_visit} дн. назад`,
      visits: client.completed_count,
      revenue: pickCurrencyValue(client.money, currency, (money) => money.revenue),
      note: client.note,
    })),
  }
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

function RevenueChart({ points, currency }: { points: TrendPoint[]; currency: string }) {
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
                  title={`${point.label}: ${formatMoney(point.revenue, currency)}, визитов: ${point.visits}`}
                />
              </div>
              <span className="text-[11px] text-stone-500 dark:text-stone-400">{point.label}</span>
            </div>
          )
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-stone-500 dark:text-stone-400">
        <span>Пик: {formatMoney(max, currency)}</span>
        <span>Дней с визитами: {points.filter((p) => p.visits > 0).length}</span>
      </div>
    </div>
  )
}

function ServicesTable({ services, currency }: { services: ServiceMetric[]; currency: string }) {
  if (services.length === 0) {
    return (
      <p className="mt-5 rounded-lg border border-dashed border-stone-300 px-4 py-6 text-sm text-stone-500 dark:border-stone-700 dark:text-stone-400">
        За выбранный период нет завершенных, отмененных или пропущенных записей по услугам.
      </p>
    )
  }

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
          key={service.id}
          className="grid grid-cols-[minmax(0,1.4fr)_0.8fr_0.7fr] gap-3 border-t border-stone-200 px-4 py-3 text-sm dark:border-stone-700 sm:grid-cols-[minmax(0,1.4fr)_0.7fr_0.7fr_0.7fr]"
        >
          <div className="min-w-0">
            <p className="truncate font-medium text-stone-900 dark:text-stone-100">{service.name}</p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-stone-200 dark:bg-stone-800">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${service.share}%` }} />
            </div>
            <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">{service.share}% выручки</p>
          </div>
          <span className="font-medium text-stone-900 dark:text-stone-100">{formatMoney(service.revenue, currency)}</span>
          <span className="text-stone-600 dark:text-stone-300">{service.visits}</span>
          <span className="hidden text-stone-600 dark:text-stone-300 sm:block">{formatMoney(service.averageCheck, currency)}</span>
        </div>
      ))}
    </div>
  )
}

function ReturnClients({ clients, currency }: { clients: ReturnClient[]; currency: string }) {
  if (clients.length === 0) {
    return (
      <p className="mt-5 rounded-lg border border-dashed border-stone-300 px-4 py-6 text-sm text-stone-500 dark:border-stone-700 dark:text-stone-400">
        Пока нет клиентов, которые подходят под условия возврата.
      </p>
    )
  }

  return (
    <div className="mt-5 space-y-3">
      {clients.map((client) => (
        <Link
          key={client.id}
          to={`/master/clients/${client.id}`}
          className="block rounded-lg border border-stone-200 p-3 transition hover:border-teal-300 hover:bg-teal-50/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-stone-700 dark:hover:border-teal-700 dark:hover:bg-teal-950/20"
        >
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
            <span>{formatMoney(client.revenue, currency)}</span>
          </div>
        </Link>
      ))}
    </div>
  )
}

export function AnalyticsPage() {
  const [period, setPeriod] = useState<AnalyticsPeriod>('month')
  const analytics = useQuery({
    queryKey: ['master', 'analytics', period],
    queryFn: () => masterAnalyticsApi(period),
  })
  const data = useMemo(() => (analytics.data ? toSnapshot(analytics.data) : null), [analytics.data])

  const totalVisits = useMemo(
    () => (data ? data.summary.completed + data.summary.cancelled + data.summary.noShow : 0),
    [data],
  )

  if (analytics.isError) {
    return (
      <div className={surfacePanel('p-5')}>
        <h1 className="text-lg font-semibold text-stone-950 dark:text-stone-50">Аналитика недоступна</h1>
        <p className="mt-2 text-sm text-stone-500 dark:text-stone-400">
          Не удалось загрузить данные. Обновите страницу или попробуйте позже.
        </p>
      </div>
    )
  }

  if (analytics.isLoading || !data) {
    return <p className="text-stone-500 dark:text-stone-400">Загрузка аналитики…</p>
  }

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
        <KpiCard
          label="Выручка"
          value={formatMoney(data.summary.revenue, data.currency)}
          detail={data.label}
          tone="teal"
        />
        <KpiCard
          label="Завершенные визиты"
          value={String(data.summary.completed)}
          detail={`из ${totalVisits} записей`}
          tone="emerald"
        />
        <KpiCard
          label="Средний чек"
          value={formatMoney(data.summary.averageCheck, data.currency)}
          detail="по завершенным визитам"
          tone="violet"
        />
        <KpiCard
          label="Заполненность"
          value={`${data.summary.occupancy}%`}
          detail={`${data.summary.bookedHours.toLocaleString('ru-RU')} из ${data.summary.availableHours.toLocaleString('ru-RU')} ч`}
          tone="amber"
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(320px,0.8fr)]">
        <div className={surfacePanel('p-5')}>
          <PanelHeader title="Динамика выручки" aside={`${data.currency}, по дате визита`} />
          <RevenueChart points={data.revenueByDay} currency={data.currency} />
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
              <p className="mt-1 text-xl font-semibold text-amber-800 dark:text-amber-200">
                {formatMoney(data.summary.lostRevenue, data.currency)}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
        <div className={surfacePanel('p-5')}>
          <PanelHeader title="Услуги по выручке" aside="по snapshot-ценам записей" />
          <ServicesTable services={data.services} currency={data.currency} />
        </div>

        <div className={surfacePanel('p-5')}>
          <PanelHeader title="Клиенты на возврат" aside="2+ визита, без будущей записи" />
          <ReturnClients clients={data.clientsToReturn} currency={data.currency} />
        </div>
      </section>
    </div>
  )
}
