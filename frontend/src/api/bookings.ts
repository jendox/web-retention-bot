import { apiFetch } from './client'

export type PaginatedBookings = {
  items: Booking[]
  total: number
  page: number
  page_size: number
}

export type Booking = {
  id: string
  master_id: string
  client_id: string
  service_id: string
  start_at: string
  end_at: string
  duration_min: number
  price_snapshot: string
  currency_snapshot: string
  status: string
  attendance_confirmed_at?: string | null
  cancel_comment?: string | null
  reschedule_comment?: string | null
}

export const BOOKING_COMMENT_MAX_LENGTH = 500

export type BookingClientListItem = Booking & {
  master_display_name: string
  service_name: string
}

export type BookingListScope = 'upcoming' | 'history'

export type PaginatedClientBookings = {
  items: BookingClientListItem[]
  total: number
  page: number
  page_size: number
}

export async function bookingsMyListApi(params: {
  scope: BookingListScope
  page: number
  page_size: number
}) {
  const q = new URLSearchParams({
    scope: params.scope,
    page: String(params.page),
    page_size: String(params.page_size),
  })
  return apiFetch<PaginatedClientBookings>(`/api/bookings/me?${q}`)
}

export async function bookingsMyCreateApi(body: {
  master_id: string
  service_id: string
  start_at: string
}) {
  return apiFetch<BookingClientListItem>('/api/bookings/me', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function bookingsMyCancelApi(bookingId: string, comment?: string | null) {
  const trimmed = comment?.trim()
  await apiFetch(`/api/bookings/me/${bookingId}/cancel`, {
    method: 'POST',
    body: JSON.stringify(trimmed ? { comment: trimmed } : {}),
  })
}

export async function bookingsMyRescheduleApi(bookingId: string, start_at: string, comment?: string | null) {
  const trimmed = comment?.trim()
  return apiFetch<BookingClientListItem>(`/api/bookings/me/${bookingId}/reschedule`, {
    method: 'POST',
    body: JSON.stringify({
      start_at,
      ...(trimmed ? { comment: trimmed } : {}),
    }),
  })
}

export async function bookingsListApi(params: {
  scope: BookingListScope
  page: number
  page_size: number
  client_id?: string
  service_id?: string
}) {
  const q = new URLSearchParams({
    scope: params.scope,
    page: String(params.page),
    page_size: String(params.page_size),
  })
  if (params.client_id) {
    q.set('client_id', params.client_id)
  }
  if (params.service_id) {
    q.set('service_id', params.service_id)
  }
  return apiFetch<PaginatedBookings>(`/api/bookings?${q}`)
}

export async function bookingsCreateApi(body: {
  client_id: string
  service_id: string
  start_at: string
}) {
  return apiFetch<Booking>('/api/bookings', { method: 'POST', body: JSON.stringify(body) })
}

export async function bookingsCancelApi(id: string, comment?: string | null) {
  const trimmed = comment?.trim()
  await apiFetch(`/api/bookings/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify(trimmed ? { comment: trimmed } : {}),
  })
}

export async function bookingsRescheduleApi(id: string, start_at: string, comment?: string | null) {
  const trimmed = comment?.trim()
  return apiFetch<Booking>(`/api/bookings/${id}/reschedule`, {
    method: 'POST',
    body: JSON.stringify({
      start_at,
      ...(trimmed ? { comment: trimmed } : {}),
    }),
  })
}

export async function bookingsMarkAttendanceApi(id: string, attended: boolean) {
  return apiFetch<Booking>(`/api/bookings/${id}/attendance`, {
    method: 'POST',
    body: JSON.stringify({ attended }),
  })
}
