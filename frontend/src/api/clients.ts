import { apiFetch } from './client'

export type ClientWithLink = {
  client: {
    id: string
    display_name: string
    phone: string | null
    email: string | null
  }
  link: { id: string; alias: string | null; notes: string | null; invitation_status: string }
}

export type PaginatedClients = {
  items: ClientWithLink[]
  total: number
  page: number
  page_size: number
}

export async function clientsListApi(params?: { page?: number; page_size?: number }) {
  const sp = new URLSearchParams()
  if (params?.page != null) {
    sp.set('page', String(params.page))
  }
  if (params?.page_size != null) {
    sp.set('page_size', String(params.page_size))
  }
  const qs = sp.toString()
  return apiFetch<PaginatedClients>(`/api/clients${qs ? `?${qs}` : ''}`)
}

export async function clientsGetApi(clientId: string) {
  return apiFetch<ClientWithLink>(`/api/clients/${clientId}`)
}

export async function clientsCreateApi(body: { display_name: string; phone?: string; email?: string }) {
  return apiFetch<ClientWithLink>('/api/clients', { method: 'POST', body: JSON.stringify(body) })
}

export type ClientPatchBody = {
  display_name?: string
  phone?: string | null
  email?: string | null
  notes?: string | null
  alias?: string | null
}

export async function clientsPatchApi(clientId: string, body: ClientPatchBody) {
  return apiFetch<ClientWithLink>(`/api/clients/${clientId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function clientsDeleteApi(clientId: string) {
  return apiFetch<void>(`/api/clients/${clientId}`, { method: 'DELETE' })
}
