import { apiFetch } from '../client'

export type MasterProfile = {
  id: string
  display_name: string
  public_slug: string | null
  timezone: string
  default_currency: string
  contact_email: string | null
  contact_phone: string | null
  telegram: string | null
  viber: string | null
}

export type MasterProfileUpdate = {
  display_name?: string
  public_slug?: string | null
  timezone?: string
  default_currency?: string
  contact_email?: string | null
  contact_phone?: string | null
  telegram?: string | null
  viber?: string | null
}

export async function masterMeApi() {
  return apiFetch<MasterProfile>('/api/master/profile')
}

export async function masterMeUpdateApi(body: MasterProfileUpdate) {
  return apiFetch<MasterProfile>('/api/master/profile', {
    method: 'PUT',
    body: JSON.stringify(body),
  })
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
  return apiFetch<SchedulePayload>('/api/master/schedule')
}

export async function putScheduleApi(body: SchedulePayload) {
  return apiFetch<SchedulePayload>('/api/master/schedule', {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}
