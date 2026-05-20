/** Shared client types and re-exports from client/master API modules. */

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
  client_alias: string | null
  contact_email: string | null
  contact_phone: string | null
  telegram: string | null
  viber: string | null
}

export function clientMasterLabel(master: Pick<ClientMyMasterItem, 'client_alias' | 'display_name'>) {
  const alias = master.client_alias?.trim()
  return alias || master.display_name
}

export type ClientPatchBody = {
  display_name?: string
  phone?: string | null
  email?: string | null
  notes?: string | null
  alias?: string | null
}

export {
  clientsMyMastersApi,
  clientsMyMasterPatchApi,
  clientsMyMasterServicesApi,
} from './client/masters'

export {
  clientsListApi,
  clientsGetApi,
  clientsCreateApi,
  clientsPatchApi,
  clientsDeleteApi,
} from './master/clients'
