import { useEffect, useState, type MouseEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { availabilityApi } from '../../api/availability'
import { bookingsMyCreateApi, type BookingClientListItem } from '../../api/bookings'
import { clientMasterLabel, clientsMyMasterServicesApi, type ClientMyMasterItem } from '../../api/clients'
import type { Service } from '../../api/services'
import { getUserFacingError } from '../../lib/apiErrors'
import {
  bookingDateBounds,
  bookingDateFieldClass,
  formatSlotDateTime,
  formatSlotTime,
} from '../../lib/bookingSchedule'
import { bookingSlotButtonClass } from '../../lib/bookingSlots'
import { cn } from '../../lib/forms'
import { toDateInputValueInTimeZone } from '../../lib/timezones'

type Step = 'master' | 'service' | 'slot'

type Props = {
  onClose: () => void
  masters: ClientMyMasterItem[]
  clientTimeZone: string
  initialMasterId?: string | null
  onSuccess: (booking: BookingClientListItem) => void
}

export function ClientBookingModal({ onClose, masters, clientTimeZone, initialMasterId, onSuccess }: Props) {
  const resolvedInitialMaster =
    initialMasterId && masters.some((m) => m.master_id === initialMasterId) ? initialMasterId : null

  const [step, setStep] = useState<Step>(resolvedInitialMaster ? 'service' : 'master')
  const [masterId, setMasterId] = useState<string | null>(resolvedInitialMaster)
  const [serviceId, setServiceId] = useState<string | null>(null)
  const [dateInput, setDateInput] = useState(() => toDateInputValueInTimeZone(new Date(), clientTimeZone))
  const [slotIso, setSlotIso] = useState<string | null>(null)

  const { min: todayInput, max: maxDateInput } = bookingDateBounds(clientTimeZone)

  const selectedMaster = masters.find((m) => m.master_id === masterId) ?? null

  const servicesQuery = useQuery({
    queryKey: ['clients', 'me', 'masters', masterId, 'services'],
    queryFn: () => clientsMyMasterServicesApi(masterId!),
    enabled: Boolean(masterId),
  })

  const masterServices = servicesQuery.data ?? []
  const selectedService = masterServices.find((s) => s.id === serviceId) ?? null

  const slotsQuery = useQuery({
    queryKey: ['availability', masterId, serviceId, dateInput, clientTimeZone],
    queryFn: () =>
      availabilityApi({
        master_id: masterId!,
        service_id: serviceId!,
        date: dateInput,
        timezone: clientTimeZone,
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
    onSuccess: (booking) => {
      onSuccess(booking)
      onClose()
    },
  })

  const isPending = createBooking.isPending

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isPending) {
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, isPending])

  const slotsError = slotsQuery.error instanceof Error ? getUserFacingError(slotsQuery.error) : null
  const freeSlots = slotsQuery.data ?? []

  const handleOverlayClick = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget && !isPending) {
      onClose()
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="client-booking-title"
      onClick={handleOverlayClick}
    >
      <div
        className="flex max-h-[min(90vh,44rem)] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-xl dark:border-stone-700 dark:bg-stone-900"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="border-b border-stone-200 px-6 py-5 dark:border-stone-700">
          <h2 id="client-booking-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
            Новая запись
          </h2>
          {selectedMaster && step !== 'master' ? (
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
              {clientMasterLabel(selectedMaster)}
              {selectedService ? ` · ${selectedService.name}` : null}
            </p>
          ) : (
            <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">Выберите мастера, услугу и свободное время.</p>
          )}
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-5">
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
              {servicesQuery.isLoading ? (
                <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем услуги…</p>
              ) : servicesQuery.isError ? (
                <p className="text-sm text-red-700 dark:text-red-300">{getUserFacingError(servicesQuery.error)}</p>
              ) : masterServices.length === 0 ? (
                <p className="text-sm text-stone-500 dark:text-stone-400">Нет доступных услуг.</p>
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
                        <p className="font-medium text-stone-900 dark:text-stone-100">{s.name}</p>
                        <p className="text-xs text-stone-500 dark:text-stone-400">
                          {s.duration_min} мин · {s.price} {s.currency}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <button
                type="button"
                className="text-sm text-teal-700 dark:text-teal-400"
                onClick={() => setStep('master')}
              >
                Другой мастер
              </button>
            </div>
          ) : null}

          {step === 'slot' && selectedService ? (
            <div className="space-y-4">
              <label className="block max-w-xs">
                <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Дата</span>
                <input
                  type="date"
                  value={dateInput}
                  min={todayInput}
                  max={maxDateInput}
                  onChange={(event) => {
                    setDateInput(event.target.value)
                    setSlotIso(null)
                    createBooking.reset()
                  }}
                  className={cn(bookingDateFieldClass, 'mt-1 [color-scheme:light] dark:[color-scheme:dark]')}
                />
              </label>

              <div>
                <p className="mb-2 text-sm font-medium text-stone-700 dark:text-stone-300">Время</p>
                {slotsQuery.isLoading ? (
                  <p className="text-sm text-stone-500 dark:text-stone-400">Ищем свободные слоты...</p>
                ) : slotsError ? (
                  <p className="text-sm text-red-700 dark:text-red-300">{slotsError}</p>
                ) : freeSlots.length === 0 ? (
                  <p className="text-sm text-stone-500 dark:text-stone-400">На эту дату свободного времени нет.</p>
                ) : (
                  <div className="grid max-h-64 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-4 md:grid-cols-5">
                    {freeSlots.map((slot) => (
                      <button
                        key={slot.start_at}
                        type="button"
                        disabled={isPending}
                        onClick={() => {
                          createBooking.reset()
                          setSlotIso(slot.start_at)
                        }}
                        className={bookingSlotButtonClass(slotIso === slot.start_at)}
                      >
                        {formatSlotTime(slot.start_at, clientTimeZone)}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {slotIso ? (
                <p className="text-sm text-stone-600 dark:text-stone-400">
                  Выбрано: {formatSlotDateTime(slotIso, clientTimeZone)}
                </p>
              ) : null}

              <button
                type="button"
                className="text-sm text-teal-700 dark:text-teal-400"
                onClick={() => setStep('service')}
              >
                Другая услуга
              </button>
            </div>
          ) : null}

          {createBooking.isError ? (
            <p className="text-sm text-red-700 dark:text-red-300" role="alert">
              {getUserFacingError(createBooking.error)}
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap justify-end gap-2 border-t border-stone-200 px-6 py-5 dark:border-stone-700">
          <button
            type="button"
            disabled={isPending}
            onClick={onClose}
            className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
          >
            Отмена
          </button>
          {step === 'slot' ? (
            <button
              type="button"
              disabled={isPending || !slotIso}
              onClick={() => createBooking.mutate()}
              className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
            >
              {isPending ? 'Записываем...' : 'Записаться'}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
