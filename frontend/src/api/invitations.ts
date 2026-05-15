import { apiFetch } from './client'
import type { Service } from './services'

export type InvitationLanding = {
  master_display_name: string
  timezone: string
  token: string
  expires_at: string
  accepted_at: string | null
  linked_client_id: string | null
  services: Service[]
}

export async function invitationGetApi(token: string) {
  return apiFetch<InvitationLanding>(`/api/invitations/${token}`)
}

export async function invitationAcceptApi(
  token: string,
  body: { display_name: string; phone?: string; email?: string },
) {
  return apiFetch<{ client_id: string }>(`/api/invitations/${token}/accept`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function invitationsCreateApi(body: { expires_hours?: number; target_email?: string }) {
  return apiFetch<{ token: string; expires_at: string; target_email: string | null }>(
    '/api/invitations',
    { method: 'POST', body: JSON.stringify(body) },
  )
}
