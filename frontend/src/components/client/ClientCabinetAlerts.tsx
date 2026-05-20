import { getUserFacingError } from '../../lib/apiErrors'
import { useClientCabinet } from './ClientCabinetContext'

export function ClientCabinetAlerts() {
  const {
    useMocks,
    me,
    dataError,
    bookingsOverviewError,
    myMastersError,
    bookingSuccessNotice,
    demoBookingNotice,
  } = useClientCabinet()

  return (
    <>
      {bookingSuccessNotice ? (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100"
        >
          Запись сохранена.
        </div>
      ) : null}

      {demoBookingNotice ? (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100"
        >
          Запись добавлена в демо-список на этом экране. После перезагрузки страницы изменения не сохранятся.
        </div>
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
