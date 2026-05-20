import { apiFetch } from '../client'
import type { PaginatedServices, Service, ServiceCreatePayload } from '../services'

export type { PaginatedServices, Service, ServiceCreatePayload }
export type ServiceUpdate = Partial<ServiceCreatePayload>

export async function servicesListApi(params?: {
  page?: number
  page_size?: number
  is_active?: boolean | null
  q?: string
}) {
  const sp = new URLSearchParams()
  if (params?.page != null) {
    sp.set('page', String(params.page))
  }
  if (params?.page_size != null) {
    sp.set('page_size', String(params.page_size))
  }
  if (params?.is_active === true) {
    sp.set('is_active', 'true')
  }
  if (params?.is_active === false) {
    sp.set('is_active', 'false')
  }
  if (params?.q) {
    sp.set('q', params.q)
  }
  const qs = sp.toString()
  return apiFetch<PaginatedServices>(`/api/master/services${qs ? `?${qs}` : ''}`)
}

export async function servicesCreateApi(body: ServiceCreatePayload) {
  return apiFetch<Service>('/api/master/services', { method: 'POST', body: JSON.stringify(body) })
}

export async function servicesUpdateApi(id: string, body: ServiceUpdate) {
  return apiFetch<Service>(`/api/master/services/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function servicesDeleteApi(id: string) {
  return apiFetch<void>(`/api/master/services/${id}`, { method: 'DELETE' })
}
