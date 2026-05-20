import { apiFetch } from './client'
import type { Service } from './services'

export type ClientBookingStats = {
  no_show_count: number
  completed_count: number
}

export type ClientWithLink = {
  client: {
    id: string
    display_name: string
    phone: string | null
    email: string | null
    user_id?: string | null
  }
  link: {
    id: string
    alias: string | null
    notes: string | null
    invitation_status: string
    linked_account_email?: string | null
    invite_email_mismatch?: boolean
  }
  booking_stats?: ClientBookingStats
}

export type PaginatedClients = {
  items: ClientWithLink[]
  total: number
  page: number
  page_size: number
}

export type ClientMyMasterItem = {
  master_id: string
  display_name: string
  public_slug: string | null
  link_id: string
  invitation_status: string
  client_id: string
  client_display_name: string
  alias: string | null
  contact_email: string
}

export async function clientsMyMastersApi() {
  return apiFetch<ClientMyMasterItem[]>('/api/clients/me/masters')
}

export async function clientsMyMasterServicesApi(masterId: string) {
  return apiFetch<Service[]>(`/api/clients/me/masters/${masterId}/services`)
}

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
