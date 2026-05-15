import { apiFetch } from './client'

export type Service = {
  id: string
  master_id: string
  name: string
  description: string | null
  duration_min: number
  price: string
  currency: string
  is_active: boolean
  sort_order: number
}

export async function servicesListApi() {
  return apiFetch<Service[]>('/api/services')
}

export type ServicePayload = {
  name: string
  description?: string | null
  duration_min: number
  price: string
  currency: string
  is_active?: boolean
  sort_order?: number
}

export async function servicesCreateApi(body: ServicePayload) {
  return apiFetch<Service>('/api/services', { method: 'POST', body: JSON.stringify(body) })
}

export async function serviceUpdateApi(id: string, body: Partial<ServicePayload>) {
  return apiFetch<Service>(`/api/services/${id}`, { method: 'PUT', body: JSON.stringify(body) })
}

export async function serviceDeleteApi(id: string) {
  await apiFetch(`/api/services/${id}`, { method: 'DELETE' })
}
