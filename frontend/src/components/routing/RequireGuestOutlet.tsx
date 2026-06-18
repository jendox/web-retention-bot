import { useQuery } from '@tanstack/react-query'
import { Navigate, Outlet } from 'react-router-dom'

import { meApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { useMasterMe } from '../../hooks/useMasterMe'

/** Публичные auth-экраны доступны только гостям; залогиненных ведем в их кабинет. */
export function RequireGuestOutlet() {
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useMasterMe(me.isSuccess)

  if (me.isLoading || (me.isSuccess && !master.isFetched)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-100 dark:bg-stone-950">
        <p className="text-sm text-stone-500 dark:text-stone-400">Загрузка…</p>
      </div>
    )
  }

  if (me.isError || !me.data) {
    return <Outlet />
  }

  if (master.isSuccess) {
    return <Navigate to="/master" replace />
  }

  if (master.isError && master.error instanceof ApiError && master.error.status === 404) {
    return <Navigate to="/client" replace />
  }

  return <Navigate to="/client" replace />
}
