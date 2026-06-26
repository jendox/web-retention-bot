import { apiFetch } from '../client'

export type AnalyticsPeriod = 'month' | 'last30' | 'previous'

export type AnalyticsPeriodPreset = 'current_month' | 'last_30_days' | 'previous_month'

export type AnalyticsMoney = {
  currency: string
  revenue: string
  average_check: string
  lost_revenue: string
}

export type AnalyticsDailyMoney = {
  currency: string
  revenue: string
}

export type AnalyticsRevenuePoint = {
  date: string
  label: string
  completed_count: number
  money: AnalyticsDailyMoney[]
}

export type AnalyticsServiceMoney = {
  currency: string
  revenue: string
  average_check: string
}

export type AnalyticsService = {
  service_id: string
  name: string
  completed_count: number
  cancelled_count: number
  no_show_count: number
  revenue_share_percent: number
  money: AnalyticsServiceMoney[]
}

export type AnalyticsReturnClientMoney = {
  currency: string
  revenue: string
}

export type AnalyticsReturnClient = {
  client_id: string
  display_name: string
  last_visit_at: string
  days_since_last_visit: number
  completed_count: number
  note: string
  money: AnalyticsReturnClientMoney[]
}

export type AnalyticsOccupancy = {
  percent: number
  available_minutes: number
  booked_minutes: number
  available_hours: string
  booked_hours: string
}

export type MasterAnalytics = {
  period: {
    preset: AnalyticsPeriodPreset | null
    from_date: string
    to_date: string
    timezone: string
    range_start: string
    range_end: string
    label: string
  }
  display_currency: string
  summary: {
    completed_count: number
    cancelled_count: number
    no_show_count: number
    unique_clients: number
    new_clients: number
    repeat_clients: number
  }
  occupancy: AnalyticsOccupancy
  money: AnalyticsMoney[]
  revenue_by_day: AnalyticsRevenuePoint[]
  services: AnalyticsService[]
  clients_to_return: AnalyticsReturnClient[]
}

const periodToPreset: Record<AnalyticsPeriod, AnalyticsPeriodPreset> = {
  month: 'current_month',
  last30: 'last_30_days',
  previous: 'previous_month',
}

export async function masterAnalyticsApi(period: AnalyticsPeriod) {
  const q = new URLSearchParams({ period: periodToPreset[period] })
  return apiFetch<MasterAnalytics>(`/api/master/analytics?${q}`)
}
