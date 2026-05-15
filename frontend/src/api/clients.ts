import { apiFetch } from './client'

export type ClientDto = {
  client: {
    id: string
    display_name: string
    phone: string | null
    email: string | null
  }
  link: { id: string; alias: string | null; notes: string | null; invitation_status: string }
}

export async function clientsListApi() {
  return apiFetch<ClientDto[]>('/api/clients')
}

export async function clientsCreateApi(body: { display_name: string; phone?: string; email?: string }) {
  return apiFetch<ClientDto>('/api/clients', { method: 'POST', body: JSON.stringify(body) })
}
