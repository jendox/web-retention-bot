import { apiFetch } from '../client'
import type { Service } from '../services'
import type { ClientMyMasterItem } from '../clients'

export type { ClientMyMasterItem }

export async function clientsMyMastersApi() {
  return apiFetch<ClientMyMasterItem[]>('/api/client/masters')
}

export async function clientsMyMasterPatchApi(masterId: string, body: { client_alias?: string | null }) {
  return apiFetch<ClientMyMasterItem>(`/api/client/masters/${masterId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function clientsMyMasterServicesApi(masterId: string) {
  return apiFetch<Service[]>(`/api/client/masters/${masterId}/services`)
}
