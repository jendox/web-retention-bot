import { useEffect, useMemo, useState } from 'react'

import type { BookingClientListItem } from '../../api/bookings'
import { cn } from '../../lib/forms'
import {
  mockFreeSlotsForMaster,
  type ClientMasterView,
  type MockBookableService,
} from '../../mocks/clientCabinetMocks'

function addMinutesIso(isoStart: string, minutes: number): string {
  return new Date(new Date(isoStart).getTime() + minutes * 60_000).toISOString()
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
  masters: ClientMasterView[]
  services: MockBookableService[]
  /** Все записи (базовые моки + добавленные в сессии) — чтобы слоты не пересекались. */
  existingBookings: BookingClientListItem[]
  initialMasterId?: string | null
  onConfirm: (booking: BookingClientListItem) => void
}

export function ClientDemoBookingModal({
  onClose,
  masters,
  services,
  existingBookings,
  initialMasterId,
  onConfirm,
}: Props) {
  const resolvedInitialMaster =
    initialMasterId && masters.some((m) => m.master_id === initialMasterId) ? initialMasterId : null

  const [step, setStep] = useState<Step>(resolvedInitialMaster ? 'service' : 'master')
  const [masterId, setMasterId] = useState<string | null>(resolvedInitialMaster)
  const [serviceId, setServiceId] = useState<string | null>(null)
  const [slotIso, setSlotIso] = useState<string | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const selectedMaster = masters.find((m) => m.master_id === masterId) ?? null
  const masterServices = useMemo(() => services.filter((s) => s.master_id === masterId), [services, masterId])
  const selectedService = masterServices.find((s) => s.id === serviceId) ?? null

  const freeSlots = useMemo(() => {
    if (!masterId || !selectedService) {
      return []
    }
    return mockFreeSlotsForMaster(masterId, existingBookings, new Date(), 18, selectedService.duration_min)
  }, [masterId, selectedService, existingBookings])

  const goConfirm = () => {
    if (!selectedMaster || !selectedService || !slotIso) {
      return
    }
    const booking: BookingClientListItem = {
      id: `mock-b-${Date.now()}`,
      master_id: selectedMaster.master_id,
      client_id: 'mock-client-self',
      service_id: selectedService.id,
      start_at: slotIso,
      end_at: addMinutesIso(slotIso, selectedService.duration_min),
      duration_min: selectedService.duration_min,
      price_snapshot: selectedService.price,
      currency_snapshot: selectedService.currency,
      status: 'scheduled',
      master_display_name: selectedMaster.display_name,
      service_name: selectedService.name,
    }
    onConfirm(booking)
    onClose()
  }

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
            <p className="mt-0.5 text-xs text-stone-500 dark:text-stone-400">Демо: без сохранения на сервере.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-stone-500 hover:bg-stone-100 hover:text-stone-900 dark:hover:bg-stone-800 dark:hover:text-stone-100"
          >
            <span className="sr-only">Закрыть</span>
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <ol className="mb-4 flex flex-wrap gap-x-2 gap-y-1 text-[11px] font-medium uppercase tracking-wide text-stone-500 dark:text-stone-400">
            {(
              [
                { id: 'master' as const, label: 'Мастер' },
                { id: 'service' as const, label: 'Услуга' },
                { id: 'slot' as const, label: 'Время' },
                { id: 'confirm' as const, label: 'Готово' },
              ] as const
            ).map((item, i) => {
              const order = ['master', 'service', 'slot', 'confirm']
              const done = order.indexOf(step) > order.indexOf(item.id)
              return (
                <li key={item.id} className="flex items-center gap-2">
                  {i > 0 ? <span className="text-stone-300 dark:text-stone-600">·</span> : null}
                  <span
                    className={cn(
                      step === item.id && 'text-teal-700 dark:text-teal-300',
                      done && 'text-emerald-600 dark:text-emerald-400',
                    )}
                  >
                    {item.label}
                  </span>
                </li>
              )
            })}
          </ol>

          {step === 'master' ? (
            <ul className="space-y-2">
              {masters.map((m) => (
                <li key={m.link_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setMasterId(m.master_id)
                      setServiceId(null)
                      setSlotIso(null)
                      setStep('service')
                    }}
                    className={cn(
                      'flex w-full rounded-xl border px-4 py-3 text-left text-sm transition-colors',
                      masterId === m.master_id
                        ? 'border-teal-500 bg-teal-50 dark:border-teal-600 dark:bg-teal-950/40'
                        : 'border-stone-200 hover:border-stone-300 hover:bg-stone-50 dark:border-stone-700 dark:hover:border-stone-600 dark:hover:bg-stone-800/40',
                    )}
                  >
                    <span className="font-medium text-stone-900 dark:text-stone-50">{m.display_name}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          {step === 'service' && masterId ? (
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => setStep('master')}
                className="text-xs font-medium text-teal-700 hover:underline dark:text-teal-400"
              >
                ← Сменить мастера
              </button>
              <p className="text-sm text-stone-600 dark:text-stone-400">{selectedMaster?.display_name}</p>
              <ul className="space-y-2">
                {masterServices.map((svc) => (
                  <li key={svc.id}>
                    <button
                      type="button"
                      onClick={() => {
                        setServiceId(svc.id)
                        setSlotIso(null)
                        setStep('slot')
                      }}
                      className={cn(
                        'flex w-full flex-col rounded-xl border px-4 py-3 text-left text-sm transition-colors',
                        serviceId === svc.id
                          ? 'border-teal-500 bg-teal-50 dark:border-teal-600 dark:bg-teal-950/40'
                          : 'border-stone-200 hover:border-stone-300 hover:bg-stone-50 dark:border-stone-700 dark:hover:border-stone-600 dark:hover:bg-stone-800/40',
                      )}
                    >
                      <span className="font-medium text-stone-900 dark:text-stone-50">{svc.name}</span>
                      <span className="text-xs text-stone-500 dark:text-stone-400">
                        {svc.duration_min} мин · {svc.price} {svc.currency}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {step === 'slot' && selectedService ? (
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => setStep('service')}
                className="text-xs font-medium text-teal-700 hover:underline dark:text-teal-400"
              >
                ← Другая услуга
              </button>
              <p className="text-sm font-medium text-stone-800 dark:text-stone-200">{selectedService.name}</p>
              {freeSlots.length === 0 ? (
                <p className="text-sm text-stone-500 dark:text-stone-400">Нет свободных окон в демо-расписании.</p>
              ) : (
                <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {freeSlots.map((iso) => (
                    <li key={iso}>
                      <button
                        type="button"
                        onClick={() => {
                          setSlotIso(iso)
                          setStep('confirm')
                        }}
                        className={cn(
                          'w-full rounded-lg border px-2 py-2 text-center text-xs font-medium transition-colors',
                          slotIso === iso
                            ? 'border-teal-500 bg-teal-50 text-teal-900 dark:border-teal-600 dark:bg-teal-950/50 dark:text-teal-100'
                            : 'border-stone-200 text-stone-800 hover:border-teal-400 hover:bg-stone-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800/60',
                        )}
                      >
                        {formatSlotLabel(iso)}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}

          {step === 'confirm' && selectedMaster && selectedService && slotIso ? (
            <div className="space-y-4">
              <button
                type="button"
                onClick={() => setStep('slot')}
                className="text-xs font-medium text-teal-700 hover:underline dark:text-teal-400"
              >
                ← Другое время
              </button>
              <dl className="space-y-2 rounded-xl border border-stone-100 bg-stone-50/80 px-4 py-3 text-sm dark:border-stone-800 dark:bg-stone-950/40">
                <div className="flex justify-between gap-2">
                  <dt className="text-stone-500 dark:text-stone-400">Мастер</dt>
                  <dd className="text-right font-medium text-stone-900 dark:text-stone-50">{selectedMaster.display_name}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-stone-500 dark:text-stone-400">Услуга</dt>
                  <dd className="text-right font-medium text-stone-900 dark:text-stone-50">{selectedService.name}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-stone-500 dark:text-stone-400">Время</dt>
                  <dd className="text-right font-medium text-stone-900 dark:text-stone-50">{formatSlotLabel(slotIso)}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-stone-500 dark:text-stone-400">Стоимость</dt>
                  <dd className="text-right font-medium text-stone-900 dark:text-stone-50">
                    {selectedService.price} {selectedService.currency}
                  </dd>
                </div>
              </dl>
              <button
                type="button"
                onClick={goConfirm}
                className="w-full rounded-xl bg-teal-600 py-3 text-sm font-semibold text-white shadow-sm hover:bg-teal-500 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400"
              >
                Подтвердить запись (демо)
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
