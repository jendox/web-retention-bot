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

export type SchedulePayload = {
  weekly_rules: { weekday: number; start_time: string; end_time: string }[]
  overrides: {
    override_date: string
    is_closed: boolean
    start_time?: string | null
    end_time?: string | null
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
