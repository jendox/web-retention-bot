import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { meApi } from '../../api/auth'
import { bookingsMyListApi, type BookingClientListItem } from '../../api/bookings'
import { clientsMyMastersApi, type ClientMyMasterItem } from '../../api/clients'
import { blocksCalendar, isBookingUpcoming } from '../../lib/bookingStatus'
import {
  buildClientCabinetMocks,
  clientDashboardUsesMocks,
  type ClientMasterView,
  type MockBookableService,
} from '../../mocks/clientCabinetMocks'
import { computeOverviewStats } from './clientCabinetUi'
import { ClientBookingModal } from './ClientBookingModal'
import { ClientDemoBookingModal } from './ClientDemoBookingModal'
import { ClientVisitManageModal } from './ClientVisitManageModal'

const EMPTY_BOOKINGS: BookingClientListItem[] = []
const EMPTY_MASTERS: ClientMasterView[] = []

type VisitManageState = {
  booking: BookingClientListItem
  mode: 'reschedule' | 'cancel'
}

type ClientCabinetContextValue = {
  useMocks: boolean
  me: ReturnType<typeof useQuery<Awaited<ReturnType<typeof meApi>>>>['data']
  meLoading: boolean
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
  bookingSuccessNotice: boolean
  demoBookingNotice: boolean
  invalidateCabinetData: () => void
}

const ClientCabinetContext = createContext<ClientCabinetContextValue | null>(null)

export function useClientCabinet() {
  const ctx = useContext(ClientCabinetContext)
  if (!ctx) {
    throw new Error('useClientCabinet must be used within ClientCabinetProvider')
  }
  return ctx
}

export function ClientCabinetProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const useMocks = clientDashboardUsesMocks()
  const mockBundle = useMemo(() => (useMocks ? buildClientCabinetMocks() : null), [useMocks])

  const [mockBookingExtras, setMockBookingExtras] = useState<BookingClientListItem[]>([])
  const [bookingModalOpen, setBookingModalOpen] = useState(false)
  const [bookingModalMasterId, setBookingModalMasterId] = useState<string | null>(null)
  const [bookingModalNonce, setBookingModalNonce] = useState(0)
  const [demoBookingNotice, setDemoBookingNotice] = useState(false)
  const [visitManage, setVisitManage] = useState<VisitManageState | null>(null)
  const [bookingSuccessNotice, setBookingSuccessNotice] = useState(false)

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const bookingsOverview = useQuery({
    queryKey: ['bookings', 'me', 'overview', 'upcoming'],
    queryFn: () => bookingsMyListApi({ scope: 'upcoming', page: 1, page_size: 10 }),
    enabled: !useMocks && me.isSuccess,
    retry: false,
  })
  const myMastersLive = useQuery({
    queryKey: ['clients', 'me', 'masters'],
    queryFn: clientsMyMastersApi,
    enabled: !useMocks && me.isSuccess,
    retry: false,
  })

  const invalidateCabinetData = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['bookings', 'me'] })
    void queryClient.invalidateQueries({ queryKey: ['notifications', 'me'] })
    void queryClient.invalidateQueries({ queryKey: ['availability'] })
  }, [queryClient])

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  const mockBookings = useMemo(() => {
    const base = mockBundle?.bookings ?? EMPTY_BOOKINGS
    return [...base, ...mockBookingExtras]
  }, [mockBookingExtras, mockBundle])

  const masters = useMemo((): ClientMasterView[] | ClientMyMasterItem[] => {
    if (useMocks) {
      return mockBundle?.masters ?? EMPTY_MASTERS
    }
    return myMastersLive.data ?? EMPTY_MASTERS
  }, [mockBundle, myMastersLive.data, useMocks])

  const bookableServices: MockBookableService[] = useMocks ? (mockBundle?.bookableServices ?? []) : []

  const openBookingModal = useCallback((masterId: string | null) => {
    setBookingModalNonce((n) => n + 1)
    setBookingModalMasterId(masterId)
    setBookingModalOpen(true)
  }, [])

  const canManageVisit = useCallback((b: BookingClientListItem) => isBookingUpcoming(b, new Date()), [])

  const firstName = useMemo(() => {
    const name = me.data?.client_display_name?.trim()
    if (name) {
      return name.split(/\s+/)[0] ?? name
    }
    return me.data?.email?.split('@')[0] ?? 'Вы'
  }, [me.data?.client_display_name, me.data?.email])

  const stats = useMemo(() => {
    if (useMocks) {
      return computeOverviewStats(
        mockBookings.filter((b) => isBookingUpcoming(b, new Date())),
        mockBookings.filter((b) => blocksCalendar(b.status)).length,
      )
    }
    const items = (bookingsOverview.data?.items ?? []).slice(0, 6)
    return computeOverviewStats(items, bookingsOverview.data?.total ?? 0)
  }, [bookingsOverview.data, mockBookings, useMocks])

  const overviewLoading = !useMocks && (bookingsOverview.isLoading || myMastersLive.isLoading)
  const dataError = !useMocks && (bookingsOverview.isError || myMastersLive.isError)

  const value = useMemo(
    (): ClientCabinetContextValue => ({
      useMocks,
      me: me.data,
      meLoading: me.isLoading,
      firstName,
      masters,
      bookableServices,
      mockBookings,
      stats,
      overviewLoading,
      dataError,
      bookingsOverviewError: bookingsOverview.error,
      myMastersError: myMastersLive.error,
      linkedMasterCount: masters.length,
      openBookingModal,
      canManageVisit,
      setVisitManage,
      bookingSuccessNotice,
      demoBookingNotice,
      invalidateCabinetData,
    }),
    [
      useMocks,
      me.data,
      me.isLoading,
      firstName,
      masters,
      bookableServices,
      mockBookings,
      stats,
      overviewLoading,
      dataError,
      bookingsOverview.error,
      myMastersLive.error,
      openBookingModal,
      canManageVisit,
      bookingSuccessNotice,
      demoBookingNotice,
      invalidateCabinetData,
    ],
  )

  if (me.isLoading || !me.data) {
    return <p className="text-stone-500 dark:text-stone-400">Загрузка…</p>
  }

  return (
    <ClientCabinetContext.Provider value={value}>
      {children}

      {bookingModalOpen && useMocks ? (
        <ClientDemoBookingModal
          key={bookingModalNonce}
          onClose={() => setBookingModalOpen(false)}
          masters={masters as ClientMasterView[]}
          services={bookableServices}
          existingBookings={mockBookings}
          initialMasterId={bookingModalMasterId}
          onConfirm={(b) => {
            setMockBookingExtras((prev) => [...prev, b])
            setDemoBookingNotice(true)
            window.setTimeout(() => setDemoBookingNotice(false), 4500)
          }}
        />
      ) : null}

      {bookingModalOpen && !useMocks && masters.length > 0 ? (
        <ClientBookingModal
          key={bookingModalNonce}
          onClose={() => setBookingModalOpen(false)}
          masters={masters as ClientMyMasterItem[]}
          initialMasterId={bookingModalMasterId}
          onSuccess={() => {
            invalidateCabinetData()
            setBookingSuccessNotice(true)
            window.setTimeout(() => setBookingSuccessNotice(false), 4500)
          }}
        />
      ) : null}

      {visitManage && !useMocks ? (
        <ClientVisitManageModal
          booking={visitManage.booking}
          mode={visitManage.mode}
          onClose={() => setVisitManage(null)}
          onSuccess={() => {
            invalidateCabinetData()
            setVisitManage(null)
          }}
        />
      ) : null}
    </ClientCabinetContext.Provider>
  )
}
