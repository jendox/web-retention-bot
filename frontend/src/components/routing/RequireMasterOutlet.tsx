import { useQuery } from '@tanstack/react-query'
import { Navigate, Outlet } from 'react-router-dom'

import { meApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { masterMeApi } from '../../api/masters'

/** Экраны кабинета мастера — только для пользователей с профилем мастера. */
export function RequireMasterOutlet() {
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useQuery({
    queryKey: ['master'],
    queryFn: masterMeApi,
    enabled: me.isSuccess,
    retry: false,
  })

  if (me.isLoading || !me.data || master.isPending) {
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

  return <Outlet />
}
