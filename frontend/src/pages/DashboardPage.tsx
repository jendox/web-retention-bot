import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { logoutApi, meApi } from '../api/auth'
import { invitationsCreateApi } from '../api/invitations'
import { masterMeApi } from '../api/masters'
import { queryClient } from '../lib/query'

export function DashboardPage() {
  const navigate = useNavigate()
  const [inviteMessage, setInviteMessage] = useState<string>()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useQuery({
    queryKey: ['master'],
    queryFn: masterMeApi,
    enabled: me.isSuccess,
  })

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  const logout = useMutation({
    mutationFn: logoutApi,
    onSuccess: async () => {
      await queryClient.removeQueries({ queryKey: ['me'] })
      await queryClient.removeQueries({ queryKey: ['master'] })
      navigate('/login')
    },
  })

  const createInvite = useMutation({
    mutationFn: () => invitationsCreateApi({}),
    onSuccess: (payload) => {
      const relative = `/invite/${payload.token}`
      setInviteMessage(`Ссылка для клиента: ${window.location.origin}${relative}`)
    },
  })

  if (me.isLoading) {
    return <p className="text-slate-600 dark:text-slate-400">Загрузка…</p>
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-3xl font-semibold">Привет!</h2>
          <p className="text-slate-600 dark:text-slate-400">Управляйте профилем, услугами и записями.</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => createInvite.mutate()}
            className="rounded-md border border-emerald-600 px-4 py-2 text-sm font-semibold text-emerald-700 disabled:opacity-50 dark:border-emerald-400 dark:text-emerald-300"
          >
            Создать инвайт
          </button>
          <button
            type="button"
            onClick={() => logout.mutate()}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm dark:border-slate-700"
          >
            Выйти
          </button>
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <p className="text-sm text-slate-600 dark:text-slate-400">Учётная запись</p>
          <p className="text-xl font-semibold">{me.data?.email}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
            {me.data?.email_verified ? 'Email подтверждён' : 'Подтвердите email для безопасного доступа'}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <p className="text-sm text-slate-600 dark:text-slate-400">Профиль мастера</p>
          {master.data ? (
            <>
              <p className="text-xl font-semibold">{master.data.display_name}</p>
              <p className="text-slate-600 dark:text-slate-400">TZ: {master.data.timezone}</p>
            </>
          ) : (
            <p className="text-slate-600 dark:text-slate-400">Нет профиля</p>
          )}
        </div>
      </section>

      {inviteMessage && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-slate-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-slate-100">
          {inviteMessage}
        </div>
      )}
    </div>
  )
}
