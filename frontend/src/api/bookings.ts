import { apiFetch } from './client'

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
}

export async function bookingsListApi() {
  return apiFetch<Booking[]>('/api/bookings')
}

export async function bookingsCreateApi(body: {
  client_id: string
  service_id: string
  start_at: string
  invite_token?: string | null
}) {
  return apiFetch<Booking>('/api/bookings', { method: 'POST', body: JSON.stringify(body) })
}

export async function bookingsCancelApi(id: string) {
  await apiFetch(`/api/bookings/${id}/cancel`, { method: 'POST' })
}

export async function bookingsRescheduleApi(id: string, start_at: string) {
  return apiFetch<Booking>(`/api/bookings/${id}/reschedule`, {
    method: 'POST',
    body: JSON.stringify({ start_at }),
  })
}
