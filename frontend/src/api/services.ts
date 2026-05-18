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

export type PaginatedServices = {
  items: Service[]
  total: number
  page: number
  page_size: number
}

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
  return apiFetch<PaginatedServices>(`/api/services${qs ? `?${qs}` : ''}`)
}

export type ServiceCreatePayload = {
  name: string
  description?: string | null
  duration_min: number
  price: string
  currency?: string | null
  is_active?: boolean
  sort_order?: number
}

export async function servicesCreateApi(body: ServiceCreatePayload) {
  return apiFetch<Service>('/api/services', { method: 'POST', body: JSON.stringify(body) })
}

export async function servicePatchApi(id: string, body: Partial<ServiceCreatePayload>) {
  return apiFetch<Service>(`/api/services/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function serviceDeleteApi(id: string) {
  return apiFetch<void>(`/api/services/${id}`, { method: 'DELETE' })
}
