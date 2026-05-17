import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { meApi } from '../api/auth'
import { cn } from '../lib/forms'

type ClientMode = 'accounting' | 'existing' | 'linked'

type MockClient = {
  id: string
  name: string
  phone?: string
  email?: string
  kind: 'accounting' | 'linked'
}

type MockService = {
  id: string
  name: string
  duration: number
  price: string
}

type MockBooking = {
  id: string
  clientName: string
  serviceName: string
  startAt: string
  duration: number
  price: string
  status: 'scheduled' | 'cancelled'
  source: 'manual' | 'client'
}

const fieldClass =
  'w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none transition focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:focus:border-stone-500'

const clientModes: { value: ClientMode; label: string; description: string }[] = [
  {
    value: 'accounting',
    label: 'Новый клиент для учета',
    description: 'Создать карточку без входа в приложение',
  },
  {
    value: 'existing',
    label: 'Клиент из базы',
    description: 'Выбрать уже созданную карточку',
  },
  {
    value: 'linked',
    label: 'Клиент с аккаунтом',
    description: 'Запись для привязанного пользователя',
  },
]

const mockClients: MockClient[] = [
  { id: 'c1', name: 'Анна Смирнова', phone: '+375 29 111-22-33', kind: 'accounting' },
  { id: 'c2', name: 'Мария Коваль', phone: '+375 44 555-10-10', email: 'maria@example.com', kind: 'linked' },
  { id: 'c3', name: 'Ирина Литвин', phone: '+375 33 902-18-44', kind: 'accounting' },
]

const mockServices: MockService[] = [
  { id: 's1', name: 'Маникюр с покрытием', duration: 90, price: '75 BYN' },
  { id: 's2', name: 'Коррекция бровей', duration: 30, price: '25 BYN' },
  { id: 's3', name: 'Консультация', duration: 45, price: '0 BYN' },
]

const mockSlots = ['10:00', '11:30', '13:00', '15:30', '17:00']

const mockBookings: MockBooking[] = [
  {
    id: 'b1',
    clientName: 'Мария Коваль',
    serviceName: 'Маникюр с покрытием',
    startAt: '2026-05-20T10:00:00',
    duration: 90,
    price: '75 BYN',
    status: 'scheduled',
    source: 'client',
  },
  {
    id: 'b2',
    clientName: 'Анна Смирнова',
    serviceName: 'Коррекция бровей',
    startAt: '2026-05-20T13:00:00',
    duration: 30,
    price: '25 BYN',
    status: 'scheduled',
    source: 'manual',
  },
  {
    id: 'b3',
    clientName: 'Ирина Литвин',
    serviceName: 'Консультация',
    startAt: '2026-05-21T15:30:00',
    duration: 45,
    price: '0 BYN',
    status: 'cancelled',
    source: 'manual',
  },
]

