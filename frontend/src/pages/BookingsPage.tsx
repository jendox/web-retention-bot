import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { availabilityApi } from '../api/availability'
import { meApi } from '../api/auth'
import {
  bookingsCancelApi,
  bookingsCreateApi,
  bookingsListApi,
  bookingsMarkAttendanceApi,
  bookingsRescheduleApi,
  type Booking,
  type BookingListScope,
} from '../api/bookings'
import { clientsCreateApi, clientsGetApi, clientsListApi, type ClientWithLink } from '../api/clients'
import { servicesListApi, type Service } from '../api/services'
import { IconReschedule, IconTrash } from '../components/booking/bookingActionIcons'
import { SegmentTabs } from '../components/ui/SegmentTabs'
import { useMasterMe } from '../hooks/useMasterMe'
import { getUserFacingError } from '../lib/apiErrors'
import { bookingSlotButtonClass } from '../lib/bookingSlots'
import { cn } from '../lib/forms'
import {
  blocksCalendar,
  bookingStatusBadgeClass,
  bookingStatusLabel,
  needsAttendanceConfirmation,
} from '../lib/bookingStatus'
import { ALLOWED_PAGE_SIZES, parsePage, parsePageSize, type PageSize } from '../lib/pagination'

type ClientSource = 'existing' | 'new'

const SEARCH_PAGE_SIZE = 10
const MIN_SEARCH_LENGTH = 2
const BOOKING_MAX_ADVANCE_DAYS = 90
const BOOKING_LOOKUP_PAGE_SIZE = ALLOWED_PAGE_SIZES[ALLOWED_PAGE_SIZES.length - 1]

const fieldClass =
  'w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none transition focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:focus:border-stone-500'

const sourceTabs: { value: ClientSource; label: string }[] = [
  { value: 'existing', label: 'Из базы' },
  { value: 'new', label: 'Новый' },
]

const listScopeTabs: { value: BookingListScope; label: string }[] = [
  { value: 'upcoming', label: 'Текущие' },
  { value: 'history', label: 'История' },
]

function parseListScope(param: string | null): BookingListScope {
  return param === 'history' ? 'history' : 'upcoming'
}

function toDateInputValue(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addDays(date: Date, days: number) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

const dateLongFormatter = new Intl.DateTimeFormat('ru-RU', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})

function formatDateLong(date: Date) {
  return dateLongFormatter.format(date)
}

function formatPreviewDate(dateInput: string) {
  if (!dateInput) {
    return 'Дата не выбрана'
  }
  const [year, month, day] = dateInput.split('-').map(Number)
  return formatDateLong(new Date(year, month - 1, day))
}

function formatSlotTime(value: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatBookingDateTime(value: string) {
  const date = new Date(value)
  return `${formatDateLong(date)}, ${formatSlotTime(value)}`
}

function formatSlotFull(value: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatMoney(service: Service) {
  return `${service.price} ${service.currency}`
}

function clientDisplayName(item: ClientWithLink) {
  return item.link.alias?.trim() || item.client.display_name
}

function clientContactLine(item: ClientWithLink) {
  const bits = [item.client.phone, item.client.email].filter(Boolean)
  return bits.length > 0 ? bits.join(' · ') : 'контакты не указаны'
}

function cabinetLabel(item: ClientWithLink) {
  return item.client.user_id ? 'кабинет подключен' : 'без кабинета'
}

function IconCalendarSmall(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3M5 11h14M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}

function IconPlus(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
    </svg>
  )
}

function IconSearch(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35m1.35-5.15a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z" />
    </svg>
  )
}

function IconCheckCircle(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

function IconThumbUp(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M7.493 18.75c-.425 0-.82-.236-1.023-.544l-1.09-1.637a.75.75 0 00-1.049-.15l-.194.145a.75.75 0 01-.824 0l-.194-.145a.75.75 0 00-1.049.15l-1.09 1.637A1.125 1.125 0 013.75 18.75H3v-7.82a3 3 0 011.183-2.39l5.48-4.035a1.125 1.125 0 011.678 0l5.48 4.035A3 3 0 0121 10.93V18.75h-.75zM12 4.5v12.75"
      />
    </svg>
  )
}

