import { useEffect, useState, type MouseEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { availabilityApi } from '../../api/availability'
import { bookingsMyCancelApi, bookingsMyRescheduleApi, type BookingClientListItem } from '../../api/bookings'
import { getUserFacingError } from '../../lib/apiErrors'
import {
  bookingDateBounds,
  bookingDateFieldClass,
  formatSlotTime,
  toDateInputValue,
} from '../../lib/bookingSchedule'
import { bookingSlotButtonClass } from '../../lib/bookingSlots'
import { cn } from '../../lib/forms'

const dateLongFormatter = new Intl.DateTimeFormat('ru-RU', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})

function formatDateLong(date: Date) {
  return dateLongFormatter.format(date)
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

type Mode = 'reschedule' | 'cancel'

type Props = {
  booking: BookingClientListItem
  mode: Mode
  onClose: () => void
  onSuccess: () => void
}

export function ClientVisitManageModal({ booking, mode, onClose, onSuccess }: Props) {
  const [rescheduleDate, setRescheduleDate] = useState(() => toDateInputValue(new Date(booking.start_at)))
  const [rescheduleSlot, setRescheduleSlot] = useState<string | null>(null)

  const { min: todayValue, max: maxDateValue } = bookingDateBounds()

  const rescheduleSlots = useQuery({
    queryKey: ['availability', 'reschedule', booking.master_id, booking.service_id, rescheduleDate],
    queryFn: () =>
      availabilityApi({
        master_id: booking.master_id,
        service_id: booking.service_id,
        date: rescheduleDate,
      }),
    enabled: mode === 'reschedule' && Boolean(rescheduleDate),
  })

  const cancelBooking = useMutation({
    mutationFn: () => bookingsMyCancelApi(booking.id),
    onSuccess: () => {
      onSuccess()
      onClose()
    },
  })

  const reschedule = useMutation({
    mutationFn: () => {
      if (!rescheduleSlot) {
        throw new Error('Выберите новое время.')
      }
      return bookingsMyRescheduleApi(booking.id, rescheduleSlot)
    },
    onSuccess: () => {
      onSuccess()
      onClose()
    },
  })

  const isPending = mode === 'cancel' ? cancelBooking.isPending : reschedule.isPending

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isPending) {
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, isPending])

  const rescheduleSlotsError =
    rescheduleSlots.error instanceof Error ? getUserFacingError(rescheduleSlots.error) : null

  const handleOverlayClick = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget && !isPending) {
      onClose()
    }
  }

  if (mode === 'cancel') {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cancel-booking-title"
        onClick={handleOverlayClick}
      >
        <div
          className="w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-xl dark:border-stone-700 dark:bg-stone-900"
          onClick={(event) => event.stopPropagation()}
        >
          <h2 id="cancel-booking-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
            Отменить запись?
          </h2>
          <p className="mt-3 text-sm text-stone-600 dark:text-stone-400">
            Запись к «{booking.master_display_name}» на {formatSlotFull(booking.start_at)} ({booking.service_name}) будет
            отменена.
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
              onClick={onClose}
              className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
            >
              Оставить
            </button>
            <button
              type="button"
              disabled={cancelBooking.isPending}
              onClick={() => cancelBooking.mutate()}
              className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-50 dark:bg-rose-600 dark:hover:bg-rose-500"
            >
              {cancelBooking.isPending ? 'Отмена...' : 'Отменить запись'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reschedule-booking-title"
      onClick={handleOverlayClick}
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
            {booking.master_display_name} · {booking.service_name}
          </p>
          <p className="text-sm text-stone-500 dark:text-stone-400">Сейчас: {formatBookingDateTime(booking.start_at)}</p>
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
              className={cn(bookingDateFieldClass, 'mt-1 [color-scheme:light] dark:[color-scheme:dark]')}
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
            onClick={onClose}
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
  )
}
