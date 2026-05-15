import { apiFetch } from './client'

export async function availabilityApi(params: {
  master_id: string
  service_id: string
  date: string // YYYY-MM-DD
}) {
  const qs = new URLSearchParams({
    master_id: params.master_id,
    service_id: params.service_id,
    date: params.date,
  })
  return apiFetch<{ start_at: string }[]>(`/api/availability?${qs}`)
}
