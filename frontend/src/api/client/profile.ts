import { apiFetch } from '../client'

export type ClientProfile = {
  id: string
  display_name: string
  phone: string | null
  email: string | null
  timezone: string
  user_id: string | null
}

export type ClientProfileUpdate = {
  display_name?: string
  phone?: string | null
  timezone?: string
}

export async function clientProfileGetApi() {
  return apiFetch<ClientProfile>('/api/client/profile')
}

export async function clientProfilePatchApi(body: ClientProfileUpdate) {
  return apiFetch<ClientProfile>('/api/client/profile', {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}
