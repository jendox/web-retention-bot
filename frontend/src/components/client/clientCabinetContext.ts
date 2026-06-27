import { createContext, useContext } from 'react'

import type { AuthUser } from '../../api/auth'
import type { BookingClientListItem } from '../../api/bookings'
import type { ClientMyMasterItem } from '../../api/clients'
import type { ClientMasterView, MockBookableService } from '../../mocks/clientCabinetMocks'
import type { computeOverviewStats } from './clientCabinetFormat'

export type VisitManageState = {
  booking: BookingClientListItem
  mode: 'reschedule' | 'cancel'
}

export type ClientCabinetContextValue = {
  useMocks: boolean
  me: AuthUser | undefined
  meLoading: boolean
  clientTimeZone: string
  firstName: string
  masters: ClientMasterView[] | ClientMyMasterItem[]
  bookableServices: MockBookableService[]
  mockBookings: BookingClientListItem[]
  stats: ReturnType<typeof computeOverviewStats>
  overviewLoading: boolean
  dataError: boolean
  bookingsOverviewError: unknown
  myMastersError: unknown
  linkedMasterCount: number
  openBookingModal: (masterId: string | null) => void
  canManageVisit: (b: BookingClientListItem) => boolean
  setVisitManage: (state: VisitManageState | null) => void
  bookingCreatedNotice: BookingClientListItem | null
  showBookingCreatedNotice: (booking: BookingClientListItem) => void
  clearBookingCreatedNotice: () => void
  invalidateCabinetData: () => void
  updateLinkedMaster: (updatedMaster: ClientMyMasterItem) => void
}

export const ClientCabinetContext = createContext<ClientCabinetContextValue | null>(null)

export function useClientCabinet() {
  const ctx = useContext(ClientCabinetContext)
  if (!ctx) {
    throw new Error('useClientCabinet must be used within ClientCabinetProvider')
  }
  return ctx
}
