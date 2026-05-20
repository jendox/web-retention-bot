import { useQuery } from '@tanstack/react-query'
import { Navigate, Outlet, useOutletContext } from 'react-router-dom'

import type { AppShellOutletContext } from '../../app/appShellOutletContext'
import { meApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { useMasterMe } from '../../hooks/useMasterMe'

/** Экраны кабинета мастера — только для пользователей с профилем мастера. */
export function RequireMasterOutlet() {
  const shellContext = useOutletContext<AppShellOutletContext>()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useMasterMe(me.isSuccess)

  if (me.isLoading || !me.data || (me.isSuccess && !master.isFetched)) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-sm text-stone-500 dark:text-stone-400">Загрузка…</p>
      </div>
    )
  }

  if (master.isError && master.error instanceof ApiError && master.error.status === 404) {
    return <Navigate to="/client" replace />
  }

  if (!master.data) {
    return <Navigate to="/client" replace />
  }

  return <Outlet context={shellContext} />
}
