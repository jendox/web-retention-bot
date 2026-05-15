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
  invite_kind: 'open' | 'client'
  master_record_has_email: boolean
}

export async function invitationGetApi(token: string) {
  return apiFetch<InvitationLanding>(`/api/invitations/${token}`)
}

export async function invitationAcceptApi(token: string, body: { display_name: string; phone?: string | null }) {
  return apiFetch<{ client_id: string; email_mismatch_with_master_record: boolean }>(
    `/api/invitations/${token}/accept`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
  )
}

export type InvitationCreated = {
  token: string
  expires_at: string
  target_email: string | null
  target_client_id: string | null
}

export async function invitationsCreateApi(body: {
  expires_hours?: number
  target_email?: string | null
  target_client_id?: string | null
  replace?: boolean
}) {
  return apiFetch<InvitationCreated>('/api/invitations', { method: 'POST', body: JSON.stringify(body) })
}
