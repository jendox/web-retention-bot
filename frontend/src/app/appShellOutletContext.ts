export type AppCabinet = 'client' | 'master'

/** Контекст дочерних маршрутов внутри {@link AppLayout} (react-router Outlet). */
export type AppShellOutletContext = {
  /** Нет профиля мастера — только клиентский кабинет. */
  isClientOnly: boolean
  /** Текущий кабинет по URL-префиксу. */
  cabinet: AppCabinet
  /** IANA timezone текущего мастера; в клиентском кабинете используется локальная timezone браузера. */
  masterTimeZone?: string
}
