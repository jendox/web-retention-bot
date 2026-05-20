import type { AppCabinet } from '../app/appShellOutletContext'

/** Кабинет по URL, если outlet context ещё не проброшен вложенным layout. */
export function cabinetFromPathname(pathname: string): AppCabinet {
  return pathname.startsWith('/master') ? 'master' : 'client'
}
