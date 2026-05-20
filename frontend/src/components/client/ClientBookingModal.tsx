import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { availabilityApi } from '../../api/availability'
import { bookingsMyCreateApi } from '../../api/bookings'
import { clientMasterLabel, clientsMyMasterServicesApi, type ClientMyMasterItem } from '../../api/clients'
import type { Service } from '../../api/services'
import { getUserFacingError } from '../../lib/apiErrors'
import { bookingSlotButtonClass } from '../../lib/bookingSlots'

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

function formatSlotLabel(iso: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

type Step = 'master' | 'service' | 'slot' | 'confirm'

type Props = {
  onClose: () => void
  masters: ClientMyMasterItem[]
  initialMasterId?: string | null
  onSuccess: () => void
}

export function ClientBookingModal({ onClose, masters, initialMasterId, onSuccess }: Props) {
  const resolvedInitialMaster =
    initialMasterId && masters.some((m) => m.master_id === initialMasterId) ? initialMasterId : null

  const [step, setStep] = useState<Step>(resolvedInitialMaster ? 'service' : 'master')
  const [masterId, setMasterId] = useState<string | null>(resolvedInitialMaster)
  const [serviceId, setServiceId] = useState<string | null>(null)
  const [dateInput, setDateInput] = useState(() => toDateInputValue(new Date()))
  const [slotIso, setSlotIso] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const todayInput = toDateInputValue(new Date())
  const maxDateInput = toDateInputValue(addDays(new Date(), 90))

  const selectedMaster = masters.find((m) => m.master_id === masterId) ?? null

  const servicesQuery = useQuery({
    queryKey: ['clients', 'me', 'masters', masterId, 'services'],
    queryFn: () => clientsMyMasterServicesApi(masterId!),
    enabled: Boolean(masterId),
  })

  const masterServices = servicesQuery.data ?? []
  const selectedService = masterServices.find((s) => s.id === serviceId) ?? null

  const slotsQuery = useQuery({
    queryKey: ['availability', masterId, serviceId, dateInput],
    queryFn: () =>
      availabilityApi({
        master_id: masterId!,
        service_id: serviceId!,
        date: dateInput,
      }),
    enabled: Boolean(masterId && serviceId && dateInput),
  })

  const createBooking = useMutation({
    mutationFn: () => {
      if (!masterId || !serviceId || !slotIso) {
        throw new Error('Выберите мастера, услугу и время.')
      }
      return bookingsMyCreateApi({
        master_id: masterId,
        service_id: serviceId,
        start_at: slotIso,
      })
    },
    onSuccess: () => {
      onSuccess()
      onClose()
    },
    onError: (error) => setSubmitError(getUserFacingError(error)),
  })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const freeSlots = slotsQuery.data ?? []

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center" aria-modal role="dialog">
      <button
        type="button"
        aria-label="Закрыть"
        className="absolute inset-0 bg-stone-950/50 dark:bg-stone-950/70"
        onClick={onClose}
      />
      <div className="relative flex max-h-[min(90vh,40rem)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-xl dark:border-stone-700 dark:bg-stone-900">
        <div className="flex items-start justify-between gap-3 border-b border-stone-100 px-5 py-4 dark:border-stone-800">
          <div>
            <h2 className="text-lg font-semibold text-stone-900 dark:text-stone-50">Новая запись</h2>
            <p className="mt-0.5 text-xs text-stone-500 dark:text-stone-400">Выберите мастера, услугу и свободное время.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"
          >
            <span className="sr-only">Закрыть</span>
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {submitError ? (
            <p className="mb-3 text-sm text-rose-600 dark:text-rose-300" role="alert">
              {submitError}
            </p>
          ) : null}

          {step === 'master' ? (
            <ul className="space-y-2">
              {masters.map((m) => (
                <li key={m.master_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setMasterId(m.master_id)
                      setServiceId(null)
                      setSlotIso(null)
                      setStep('service')
                    }}
                    className="w-full rounded-lg border border-stone-200 px-4 py-3 text-left hover:border-teal-500 dark:border-stone-700"
                  >
                    <p className="font-medium text-stone-900 dark:text-stone-100">{clientMasterLabel(m)}</p>
                    {m.alias ? <p className="text-xs text-stone-500">Как вас зовут: {m.alias}</p> : null}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          {step === 'service' ? (
            <div className="space-y-3">
              {selectedMaster ? (
                <p className="text-sm text-stone-600 dark:text-stone-400">Мастер: {clientMasterLabel(selectedMaster)}</p>
              ) : null}
              {servicesQuery.isLoading ? (
                <p className="text-sm text-stone-500">Загружаем услуги…</p>
              ) : servicesQuery.isError ? (
                <p className="text-sm text-rose-600">{getUserFacingError(servicesQuery.error)}</p>
              ) : masterServices.length === 0 ? (
                <p className="text-sm text-stone-500">Нет доступных услуг.</p>
              ) : (
                <ul className="space-y-2">
                  {masterServices.map((s: Service) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        onClick={() => {
                          setServiceId(s.id)
                          setSlotIso(null)
                          setStep('slot')
                        }}
                        className="w-full rounded-lg border border-stone-200 px-4 py-3 text-left hover:border-teal-500 dark:border-stone-700"
                      >
                        <p className="font-medium">{s.name}</p>
                        <p className="text-xs text-stone-500">
                          {s.duration_min} мин · {s.price} {s.currency}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <button type="button" className="text-sm text-teal-700 dark:text-teal-400" onClick={() => setStep('master')}>
                ← Другой мастер
              </button>
            </div>
          ) : null}

          {step === 'slot' ? (
            <div className="space-y-4">
              {selectedService ? (
                <p className="text-sm text-stone-600 dark:text-stone-400">
                  {selectedService.name} · {selectedService.duration_min} мин
                </p>
              ) : null}
              <label className="block text-sm">
                <span className="font-medium text-stone-700 dark:text-stone-300">Дата</span>
                <input
                  type="date"
                  value={dateInput}
                  min={todayInput}
                  max={maxDateInput}
                  onChange={(e) => {
                    setDateInput(e.target.value)
                    setSlotIso(null)
                  }}
                  className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-2 text-sm dark:border-stone-600 dark:bg-stone-950"
                />
              </label>
              {slotsQuery.isLoading ? (
                <p className="text-sm text-stone-500">Загружаем слоты…</p>
              ) : slotsQuery.isError ? (
                <p className="text-sm text-rose-600">{getUserFacingError(slotsQuery.error)}</p>
              ) : freeSlots.length === 0 ? (
                <p className="text-sm text-stone-500">На эту дату нет свободного времени.</p>
              ) : (
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
                  {freeSlots.map((slot) => (
                    <button
                      key={slot.start_at}
                      type="button"
                      onClick={() => {
                        setSlotIso(slot.start_at)
                        setStep('confirm')
                      }}
                      className={bookingSlotButtonClass(slotIso === slot.start_at)}
                    >
                      {formatSlotLabel(slot.start_at)}
                    </button>
                  ))}
                </div>
              )}
              <button type="button" className="text-sm text-teal-700 dark:text-teal-400" onClick={() => setStep('service')}>
                ← Другая услуга
              </button>
            </div>
          ) : null}

          {step === 'confirm' && selectedMaster && selectedService && slotIso ? (
            <div className="space-y-4">
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="text-stone-500">Мастер</dt>
                  <dd className="font-medium">{clientMasterLabel(selectedMaster)}</dd>
                </div>
                <div>
                  <dt className="text-stone-500">Услуга</dt>
                  <dd className="font-medium">{selectedService.name}</dd>
                </div>
                <div>
                  <dt className="text-stone-500">Время</dt>
                  <dd className="font-medium">{formatSlotLabel(slotIso)}</dd>
                </div>
              </dl>
              <button type="button" className="text-sm text-teal-700 dark:text-teal-400" onClick={() => setStep('slot')}>
                ← Изменить время
              </button>
            </div>
          ) : null}
        </div>

        <div className="border-t border-stone-100 px-5 py-4 dark:border-stone-800">
          {step === 'confirm' ? (
            <button
              type="button"
              disabled={createBooking.isPending}
              onClick={() => createBooking.mutate()}
              className="w-full rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-60 dark:bg-teal-500 dark:text-stone-950"
            >
              {createBooking.isPending ? 'Записываем…' : 'Подтвердить запись'}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