function toDateInputValue(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDateTime(value: string) {
  const formatted = new Intl.DateTimeFormat('ru-RU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
  return formatted.replace(' Г.', ' г.')
}

function formatDateLong(value: string) {
  const [year, month, day] = value.split('-').map(Number)
  const formatted = new Intl.DateTimeFormat('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(year, month - 1, day))
  return formatted.replace(' Г.', ' г.')
}

function IconPlus(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
    </svg>
  )
}

function IconCalendarSmall(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3M5 11h14M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}

function IconUserPlus(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 19a6 6 0 00-12 0" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 11a4 4 0 100-8 4 4 0 000 8zM19 8v6m3-3h-6" />
    </svg>
  )
}

export function BookingsPage() {
  const navigate = useNavigate()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const [clientMode, setClientMode] = useState<ClientMode>('accounting')
  const [draftName, setDraftName] = useState('')
  const [draftPhone, setDraftPhone] = useState('')
  const [draftEmail, setDraftEmail] = useState('')
  const [selectedClientId, setSelectedClientId] = useState(mockClients[0]?.id ?? '')
  const [selectedServiceId, setSelectedServiceId] = useState(mockServices[0]?.id ?? '')
  const [selectedDate, setSelectedDate] = useState(() => toDateInputValue(new Date()))
  const [selectedSlot, setSelectedSlot] = useState(mockSlots[0])
  const [comment, setComment] = useState('')

  useEffect(() => {
    if (me.isError) navigate('/login')
  }, [me.isError, navigate])

  const selectedService = mockServices.find((service) => service.id === selectedServiceId) ?? mockServices[0]
  const selectedClient = mockClients.find((client) => client.id === selectedClientId)
  const availableClients = mockClients.filter((client) => {
    if (clientMode === 'linked') {
      return client.kind === 'linked'
    }
    return client.kind === 'accounting'
  })
  const previewClientName = clientMode === 'accounting' ? draftName.trim() || 'Новый клиент' : selectedClient?.name ?? 'Клиент'
  const canCreate =
    selectedService != null &&
    selectedSlot.length > 0 &&
    (clientMode !== 'accounting' || draftName.trim().length > 0) &&
    (clientMode === 'accounting' || selectedClient != null)

  const bookingsByDate = useMemo(() => {
    const groups = new Map<string, MockBooking[]>()
    for (const booking of mockBookings) {
      const dateKey = booking.startAt.slice(0, 10)
      groups.set(dateKey, [...(groups.get(dateKey) ?? []), booking])
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [])

  if (me.isLoading || !me.data) {
    return <p className="text-stone-500 dark:text-stone-400">Загрузка...</p>
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50 sm:text-3xl">
            Записи
          </h1>
          <p className="max-w-2xl text-sm leading-6 text-stone-600 dark:text-stone-400">
            Моковый интерфейс создания записи. Первый сценарий - клиент для учета без аккаунта.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 rounded-xl border border-stone-200 bg-white p-2 shadow-sm dark:border-stone-700 dark:bg-stone-900/80">
          <div className="min-w-20 px-3 py-2">
            <p className="text-lg font-semibold text-stone-900 dark:text-stone-50">2</p>
            <p className="text-xs text-stone-500 dark:text-stone-400">активные</p>
          </div>
          <div className="min-w-20 border-x border-stone-200 px-3 py-2 dark:border-stone-700">
            <p className="text-lg font-semibold text-stone-900 dark:text-stone-50">1</p>
            <p className="text-xs text-stone-500 dark:text-stone-400">сегодня</p>
          </div>
          <div className="min-w-20 px-3 py-2">
            <p className="text-lg font-semibold text-stone-900 dark:text-stone-50">100</p>
            <p className="text-xs text-stone-500 dark:text-stone-400">BYN</p>
          </div>
        </div>
      </header>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(24rem,1.05fr)]">
        <section className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200">
              <IconPlus className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Новая запись</h2>
              <p className="text-sm text-stone-500 dark:text-stone-400">Данные пока не сохраняются на сервере</p>
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <p className="mb-2 text-sm font-medium text-stone-700 dark:text-stone-300">Клиент</p>
              <div className="grid gap-2">
                {clientModes.map((mode) => (
                  <button
                    key={mode.value}
                    type="button"
                    onClick={() => {
                      setClientMode(mode.value)
                      const nextClient = mockClients.find((client) =>
                        mode.value === 'linked' ? client.kind === 'linked' : client.kind === 'accounting',
                      )
                      if (nextClient) {
                        setSelectedClientId(nextClient.id)
                      }
                    }}
                    className={cn(
                      'flex items-start gap-3 rounded-lg border px-3 py-3 text-left transition',
                      clientMode === mode.value
                        ? 'border-teal-500 bg-teal-50 dark:border-teal-600 dark:bg-teal-950/30'
                        : 'border-stone-200 hover:bg-stone-50 dark:border-stone-700 dark:hover:bg-stone-800/60',
                    )}
                  >
                    <span
                      className={cn(
                        'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                        clientMode === mode.value
                          ? 'border-teal-600 bg-teal-600 text-white'
                          : 'border-stone-300 dark:border-stone-600',
                      )}
                    >
                      {clientMode === mode.value ? <span className="h-2 w-2 rounded-full bg-white" /> : null}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold text-stone-900 dark:text-stone-100">{mode.label}</span>
                      <span className="text-xs text-stone-500 dark:text-stone-400">{mode.description}</span>
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {clientMode === 'accounting' ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block sm:col-span-2">
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Имя клиента *</span>
                  <input
                    value={draftName}
                    onChange={(event) => setDraftName(event.target.value)}
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
            ) : (
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Выберите клиента</span>
                <select
                  value={selectedClientId}
                  onChange={(event) => setSelectedClientId(event.target.value)}
                  className={cn(fieldClass, 'mt-1')}
                >
                  {availableClients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name} {client.phone ? `- ${client.phone}` : ''}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Услуга</span>
                <select
                  value={selectedServiceId}
                  onChange={(event) => setSelectedServiceId(event.target.value)}
                  className={cn(fieldClass, 'mt-1')}
                >
                  {mockServices.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Дата</span>
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(event) => setSelectedDate(event.target.value)}
                  className={cn(fieldClass, 'mt-1 [color-scheme:light] dark:[color-scheme:dark]')}
                />
              </label>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium text-stone-700 dark:text-stone-300">Доступное время</p>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
                {mockSlots.map((slot) => (
                  <button
                    key={slot}
                    type="button"
                    onClick={() => setSelectedSlot(slot)}
                    className={cn(
                      'rounded-lg border px-3 py-2 text-sm font-medium transition',
                      selectedSlot === slot
                        ? 'border-teal-600 bg-teal-100 text-teal-900 dark:border-teal-500 dark:bg-teal-950/50 dark:text-teal-100'
                        : 'border-stone-200 text-stone-700 hover:bg-stone-50 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800',
                    )}
                  >
                    {slot}
                  </button>
                ))}
              </div>
            </div>

            <label className="block">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Комментарий</span>
              <textarea
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                rows={3}
                className={cn(fieldClass, 'mt-1 resize-y')}
                placeholder="Например: впервые, попросила напомнить за день"
              />
            </label>

            <div className="rounded-lg border border-stone-200 bg-stone-50 p-3 dark:border-stone-700 dark:bg-stone-950/50">
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">Предпросмотр</p>
              <p className="mt-1 font-medium text-stone-900 dark:text-stone-50">{previewClientName}</p>
              <p className="text-sm text-stone-600 dark:text-stone-400">
                {selectedService.name} · {selectedService.duration} мин · {selectedService.price}
              </p>
              <p className="text-sm text-stone-600 dark:text-stone-400">
                {formatDateLong(selectedDate)}, {selectedSlot}
              </p>
            </div>

            <button
              type="button"
              disabled={!canCreate}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-4 py-3 text-sm font-semibold text-white shadow-sm shadow-teal-900/15 transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400"
            >
              <IconCalendarSmall className="h-4 w-4" />
              Создать запись
            </button>
          </div>
        </section>

        <section className="space-y-4">
          <div className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-200">
                <IconUserPlus className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Что произойдет</h2>
                <p className="text-sm text-stone-500 dark:text-stone-400">
                  Для нового клиента будет создана карточка в базе мастера без пользовательского аккаунта.
                </p>
              </div>
            </div>
          </div>

          {bookingsByDate.map(([date, bookings]) => (
            <div key={date} className="rounded-xl border border-stone-200/90 bg-white shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
              <div className="border-b border-stone-200 px-4 py-3 dark:border-stone-700">
                <h2 className="font-semibold text-stone-900 dark:text-stone-50">{formatDateLong(date)}</h2>
              </div>
              <div className="divide-y divide-stone-200 dark:divide-stone-800">
                {bookings.map((booking) => (
                  <div key={booking.id} className="flex items-start justify-between gap-3 px-4 py-3">
                    <div className="min-w-0">
                      <p className="font-medium text-stone-900 dark:text-stone-50">{booking.clientName}</p>
                      <p className="text-sm text-stone-600 dark:text-stone-400">{booking.serviceName}</p>
                      <p className="text-xs text-stone-500 dark:text-stone-500">
                        {formatDateTime(booking.startAt)} · {booking.duration} мин · {booking.price}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <span
                        className={cn(
                          'rounded-full px-2 py-0.5 text-xs font-medium',
                          booking.status === 'scheduled'
                            ? 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200'
                            : 'bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-300',
                        )}
                      >
                        {booking.status === 'scheduled' ? 'Запланирована' : 'Отменена'}
                      </span>
                      <span className="text-xs text-stone-500 dark:text-stone-500">
                        {booking.source === 'client' ? 'клиент' : 'вручную'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </section>
      </div>
    </div>
  )
}
