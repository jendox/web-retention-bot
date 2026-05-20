import { apiFetch } from '../client'
import type { ClientPatchBody, ClientWithLink, PaginatedClients } from '../clients'

export type { ClientWithLink, PaginatedClients, ClientPatchBody }

export async function clientsListApi(params?: { page?: number; page_size?: number; q?: string }) {
  const sp = new URLSearchParams()
  if (params?.page != null) {
    sp.set('page', String(params.page))
  }
  if (params?.page_size != null) {
    sp.set('page_size', String(params.page_size))
  }
  if (params?.q) {
    sp.set('q', params.q)
  }
  const qs = sp.toString()
  return apiFetch<PaginatedClients>(`/api/master/clients${qs ? `?${qs}` : ''}`)
}

export async function clientsGetApi(clientId: string) {
  return apiFetch<ClientWithLink>(`/api/master/clients/${clientId}`)
}

export async function clientsCreateApi(body: { display_name: string; phone?: string; email?: string }) {
  return apiFetch<ClientWithLink>('/api/master/clients', { method: 'POST', body: JSON.stringify(body) })
}

export async function clientsPatchApi(clientId: string, body: ClientPatchBody) {
  return apiFetch<ClientWithLink>(`/api/master/clients/${clientId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function clientsDeleteApi(clientId: string) {
  return apiFetch<void>(`/api/master/clients/${clientId}`, { method: 'DELETE' })
}
