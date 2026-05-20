import { useEffect, useRef } from 'react'

import { BookingCreatedNotice } from '../booking/BookingCreatedNotice'
import { getUserFacingError } from '../../lib/apiErrors'
import { useClientCabinet } from './ClientCabinetContext'

const BOOKING_NOTICE_MS = 12_000

export function ClientCabinetAlerts() {
  const {
    useMocks,
    me,
    dataError,
    bookingsOverviewError,
    myMastersError,
    bookingCreatedNotice,
    clearBookingCreatedNotice,
  } = useClientCabinet()

  const noticeRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!bookingCreatedNotice) {
      return
    }
    noticeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    const timer = window.setTimeout(() => clearBookingCreatedNotice(), BOOKING_NOTICE_MS)
    return () => window.clearTimeout(timer)
  }, [bookingCreatedNotice, clearBookingCreatedNotice])

  return (
    <>
      {bookingCreatedNotice ? (
        <BookingCreatedNotice
          innerRef={noticeRef}
          primaryLine={`${bookingCreatedNotice.master_display_name} · ${bookingCreatedNotice.service_name}`}
          startAt={bookingCreatedNotice.start_at}
          durationMin={bookingCreatedNotice.duration_min}
          footnote={
            useMocks
              ? 'Демо-запись: после перезагрузки страницы она не сохранится.'
              : undefined
          }
        />
      ) : null}

      {!useMocks && me && !me.email_verified ? (
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100"
        >
          Подтвердите email по ссылке из письма — после этого станут доступны записи, уведомления и запись к мастеру.
        </div>
      ) : null}

      {!useMocks && dataError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200">
          <p>Не удалось загрузить данные. Обновите страницу или попробуйте позже.</p>
          {bookingsOverviewError ? (
            <p className="mt-1 text-xs opacity-90">Записи: {getUserFacingError(bookingsOverviewError)}</p>
          ) : null}
          {myMastersError ? (
            <p className="mt-1 text-xs opacity-90">Мастера: {getUserFacingError(myMastersError)}</p>
          ) : null}
        </div>
      ) : null}
    </>
  )
}
