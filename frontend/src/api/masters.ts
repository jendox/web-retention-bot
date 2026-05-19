import { apiFetch } from './client'

export type MasterProfile = {
  id: string
  display_name: string
  public_slug: string | null
  timezone: string
  default_currency: string
}

export async function masterMeApi() {
  return apiFetch<MasterProfile>('/api/masters/me')
}

export type ScheduleInterval = {
  start_time: string
  end_time: string
}

export type SchedulePayload = {
  weekly_days: { weekday: number; is_closed: boolean; intervals: ScheduleInterval[]; note?: string | null }[]
  date_overrides: {
    schedule_date: string
    is_closed: boolean
    intervals: ScheduleInterval[]
    note?: string | null
  }[]
}

export async function getScheduleApi() {
  return apiFetch<SchedulePayload>('/api/masters/me/schedule')
}

export async function putScheduleApi(body: SchedulePayload) {
  return apiFetch<SchedulePayload>('/api/masters/me/schedule', {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}
