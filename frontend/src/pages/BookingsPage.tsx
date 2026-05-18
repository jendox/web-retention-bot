import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { meApi } from '../api/auth'
import { clientsGetApi, clientsListApi, type ClientWithLink } from '../api/clients'
import { servicesListApi, type Service } from '../api/services'
import { cn } from '../lib/forms'

type ClientSource = 'existing' | 'new'

const SEARCH_PAGE_SIZE = 10
const MIN_SEARCH_LENGTH = 2

const fieldClass =
  'w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none transition focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:focus:border-stone-500'

const sourceTabs: { value: ClientSource; label: string }[] = [
  { value: 'existing', label: 'Из базы' },
  { value: 'new', label: 'Новый' },
]

function toDateInputValue(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
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

export function BookingsPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const prefillClientId = searchParams.get('client_id') ?? ''

  const [clientSource, setClientSource] = useState<ClientSource>('existing')
  const [clientSearch, setClientSearch] = useState('')
  const [selectedClient, setSelectedClient] = useState<ClientWithLink | null>(null)
  const [draftName, setDraftName] = useState('')
  const [draftPhone, setDraftPhone] = useState('')
  const [draftEmail, setDraftEmail] = useState('')
  const [serviceSearch, setServiceSearch] = useState('')
  const [selectedService, setSelectedService] = useState<Service | null>(null)
  const [selectedDate, setSelectedDate] = useState(() => toDateInputValue(new Date()))
  const [selectedTime, setSelectedTime] = useState('10:00')
  const [comment, setComment] = useState('')
  const [submitNotice, setSubmitNotice] = useState(false)

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const prefilledClient = useQuery({
    queryKey: ['client', prefillClientId],
    queryFn: () => clientsGetApi(prefillClientId),
    enabled: me.isSuccess && Boolean(prefillClientId),
  })

  const clientSearchTerm = clientSearch.trim()
  const serviceSearchTerm = serviceSearch.trim()
  const shouldSearchClients = clientSearchTerm.length >= MIN_SEARCH_LENGTH
  const shouldSearchServices = serviceSearchTerm.length >= MIN_SEARCH_LENGTH

  const clients = useQuery({
    queryKey: ['clients', 'booking-form-search', clientSearchTerm, SEARCH_PAGE_SIZE],
    queryFn: () => clientsListApi({ page: 1, page_size: SEARCH_PAGE_SIZE, q: clientSearchTerm }),
    enabled: me.isSuccess && shouldSearchClients,
  })
  const services = useQuery({
    queryKey: ['services', 'booking-form-search', serviceSearchTerm, SEARCH_PAGE_SIZE, 'active'],
    queryFn: () => servicesListApi({ page: 1, page_size: SEARCH_PAGE_SIZE, is_active: true, q: serviceSearchTerm }),
    enabled: me.isSuccess && shouldSearchServices,
  })

  useEffect(() => {
    if (me.isError) navigate('/login')
  }, [me.isError, navigate])

  const prefilled = selectedClient ?? prefilledClient.data ?? null
  const clientItems = clients.data?.items ?? []
  const serviceItems = services.data?.items ?? []
  const clientsError = clients.error instanceof Error ? clients.error.message : null
  const servicesError = services.error instanceof Error ? services.error.message : null

  const previewClientName =
    clientSource === 'new' ? draftName.trim() || 'Новый клиент' : prefilled ? clientDisplayName(prefilled) : 'Клиент'
  const canPrepare =
    selectedService != null &&
    selectedDate.length > 0 &&
    selectedTime.length > 0 &&
    (clientSource === 'new' ? draftName.trim().length > 0 : prefilled != null)

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

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(21rem,0.72fr)]">
        <section className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80 sm:p-5">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200">
              <IconPlus className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Параметры записи</h2>
              <p className="text-sm text-stone-500 dark:text-stone-400">Создание записи на сервере пока не вызывается</p>
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <p className="mb-2 text-sm font-medium text-stone-700 dark:text-stone-300">Клиент</p>
              <div className="inline-grid w-full grid-cols-2 rounded-lg bg-stone-100 p-1 dark:bg-stone-800 sm:w-auto">
                {sourceTabs.map((tab) => (
                  <button
                    key={tab.value}
                    type="button"
                    onClick={() => {
                      setClientSource(tab.value)
                      setSubmitNotice(false)
                    }}
                    className={cn(
                      'rounded-md px-4 py-2 text-sm font-medium transition',
                      clientSource === tab.value
                        ? 'bg-white text-stone-950 shadow-sm dark:bg-stone-950 dark:text-stone-50'
                        : 'text-stone-600 hover:text-stone-950 dark:text-stone-300 dark:hover:text-white',
                    )}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
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
                        setSubmitNotice(false)
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
                            setSubmitNotice(false)
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
                                setSubmitNotice(false)
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
                      setSubmitNotice(false)
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
                      setSubmitNotice(false)
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
                              setSubmitNotice(false)
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

            <div className="grid gap-3 sm:grid-cols-[10rem_8rem_minmax(0,1fr)]">
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Дата</span>
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(event) => setSelectedDate(event.target.value)}
                  className={cn(fieldClass, 'mt-1 [color-scheme:light] dark:[color-scheme:dark]')}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Время</span>
                <input
                  type="time"
                  value={selectedTime}
                  onChange={(event) => setSelectedTime(event.target.value)}
                  className={cn(fieldClass, 'mt-1 [color-scheme:light] dark:[color-scheme:dark]')}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Комментарий</span>
                <input
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                  className={cn(fieldClass, 'mt-1')}
                  placeholder="Например: впервые"
                />
              </label>
            </div>

            {submitNotice ? (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/35 dark:text-amber-100">
                Форма собрана, но запись пока не отправляется: следующий шаг - подключить слоты и POST создания записи.
              </p>
            ) : null}

            <button
              type="button"
              disabled={!canPrepare}
              onClick={() => setSubmitNotice(true)}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-4 py-3 text-sm font-semibold text-white shadow-sm shadow-teal-900/15 transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400"
            >
              <IconCalendarSmall className="h-4 w-4" />
              Подготовить запись
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
              <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">Найдите и выберите активную услугу</p>
            )}
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
              {selectedDate || 'Дата не выбрана'}, {selectedTime || 'время не выбрано'}
            </p>
          </div>

          <div className="rounded-xl border border-stone-200/90 bg-white p-4 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
            <h2 className="text-base font-semibold text-stone-900 dark:text-stone-50">Что уже подключено</h2>
            <div className="mt-3 space-y-3 text-sm text-stone-600 dark:text-stone-400">
              <p>Клиент и услуга ищутся на сервере, без показа неполного списка по умолчанию.</p>
              <p>При переходе из таблицы клиентов клиент сразу подставляется в эту же форму.</p>
              <p>Метка кабинета справочная и не меняет сценарий создания записи.</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
