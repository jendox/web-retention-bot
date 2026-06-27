import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { meApi } from '../../api/auth'
import { bookingsMyListApi, type BookingClientListItem } from '../../api/bookings'
import { clientsMyMastersApi, type ClientMyMasterItem } from '../../api/clients'
import { blocksCalendar, isBookingUpcoming } from '../../lib/bookingStatus'
import { normalizeTimeZone } from '../../lib/timezones'
import {
  buildClientCabinetMocks,
  clientDashboardUsesMocks,
  type ClientMasterView,
  type MockBookableService,
} from '../../mocks/clientCabinetMocks'
import { computeOverviewStats } from './clientCabinetFormat'
import { ClientCabinetContext, type ClientCabinetContextValue, type VisitManageState } from './clientCabinetContext'
import { ClientBookingModal } from './ClientBookingModal'
import { ClientDemoBookingModal } from './ClientDemoBookingModal'
import { ClientVisitManageModal } from './ClientVisitManageModal'

const EMPTY_BOOKINGS: BookingClientListItem[] = []
const EMPTY_MASTERS: ClientMasterView[] = []

export function ClientCabinetProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const useMocks = clientDashboardUsesMocks()
  const mockBundle = useMemo(() => (useMocks ? buildClientCabinetMocks() : null), [useMocks])

  const [mockBookingExtras, setMockBookingExtras] = useState<BookingClientListItem[]>([])
  const [bookingModalOpen, setBookingModalOpen] = useState(false)
  const [bookingModalMasterId, setBookingModalMasterId] = useState<string | null>(null)
  const [bookingModalNonce, setBookingModalNonce] = useState(0)
  const [visitManage, setVisitManage] = useState<VisitManageState | null>(null)
  const [bookingCreatedNotice, setBookingCreatedNotice] = useState<BookingClientListItem | null>(null)
  const [masterOverrides, setMasterOverrides] = useState<Record<string, ClientMyMasterItem>>({})

  const showBookingCreatedNotice = useCallback((booking: BookingClientListItem) => {
    setBookingCreatedNotice(booking)
  }, [])

  const clearBookingCreatedNotice = useCallback(() => {
    setBookingCreatedNotice(null)
  }, [])

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const clientTimeZone = normalizeTimeZone(me.data?.client_timezone)
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

  const updateLinkedMaster = useCallback(
    (updatedMaster: ClientMyMasterItem) => {
      setMasterOverrides((current) => ({
        ...current,
        [updatedMaster.master_id]: updatedMaster,
      }))
      queryClient.setQueryData<ClientMyMasterItem[]>(['clients', 'me', 'masters'], (current) =>
        current?.map((master) => (master.master_id === updatedMaster.master_id ? updatedMaster : master)),
      )
      void queryClient.invalidateQueries({ queryKey: ['clients', 'me', 'masters'] })
    },
    [queryClient],
  )

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
    const baseMasters = useMocks ? (mockBundle?.masters ?? EMPTY_MASTERS) : (myMastersLive.data ?? EMPTY_MASTERS)
    if (useMocks) {
      return baseMasters
    }
    return baseMasters.map((master) => masterOverrides[master.master_id] ?? master)
  }, [masterOverrides, mockBundle, myMastersLive.data, useMocks])

  const bookableServices = useMemo<MockBookableService[]>(
    () => (useMocks ? (mockBundle?.bookableServices ?? []) : []),
    [mockBundle, useMocks],
  )

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
        clientTimeZone,
      )
    }
    const items = (bookingsOverview.data?.items ?? []).slice(0, 6)
    return computeOverviewStats(items, bookingsOverview.data?.total ?? 0, clientTimeZone)
  }, [bookingsOverview.data, clientTimeZone, mockBookings, useMocks])

  const overviewLoading = !useMocks && (bookingsOverview.isLoading || myMastersLive.isLoading)
  const dataError = !useMocks && (bookingsOverview.isError || myMastersLive.isError)

  const value = useMemo(
    (): ClientCabinetContextValue => ({
      useMocks,
      me: me.data,
      meLoading: me.isLoading,
      clientTimeZone,
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
      bookingCreatedNotice,
      showBookingCreatedNotice,
      clearBookingCreatedNotice,
      invalidateCabinetData,
      updateLinkedMaster,
    }),
    [
      useMocks,
      me.data,
      me.isLoading,
      clientTimeZone,
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
      bookingCreatedNotice,
      showBookingCreatedNotice,
      clearBookingCreatedNotice,
      invalidateCabinetData,
      updateLinkedMaster,
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
            showBookingCreatedNotice(b)
          }}
        />
      ) : null}

      {bookingModalOpen && !useMocks && masters.length > 0 ? (
        <ClientBookingModal
          key={bookingModalNonce}
          onClose={() => setBookingModalOpen(false)}
          masters={masters as ClientMyMasterItem[]}
          clientTimeZone={clientTimeZone}
          initialMasterId={bookingModalMasterId}
          onSuccess={(booking) => {
            invalidateCabinetData()
            showBookingCreatedNotice(booking)
          }}
        />
      ) : null}

      {visitManage && !useMocks ? (
        <ClientVisitManageModal
          booking={visitManage.booking}
          mode={visitManage.mode}
          clientTimeZone={clientTimeZone}
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