function IconXCircle(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

export function BookingsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const prefillClientId = searchParams.get('client_id') ?? ''
  const listClientId = searchParams.get('list_client_id') ?? ''
  const listServiceId = searchParams.get('list_service_id') ?? ''
  const listScope = parseListScope(searchParams.get('scope'))
  const page = parsePage(searchParams.get('page'))
  const pageSize = parsePageSize(searchParams.get('page_size'))
  const listFiltersActive = Boolean(listClientId || listServiceId)

  const setListScope = (scope: BookingListScope) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('scope', scope)
      n.set('page', '1')
      n.set('page_size', String(pageSize))
      return n
    })
  }

  const setPage = (p: number) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('page', String(p))
      n.set('page_size', String(pageSize))
      if (!n.get('scope')) {
        n.set('scope', listScope)
      }
      return n
    })
  }

  const setPageSize = (ps: PageSize) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('page', '1')
      n.set('page_size', String(ps))
      if (!n.get('scope')) {
        n.set('scope', listScope)
      }
      return n
    })
  }

  const setListClientId = (clientId: string) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('page', '1')
      if (clientId) {
        n.set('list_client_id', clientId)
      } else {
        n.delete('list_client_id')
      }
      return n
    })
  }

  const setListServiceId = (serviceId: string) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('page', '1')
      if (serviceId) {
        n.set('list_service_id', serviceId)
      } else {
        n.delete('list_service_id')
      }
      return n
    })
  }

  const clearListFilters = () => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.delete('list_client_id')
      n.delete('list_service_id')
      n.set('page', '1')
      return n
    })
  }

  const [clientSource, setClientSource] = useState<ClientSource>('existing')
  const [clientSearch, setClientSearch] = useState('')
  const [selectedClient, setSelectedClient] = useState<ClientWithLink | null>(null)
  const [draftName, setDraftName] = useState('')
  const [draftPhone, setDraftPhone] = useState('')
  const [draftEmail, setDraftEmail] = useState('')
  const [serviceSearch, setServiceSearch] = useState('')
  const [selectedService, setSelectedService] = useState<Service | null>(null)
  const [selectedDate, setSelectedDate] = useState(() => toDateInputValue(new Date()))
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null)
  const [bookingSuccess, setBookingSuccess] = useState<{
    booking: Booking
    clientName: string
    serviceName: string
  } | null>(null)
  const bookingSuccessRef = useRef<HTMLDivElement>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [rescheduleBooking, setRescheduleBooking] = useState<Booking | null>(null)
  const [rescheduleDate, setRescheduleDate] = useState(() => toDateInputValue(new Date()))
  const [rescheduleSlot, setRescheduleSlot] = useState<string | null>(null)
  const [bookingActionError, setBookingActionError] = useState<string | null>(null)
  const [pendingCancel, setPendingCancel] = useState<Booking | null>(null)

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useMasterMe(me.isSuccess)
  const prefilledClient = useQuery({
    queryKey: ['client', prefillClientId],
    queryFn: () => clientsGetApi(prefillClientId),
    enabled: me.isSuccess && Boolean(prefillClientId),
  })

  const clientSearchTerm = clientSearch.trim()
  const serviceSearchTerm = serviceSearch.trim()
  const shouldSearchClients = clientSearchTerm.length >= MIN_SEARCH_LENGTH
  const shouldSearchServices = serviceSearchTerm.length >= MIN_SEARCH_LENGTH
  const todayValue = toDateInputValue(new Date())
  const maxDateValue = toDateInputValue(addDays(new Date(), BOOKING_MAX_ADVANCE_DAYS))

  const clients = useQuery({
    queryKey: ['clients', 'booking-form-search', clientSearchTerm, SEARCH_PAGE_SIZE],
    queryFn: () => clientsListApi({ page: 1, page_size: SEARCH_PAGE_SIZE, q: clientSearchTerm }),
    enabled: me.isSuccess && shouldSearchClients,
  })
  const clientLookup = useQuery({
    queryKey: ['clients', 'booking-list-lookup', 1, BOOKING_LOOKUP_PAGE_SIZE],
    queryFn: () => clientsListApi({ page: 1, page_size: BOOKING_LOOKUP_PAGE_SIZE }),
    enabled: me.isSuccess,
  })
  const services = useQuery({
    queryKey: ['services', 'booking-form-search', serviceSearchTerm, SEARCH_PAGE_SIZE, 'active'],
    queryFn: () => servicesListApi({ page: 1, page_size: SEARCH_PAGE_SIZE, is_active: true, q: serviceSearchTerm }),
    enabled: me.isSuccess && shouldSearchServices,
  })
  const serviceLookup = useQuery({
    queryKey: ['services', 'booking-list-lookup', 1, BOOKING_LOOKUP_PAGE_SIZE],
    queryFn: () => servicesListApi({ page: 1, page_size: BOOKING_LOOKUP_PAGE_SIZE }),
    enabled: me.isSuccess,
  })
  const bookings = useQuery({
    queryKey: ['bookings', listScope, page, pageSize, listClientId, listServiceId],
    queryFn: () =>
      bookingsListApi({
        scope: listScope,
        page,
        page_size: pageSize,
        client_id: listClientId || undefined,
        service_id: listServiceId || undefined,
      }),
    enabled: me.isSuccess,
  })
  const prefilled = selectedClient ?? prefilledClient.data ?? null
  const clientReady = clientSource === 'new' ? draftName.trim().length > 0 : prefilled != null
  const slots = useQuery({
    queryKey: ['availability', master.data?.id, selectedService?.id, selectedDate],
    queryFn: () =>
      availabilityApi({
        master_id: master.data?.id ?? '',
        service_id: selectedService?.id ?? '',
        date: selectedDate,
      }),
    enabled: me.isSuccess && Boolean(master.data?.id) && clientReady && Boolean(selectedService?.id) && Boolean(selectedDate),
  })

  const rescheduleSlots = useQuery({
    queryKey: ['availability', 'reschedule', master.data?.id, rescheduleBooking?.service_id, rescheduleDate],
    queryFn: () =>
      availabilityApi({
        master_id: master.data?.id ?? '',
        service_id: rescheduleBooking?.service_id ?? '',
        date: rescheduleDate,
      }),
    enabled: me.isSuccess && Boolean(master.data?.id) && Boolean(rescheduleBooking?.service_id) && Boolean(rescheduleDate),
  })

  const resetBookingFormAfterCreate = () => {
    setSelectedSlot(null)
    setSelectedService(null)
    setServiceSearch('')
    setSelectedDate(toDateInputValue(new Date()))
    setDraftName('')
    setDraftPhone('')
    setDraftEmail('')
    if (!prefillClientId) {
      setSelectedClient(null)
      setClientSearch('')
    }
  }

  const ensureUpcomingListVisible = () => {
    if (listScope === 'upcoming' && page === 1) {
      return
    }
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('scope', 'upcoming')
      n.set('page', '1')
      n.set('page_size', String(pageSize))
      return n
    })
  }

  const createBooking = useMutation({
    mutationFn: async () => {
      if (!selectedService || !selectedSlot) {
        throw new Error('Выберите услугу и свободное время.')
      }

      let clientId = prefilled?.client.id ?? null
      if (clientSource === 'new') {
        const displayName = draftName.trim()
        if (!displayName) {
          throw new Error('Укажите имя клиента.')
        }
        const client = await clientsCreateApi({
          display_name: displayName,
          phone: draftPhone.trim() || undefined,
          email: draftEmail.trim() || undefined,
        })
        clientId = client.client.id
      }

      if (!clientId) {
        throw new Error('Выберите клиента.')
      }

      return bookingsCreateApi({
        client_id: clientId,
        service_id: selectedService.id,
        start_at: selectedSlot,
      })
    },
    onSuccess: (booking) => {
      const clientName =
        clientSource === 'new'
          ? draftName.trim() || 'Новый клиент'
          : prefilled
            ? clientDisplayName(prefilled)
            : 'Клиент'
      const serviceName = selectedService?.name ?? 'Услуга'

      setBookingSuccess({ booking, clientName, serviceName })
      setSubmitError(null)
      resetBookingFormAfterCreate()
      setRescheduleBooking(null)
      setRescheduleSlot(null)
      if (document.activeElement instanceof HTMLElement) {
        document.activeElement.blur()
      }
      ensureUpcomingListVisible()
      void queryClient.invalidateQueries({ queryKey: ['bookings'] })
      void queryClient.invalidateQueries({ queryKey: ['clients'] })
      void queryClient.invalidateQueries({ queryKey: ['availability'] })
    },
    onError: (error) => {
      setBookingSuccess(null)
      setSubmitError(getUserFacingError(error))
    },
  })

  const cancelBooking = useMutation({
    mutationFn: (bookingId: string) => bookingsCancelApi(bookingId),
    onSuccess: async () => {
      setBookingActionError(null)
      setRescheduleBooking(null)
      setPendingCancel(null)
      await queryClient.invalidateQueries({ queryKey: ['bookings'] })
    },
    onError: (error) => setBookingActionError(getUserFacingError(error)),
  })

  const reschedule = useMutation({
    mutationFn: async () => {
      if (!rescheduleBooking || !rescheduleSlot) {
        throw new Error('Выберите новое время.')
      }
      return bookingsRescheduleApi(rescheduleBooking.id, rescheduleSlot)
    },
    onSuccess: async () => {
      setBookingActionError(null)
      setRescheduleBooking(null)
      setRescheduleSlot(null)
      await queryClient.invalidateQueries({ queryKey: ['bookings'] })
      await queryClient.invalidateQueries({ queryKey: ['availability'] })
    },
    onError: (error) => setBookingActionError(getUserFacingError(error)),
  })

  const markAttendance = useMutation({
    mutationFn: ({ bookingId, attended }: { bookingId: string; attended: boolean }) =>
      bookingsMarkAttendanceApi(bookingId, attended),
    onSuccess: async () => {
      setBookingActionError(null)
      await queryClient.invalidateQueries({ queryKey: ['bookings'] })
    },
    onError: (error) => setBookingActionError(getUserFacingError(error)),
  })

  useEffect(() => {
    if (me.isError) navigate('/login')
  }, [me.isError, navigate])

  useEffect(() => {
    setRescheduleBooking(null)
    setRescheduleSlot(null)
    setBookingActionError(null)
  }, [listScope])

  useEffect(() => {
    if (!bookingSuccess) {
      return
    }
    bookingSuccessRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    const timer = window.setTimeout(() => setBookingSuccess(null), 12_000)
    return () => window.clearTimeout(timer)
  }, [bookingSuccess])

  const clientItems = clients.data?.items ?? []
  const serviceItems = services.data?.items ?? []
  const clientsError = clients.error instanceof Error ? clients.error.message : null
  const servicesError = services.error instanceof Error ? services.error.message : null
  const slotsError = slots.error instanceof Error ? slots.error.message : null
  const bookingsError = bookings.error instanceof Error ? getUserFacingError(bookings.error) : null
  const rescheduleSlotsError = rescheduleSlots.error instanceof Error ? getUserFacingError(rescheduleSlots.error) : null
  const clientNameById = new Map(
    (clientLookup.data?.items ?? []).map((item) => [item.client.id, clientDisplayName(item)] as const),
  )
  const serviceNameById = new Map((serviceLookup.data?.items ?? []).map((service) => [service.id, service.name] as const))
  const listClientOptions = [...(clientLookup.data?.items ?? [])].sort((a, b) =>
    clientDisplayName(a).localeCompare(clientDisplayName(b), 'ru'),
  )
  const listServiceOptions = [...(serviceLookup.data?.items ?? [])].sort((a, b) =>
    a.name.localeCompare(b.name, 'ru'),
  )
  const bookingItems = Array.isArray(bookings.data?.items) ? bookings.data.items : []
  const bookingsListLoading = bookings.isPending && !bookings.data
  const bookingsTotal = bookings.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(bookingsTotal / pageSize))

  useEffect(() => {
    if (!bookings.isSuccess || !bookings.data) {
      return
    }
    const tp = Math.max(1, Math.ceil(bookings.data.total / pageSize))
    if (page > tp) {
      setPage(tp)
    }
  }, [bookings.isSuccess, bookings.data, page, pageSize])

  const previewClientName =
    clientSource === 'new' ? draftName.trim() || 'Новый клиент' : prefilled ? clientDisplayName(prefilled) : 'Клиент'
  const canPrepare =
    selectedService != null &&
    selectedDate.length > 0 &&
    selectedSlot != null &&
    clientReady

  if (me.isLoading || !me.data) {
    return <p className="text-stone-500 dark:text-stone-400">Загрузка...</p>
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50 sm:text-3xl">
          Новая запись
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-stone-600 dark:text-stone-400">
          Найдите клиента и услугу через поиск или быстро внесите нового клиента прямо из формы записи.
        </p>
      </header>

      {bookingSuccess ? (
        <div
          ref={bookingSuccessRef}
          role="status"
          className="scroll-mt-4 rounded-xl border border-teal-200/90 bg-teal-50/90 p-4 dark:border-teal-900/50 dark:bg-teal-950/40"
        >
          <div className="flex gap-3">
            <IconCheckCircle className="mt-0.5 h-5 w-5 shrink-0 text-teal-700 dark:text-teal-300" />
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-teal-950 dark:text-teal-50">Запись создана</p>
              <p className="mt-1 text-sm text-teal-900/90 dark:text-teal-100/90">
                {bookingSuccess.clientName} · {bookingSuccess.serviceName}
              </p>
              <p className="mt-0.5 text-sm font-medium text-teal-800 dark:text-teal-200">
                {formatBookingDateTime(bookingSuccess.booking.start_at)} · {bookingSuccess.booking.duration_min} мин
              </p>
            </div>
          </div>
        </div>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(21rem,0.72fr)]">
        <section className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80 sm:p-5">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200">
              <IconPlus className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Параметры записи</h2>
              <p className="text-sm text-stone-500 dark:text-stone-400">Выберите клиента, услугу и свободное время</p>
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <p className="mb-2 text-sm font-medium text-stone-700 dark:text-stone-300">Клиент</p>
              <SegmentTabs
                tabs={sourceTabs}
                value={clientSource}
                onChange={(next) => {
                  setClientSource(next)
                  setSelectedSlot(null)
                  setBookingSuccess(null)
                  setSubmitError(null)
                }}
                fullWidth
                className="sm:w-auto"
              />
            </div>

            {clientSource === 'existing' ? (
              <div className="space-y-3">
                {prefilled ? (
                  <div className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-3 dark:border-teal-900/70 dark:bg-teal-950/30">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <p className="font-medium text-stone-900 dark:text-stone-50">{clientDisplayName(prefilled)}</p>
                        <p className="truncate text-sm text-stone-600 dark:text-stone-400">{clientContactLine(prefilled)}</p>
                      </div>
                      <span
                        className={cn(
                          'w-fit shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                          prefilled.client.user_id
                            ? 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200'
                            : 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300',
                        )}
                      >
                        {cabinetLabel(prefilled)}
                      </span>
                    </div>
                  </div>
                ) : null}

                <label className="block">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Поиск клиента</span>
                  <span className="relative mt-1 block">
                    <IconSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
                    <input
                      value={clientSearch}
                      onChange={(event) => {
                        setClientSearch(event.target.value)
                        setSelectedClient(null)
                        setSelectedSlot(null)
                        setBookingSuccess(null)
                        setSubmitError(null)
                      }}
                      className={cn(fieldClass, 'pl-9')}
                      placeholder="Введите минимум 2 символа"
                    />
                  </span>
                </label>

                {clientSearchTerm.length > 0 && !shouldSearchClients ? (
                  <p className="text-sm text-stone-500 dark:text-stone-400">Введите еще символы для поиска по базе.</p>
                ) : null}

                {shouldSearchClients ? (
                  <div className="max-h-72 overflow-y-auto rounded-lg border border-stone-200 dark:border-stone-700">
                    {clients.isLoading ? (
                      <p className="px-3 py-4 text-sm text-stone-500 dark:text-stone-400">Поиск клиентов...</p>
                    ) : clientsError ? (
                      <p className="px-3 py-4 text-sm text-red-700 dark:text-red-300">{clientsError}</p>
                    ) : clientItems.length === 0 ? (
                      <div className="space-y-3 px-3 py-4">
                        <p className="text-sm text-stone-500 dark:text-stone-400">Клиенты не найдены</p>
                        <button
                          type="button"
                          onClick={() => {
                            setClientSource('new')
                            setDraftName(clientSearchTerm)
                            setSelectedSlot(null)
                            setBookingSuccess(null)
                            setSubmitError(null)
                          }}
                          className="rounded-lg border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
                        >
                          Создать нового: {clientSearchTerm}
                        </button>
                      </div>
                    ) : (
                      <div className="divide-y divide-stone-200 dark:divide-stone-800">
                        {clientItems.map((item) => {
                          const checked = prefilled?.client.id === item.client.id
                          return (
                            <button
                              key={item.client.id}
                              type="button"
                              onClick={() => {
                                setSelectedClient(item)
                                setClientSearch(clientDisplayName(item))
                                setSelectedSlot(null)
                                setBookingSuccess(null)
                                setSubmitError(null)
                              }}
                              className={cn(
                                'flex w-full items-start justify-between gap-3 px-3 py-3 text-left transition',
                                checked
                                  ? 'bg-teal-50 dark:bg-teal-950/30'
                                  : 'hover:bg-stone-50 dark:hover:bg-stone-800/60',
                              )}
                            >
                              <span className="min-w-0">
                                <span className="block font-medium text-stone-900 dark:text-stone-50">{clientDisplayName(item)}</span>
                                <span className="block truncate text-sm text-stone-500 dark:text-stone-400">{clientContactLine(item)}</span>
                              </span>
                              <span
                                className={cn(
                                  'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                                  item.client.user_id
                                    ? 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200'
                                    : 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300',
                                )}
                              >
                                {cabinetLabel(item)}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block sm:col-span-2">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Имя клиента *</span>
                  <input
                    value={draftName}
                    onChange={(event) => {
                      setDraftName(event.target.value)
                      setSelectedSlot(null)
                      setBookingSuccess(null)
                      setSubmitError(null)
                    }}
                    className={cn(fieldClass, 'mt-1')}
                    placeholder="Например, Елена Петрова"
                  />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Телефон</span>
                  <input
                    value={draftPhone}
                    onChange={(event) => setDraftPhone(event.target.value)}
                    className={cn(fieldClass, 'mt-1')}
                    placeholder="+375..."
                  />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Email</span>
                  <input
                    value={draftEmail}
                    onChange={(event) => setDraftEmail(event.target.value)}
                    className={cn(fieldClass, 'mt-1')}
                    placeholder="client@example.com"
                  />
                </label>
              </div>
            )}

            {clientReady ? (
            <div className="space-y-3">
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Услуга</span>
                <span className="relative mt-1 block">
                  <IconSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
                  <input
                    value={serviceSearch}
                    onChange={(event) => {
                      setServiceSearch(event.target.value)
                      setSelectedService(null)
                      setSelectedSlot(null)
                      setBookingSuccess(null)
                      setSubmitError(null)
                    }}
                    className={cn(fieldClass, 'pl-9')}
                    placeholder="Введите минимум 2 символа"
                  />
                </span>
              </label>

              {serviceSearchTerm.length > 0 && !shouldSearchServices ? (
                <p className="text-sm text-stone-500 dark:text-stone-400">Введите еще символы для поиска услуги.</p>
              ) : null}

              {shouldSearchServices ? (
                <div className="max-h-64 overflow-y-auto rounded-lg border border-stone-200 dark:border-stone-700">
                  {services.isLoading ? (
                    <p className="px-3 py-4 text-sm text-stone-500 dark:text-stone-400">Поиск услуг...</p>
                  ) : servicesError ? (
                    <p className="px-3 py-4 text-sm text-red-700 dark:text-red-300">{servicesError}</p>
                  ) : serviceItems.length === 0 ? (
                    <p className="px-3 py-4 text-sm text-stone-500 dark:text-stone-400">Активные услуги не найдены</p>
                  ) : (
                    <div className="divide-y divide-stone-200 dark:divide-stone-800">
                      {serviceItems.map((service) => {
                        const checked = selectedService?.id === service.id
                        return (
                          <button
                            key={service.id}
                            type="button"
                            onClick={() => {
                              setSelectedService(service)
                              setServiceSearch(service.name)
                              setSelectedSlot(null)
                              setBookingSuccess(null)
                              setSubmitError(null)
                            }}
                            className={cn(
                              'flex w-full items-start justify-between gap-3 px-3 py-3 text-left transition',
                              checked ? 'bg-teal-50 dark:bg-teal-950/30' : 'hover:bg-stone-50 dark:hover:bg-stone-800/60',
                            )}
                          >
                            <span className="min-w-0">
                              <span className="block font-medium text-stone-900 dark:text-stone-50">{service.name}</span>
                              <span className="block text-sm text-stone-500 dark:text-stone-400">
                                {service.duration_min} мин · {formatMoney(service)}
                              </span>
                            </span>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
            ) : null}

            {clientReady && selectedService ? (
              <div className="space-y-3 rounded-xl border border-stone-200 bg-stone-50 p-3 dark:border-stone-700 dark:bg-stone-950/40">
                <label className="block max-w-xs">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Дата</span>
                  <input
                    type="date"
                    value={selectedDate}
                    min={todayValue}
                    max={maxDateValue}
                    onChange={(event) => {
                      setSelectedDate(event.target.value)
                      setSelectedSlot(null)
                      setBookingSuccess(null)
                      setSubmitError(null)
                    }}
                    className={cn(fieldClass, 'mt-1 [color-scheme:light] dark:[color-scheme:dark]')}
                  />
                </label>

                <div>
                  <p className="mb-2 text-sm font-medium text-stone-700 dark:text-stone-300">Свободное время</p>
                  {slots.isLoading ? (
                    <p className="text-sm text-stone-500 dark:text-stone-400">Считаем свободные слоты...</p>
                  ) : slotsError ? (
                    <p className="text-sm text-red-700 dark:text-red-300">{slotsError}</p>
                  ) : (slots.data?.length ?? 0) === 0 ? (
                    <p className="text-sm text-stone-500 dark:text-stone-400">На эту дату свободного времени нет.</p>
                  ) : (
                    <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
                      {slots.data?.map((slot) => (
                        <button
                          key={slot.start_at}
                          type="button"
                          onClick={() => {
                            setSelectedSlot(slot.start_at)
                            setBookingSuccess(null)
                            setSubmitError(null)
                          }}
                          className={bookingSlotButtonClass(selectedSlot === slot.start_at)}
                        >
                          {formatSlotTime(slot.start_at)}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : null}

            {submitError ? (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/35 dark:text-red-100">
                {submitError}
              </p>
            ) : null}

            <button
              type="button"
              disabled={!canPrepare || createBooking.isPending}
              onClick={() => createBooking.mutate()}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-4 py-3 text-sm font-semibold text-white shadow-sm shadow-teal-900/15 transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400"
            >
              <IconCalendarSmall className="h-4 w-4" />
              {createBooking.isPending ? 'Создаем...' : 'Записать'}
            </button>
          </div>
        </section>

        <aside className="space-y-4">
          <div className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
            <p className="text-xs font-semibold uppercase text-stone-500 dark:text-stone-400">Предпросмотр</p>
            <p className="mt-2 text-lg font-semibold text-stone-900 dark:text-stone-50">{previewClientName}</p>
            {selectedService ? (
              <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
                {selectedService.name} · {selectedService.duration_min} мин · {formatMoney(selectedService)}
              </p>
            ) : (
              <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">
                {clientReady ? 'Найдите и выберите активную услугу' : 'Сначала выберите клиента'}
              </p>
            )}
            {selectedService ? (
              <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
                {formatPreviewDate(selectedDate)},{' '}
                {selectedSlot ? formatSlotTime(selectedSlot) : 'время не выбрано'}
              </p>
            ) : null}
          </div>
        </aside>
      </div>

      <section
        id="bookings-list-section"
        className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80 sm:p-5"
      >
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Записи</h2>
            <p className="text-sm text-stone-500 dark:text-stone-400">
              {listScope === 'upcoming'
                ? 'Предстоящие и активные визиты.'
                : 'Прошедшие, завершённые и отменённые.'}
            </p>
          </div>
          <SegmentTabs
            tabs={listScopeTabs}
            value={listScope}
            onChange={setListScope}
            fullWidth
            className="sm:w-auto"
          />
        </div>

        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="block min-w-[12rem] flex-1 sm:max-w-xs">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Клиент</span>
            <select
              value={listClientId}
              onChange={(event) => setListClientId(event.target.value)}
              className={cn(fieldClass, 'mt-1')}
            >
              <option value="">Все клиенты</option>
              {listClientOptions.map((item) => (
                <option key={item.client.id} value={item.client.id}>
                  {clientDisplayName(item)}
                </option>
              ))}
            </select>
          </label>
          <label className="block min-w-[12rem] flex-1 sm:max-w-xs">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Услуга</span>
            <select
              value={listServiceId}
              onChange={(event) => setListServiceId(event.target.value)}
              className={cn(fieldClass, 'mt-1')}
            >
              <option value="">Все услуги</option>
              {listServiceOptions.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name}
                </option>
              ))}
            </select>
          </label>
          {listFiltersActive ? (
            <button
              type="button"
              onClick={clearListFilters}
              className="rounded-lg border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
            >
              Сбросить фильтры
            </button>
          ) : null}
        </div>

        {bookingsListLoading ? (
          <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем записи...</p>
        ) : bookingsError ? (
          <p className="text-sm text-red-700 dark:text-red-300">{bookingsError}</p>
        ) : bookingItems.length === 0 ? (
          <p className="text-sm text-stone-500 dark:text-stone-400">
            {listFiltersActive
              ? 'Нет записей по выбранным фильтрам.'
              : listScope === 'upcoming'
                ? 'Нет предстоящих записей.'
                : 'История пуста.'}
          </p>
        ) : (
          <>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-stone-200 text-sm dark:divide-stone-800">
              <thead>
                <tr className="text-left text-xs font-semibold uppercase text-stone-500 dark:text-stone-400">
                  <th className="py-2 pr-4">Время</th>
                  <th className="py-2 pr-4">Клиент</th>
                  <th className="py-2 pr-4">Услуга</th>
                  <th className="py-2 pr-4">Стоимость</th>
                  <th className="py-2 pr-4">Статус</th>
                  <th className="py-2 text-right">
                    <span className="sr-only">Действия</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
                {bookingItems.map((booking) => (
                  <tr key={booking.id} className="text-stone-700 dark:text-stone-200">
                    <td className="whitespace-nowrap py-3 pr-4 font-medium text-stone-900 dark:text-stone-50">
                      {formatSlotFull(booking.start_at)}
                    </td>
                    <td className="py-3 pr-4">{clientNameById.get(booking.client_id) ?? 'Клиент'}</td>
                    <td className="py-3 pr-4">
                      <span className="font-medium text-stone-900 dark:text-stone-50">
                        {serviceNameById.get(booking.service_id) ?? 'Услуга'}
                      </span>
                      <span className="ml-2 text-stone-500 dark:text-stone-400">{booking.duration_min} мин</span>
                    </td>
                    <td className="whitespace-nowrap py-3 pr-4">
                      {booking.price_snapshot} {booking.currency_snapshot}
                    </td>
                    <td className="whitespace-nowrap py-3 pr-4">
                      <span
                        className={cn(
                          'rounded-full px-2 py-0.5 text-xs font-medium',
                          bookingStatusBadgeClass(booking.status),
                        )}
                      >
                        {bookingStatusLabel(booking.status)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {blocksCalendar(booking.status) ? (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                setBookingActionError(null)
                                setRescheduleBooking(booking)
                                setRescheduleDate(toDateInputValue(new Date(booking.start_at)))
                                setRescheduleSlot(null)
                              }}
                              className="rounded-lg p-2 text-stone-500 transition hover:bg-teal-50 hover:text-teal-700 dark:text-stone-400 dark:hover:bg-teal-950/40 dark:hover:text-teal-300"
                              aria-label={`Перенести запись клиента ${clientNameById.get(booking.client_id) ?? 'Клиент'}`}
                              title="Перенести запись"
                            >
                              <IconReschedule className="h-5 w-5" />
                            </button>
                            <button
                              type="button"
                              disabled={cancelBooking.isPending}
                              onClick={() => {
                                cancelBooking.reset()
                                setPendingCancel(booking)
                              }}
                              className="rounded-lg p-2 text-stone-400 transition hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50 dark:hover:bg-rose-950/40 dark:hover:text-rose-400"
                              aria-label={`Отменить запись клиента ${clientNameById.get(booking.client_id) ?? 'Клиент'}`}
                              title="Отменить запись"
                            >
                              <IconTrash className="h-5 w-5" />
                            </button>
                          </>
                        ) : null}
                        {listScope === 'history' && needsAttendanceConfirmation(booking) ? (
                          <div
                            className="inline-flex shrink-0 overflow-hidden rounded-lg border border-stone-200/90 dark:border-stone-700"
                            role="group"
                            aria-label="Отметить явку"
                          >
                            <button
                              type="button"
                              disabled={markAttendance.isPending}
                              onClick={() => {
                                markAttendance.reset()
                                markAttendance.mutate({ bookingId: booking.id, attended: true })
                              }}
                              className="border-r border-stone-200/90 p-1.5 text-emerald-700 transition hover:bg-emerald-50 disabled:opacity-50 dark:border-stone-700 dark:text-emerald-400 dark:hover:bg-emerald-950/50"
                              aria-label={`Клиент ${clientNameById.get(booking.client_id) ?? 'Клиент'} пришел`}
                              title="Пришел"
                            >
                              <IconThumbUp className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              disabled={markAttendance.isPending}
                              onClick={() => {
                                markAttendance.reset()
                                markAttendance.mutate({ bookingId: booking.id, attended: false })
                              }}
                              className="p-1.5 text-amber-800 transition hover:bg-amber-50 disabled:opacity-50 dark:text-amber-400 dark:hover:bg-amber-950/50"
                              aria-label={`Клиент ${clientNameById.get(booking.client_id) ?? 'Клиент'} не пришел`}
                              title="Не пришел"
                            >
                              <IconXCircle className="h-4 w-4" />
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex flex-col gap-3 border-t border-stone-200 bg-stone-50/50 px-1 pt-3 dark:border-stone-700 dark:bg-stone-950/30 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
            <p className="text-sm text-stone-600 dark:text-stone-400">
              Страница {page} из {totalPages}
              <span className="text-stone-400 dark:text-stone-500"> · </span>
              всего {bookingsTotal}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-2 text-sm text-stone-600 dark:text-stone-400">
                <span className="whitespace-nowrap">На странице</span>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(Number(e.target.value) as PageSize)}
                  className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-stone-900 shadow-sm dark:border-stone-600 dark:bg-stone-900 dark:text-stone-100"
                >
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                </select>
              </label>
              <div className="flex gap-1">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 enabled:hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-stone-600 dark:text-stone-200 dark:enabled:hover:bg-stone-800"
                >
                  Назад
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 enabled:hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-stone-600 dark:text-stone-200 dark:enabled:hover:bg-stone-800"
                >
                  Вперёд
                </button>
              </div>
            </div>
          </div>
          </>
        )}

        {bookingActionError ? (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/35 dark:text-red-100">
            {bookingActionError}
          </p>
        ) : null}

      </section>

      {pendingCancel ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cancel-booking-title"
          onClick={(event) => {
            if (event.target === event.currentTarget && !cancelBooking.isPending) {
              setPendingCancel(null)
            }
          }}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-xl dark:border-stone-700 dark:bg-stone-900"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="cancel-booking-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
              Отменить запись?
            </h2>
            <p className="mt-3 text-sm text-stone-600 dark:text-stone-400">
              Запись клиента «{clientNameById.get(pendingCancel.client_id) ?? 'Клиент'}» на{' '}
              {formatSlotFull(pendingCancel.start_at)} будет отменена.
            </p>
            {cancelBooking.isError ? (
              <p className="mt-3 text-sm text-red-700 dark:text-red-300" role="alert">
                {getUserFacingError(cancelBooking.error)}
              </p>
            ) : null}
            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                disabled={cancelBooking.isPending}
                onClick={() => setPendingCancel(null)}
                className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
              >
                Оставить
              </button>
              <button
                type="button"
                disabled={cancelBooking.isPending}
                onClick={() => cancelBooking.mutate(pendingCancel.id)}
                className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-50 dark:bg-rose-600 dark:hover:bg-rose-500"
              >
                {cancelBooking.isPending ? 'Отмена...' : 'Отменить запись'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {rescheduleBooking ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
          role="dialog"
          aria-modal="true"
          aria-labelledby="reschedule-booking-title"
          onClick={(event) => {
            if (event.target === event.currentTarget && !reschedule.isPending) {
              setRescheduleBooking(null)
              setRescheduleSlot(null)
            }
          }}
        >
          <div
            className="flex max-h-[min(90vh,44rem)] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-xl dark:border-stone-700 dark:bg-stone-900"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="border-b border-stone-200 px-6 py-5 dark:border-stone-700">
              <h2 id="reschedule-booking-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
                Перенос записи
              </h2>
              <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
                {clientNameById.get(rescheduleBooking.client_id) ?? 'Клиент'} ·{' '}
                {serviceNameById.get(rescheduleBooking.service_id) ?? 'Услуга'}
              </p>
              <p className="text-sm text-stone-500 dark:text-stone-400">
                Сейчас: {formatBookingDateTime(rescheduleBooking.start_at)}
              </p>
            </div>

            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-5">
              <label className="block max-w-xs">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Новая дата</span>
                <input
                  type="date"
                  value={rescheduleDate}
                  min={todayValue}
                  max={maxDateValue}
                  onChange={(event) => {
                    setRescheduleDate(event.target.value)
                    setRescheduleSlot(null)
                  }}
                  className={cn(fieldClass, 'mt-1 [color-scheme:light] dark:[color-scheme:dark]')}
                />
              </label>

              <div>
                <p className="mb-2 text-sm font-medium text-stone-700 dark:text-stone-300">Новое время</p>
                {rescheduleSlots.isLoading ? (
                  <p className="text-sm text-stone-500 dark:text-stone-400">Ищем свободные слоты...</p>
                ) : rescheduleSlotsError ? (
                  <p className="text-sm text-red-700 dark:text-red-300">{rescheduleSlotsError}</p>
                ) : (rescheduleSlots.data?.length ?? 0) === 0 ? (
                  <p className="text-sm text-stone-500 dark:text-stone-400">На эту дату свободного времени нет.</p>
                ) : (
                  <div className="grid max-h-64 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-4 md:grid-cols-5">
                    {rescheduleSlots.data?.map((slot) => (
                      <button
                        key={slot.start_at}
                        type="button"
                        disabled={reschedule.isPending}
                        onClick={() => {
                          reschedule.reset()
                          setRescheduleSlot(slot.start_at)
                        }}
                        className={bookingSlotButtonClass(rescheduleSlot === slot.start_at)}
                      >
                        {formatSlotTime(slot.start_at)}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {reschedule.isError ? (
                <p className="text-sm text-red-700 dark:text-red-300" role="alert">
                  {getUserFacingError(reschedule.error)}
                </p>
              ) : null}
            </div>

            <div className="flex flex-wrap justify-end gap-2 border-t border-stone-200 px-6 py-5 dark:border-stone-700">
              <button
                type="button"
                disabled={reschedule.isPending}
                onClick={() => {
                  setRescheduleBooking(null)
                  setRescheduleSlot(null)
                }}
                className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
              >
                Отмена
              </button>
              <button
                type="button"
                disabled={reschedule.isPending || !rescheduleSlot}
                onClick={() => reschedule.mutate()}
                className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
              >
                {reschedule.isPending ? 'Переносим...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
