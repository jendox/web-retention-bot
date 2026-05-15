import { useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { logoutApi, meApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { masterMeApi } from '../../api/masters'
import { cn } from '../../lib/forms'
import { queryClient } from '../../lib/query'
import {
  IconBriefcase,
  IconCalendar,
  IconClipboard,
  IconOverview,
  IconUserCircle,
  IconUsers,
} from './navIcons'

const masterNav = [
  { to: '/dashboard', label: 'Обзор', icon: IconOverview },
  { to: '/schedule', label: 'Расписание', icon: IconCalendar },
  { to: '/clients', label: 'Клиенты', icon: IconUsers },
  { to: '/services', label: 'Услуги', icon: IconBriefcase },
  { to: '/bookings', label: 'Записи', icon: IconClipboard },
]

const clientNav = [{ to: '/client', label: 'Обзор', icon: IconOverview }]

function initials(displayName: string | undefined, email: string) {
  if (displayName?.trim()) {
    const parts = displayName.trim().split(/\s+/)
    const a = parts[0]?.[0]
    const b = parts.length > 1 ? parts[parts.length - 1]?.[0] : parts[0]?.[1]
    return `${a ?? ''}${b ?? ''}`.toUpperCase().slice(0, 2) || email.slice(0, 2).toUpperCase()
  }
  return email.slice(0, 2).toUpperCase()
}

export function AppLayout() {
  const navigate = useNavigate()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useQuery({
    queryKey: ['master'],
    queryFn: masterMeApi,
    enabled: me.isSuccess,
    retry: false,
  })

  const logout = useMutation({
    mutationFn: logoutApi,
    onSuccess: async () => {
      await queryClient.removeQueries({ queryKey: ['me'] })
      await queryClient.removeQueries({ queryKey: ['master'] })
      navigate('/login')
    },
  })

  const email = me.data?.email ?? ''
  const name = master.data?.display_name

  const isClientOnly =
    me.isSuccess &&
    master.isFetched &&
    master.isError &&
    master.error instanceof ApiError &&
    master.error.status === 404

  const shellLoading = me.isLoading || (me.isSuccess && master.isPending)

  const displayName = isClientOnly ? (email.split('@')[0] || 'Клиент') : (name ?? 'Мастер')
  const cabinetLabel = isClientOnly ? 'кабинет клиента' : 'кабинет мастера'
  const homePath = isClientOnly ? '/client' : '/dashboard'
  const navItems = isClientOnly ? clientNav : masterNav

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  if (shellLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-100 dark:bg-stone-950">
        <p className="text-sm text-stone-500 dark:text-stone-400">Загрузка…</p>
      </div>
    )
  }

  if (!me.data) {
    return null
  }

  return (
    <div className="flex h-screen min-h-0 overflow-hidden bg-stone-100 dark:bg-stone-950">
      <aside className="flex h-full min-h-0 w-64 shrink-0 flex-col overflow-y-auto border-r border-stone-200 bg-stone-50 dark:border-stone-800 dark:bg-stone-900">
        <NavLink
          to={homePath}
          className="flex items-center gap-3 border-b border-stone-200/80 px-4 py-5 dark:border-stone-800"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-600 text-sm font-semibold text-white shadow-sm shadow-teal-900/20">
            R
          </div>
          <div className="min-w-0">
            <p className="truncate font-semibold tracking-tight text-stone-900 dark:text-stone-50">Retention Studio</p>
            <p className="text-xs text-stone-500 dark:text-stone-400">{cabinetLabel}</p>
          </div>
        </NavLink>

        <p className="px-4 pt-4 text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500 dark:text-stone-400">
          Меню
        </p>
        <nav className="flex flex-1 flex-col gap-0.5 px-2 py-3">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-stone-200/90 text-stone-900 dark:bg-stone-800 dark:text-stone-50'
                    : 'text-stone-600 hover:bg-stone-200/50 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-stone-800/60 dark:hover:text-stone-100',
                )
              }
            >
              <Icon className="h-5 w-5 shrink-0 opacity-80" />
              {label}
            </NavLink>
          ))}
        </nav>

        {!isClientOnly ? (
          <div className="mx-2 mb-2 rounded-lg border border-dashed border-stone-300 bg-white/60 px-3 py-3 dark:border-stone-600 dark:bg-stone-950/40">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">
              Как клиент
            </p>
            <p className="mt-1 text-xs leading-snug text-stone-600 dark:text-stone-400">
              Тот же аккаунт может записываться к другим мастерам — отдельный экран без путаницы с расписанием.
            </p>
            <NavLink
              to="/client"
              className={({ isActive }) =>
                cn(
                  'mt-2 flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-teal-100 text-teal-900 dark:bg-teal-950/50 dark:text-teal-100'
                    : 'text-teal-800 hover:bg-teal-50 dark:text-teal-300 dark:hover:bg-teal-950/30',
                )
              }
            >
              <IconUserCircle className="h-4 w-4 shrink-0" />
              Личный кабинет
            </NavLink>
          </div>
        ) : null}

        <div className="mt-auto border-t border-stone-200 p-3 dark:border-stone-800">
          <p className="px-1 text-xs text-stone-500 dark:text-stone-400">Нужна помощь?</p>
          <p className="px-1 text-xs text-stone-600 dark:text-stone-500">Напишите в поддержку из настроек (скоро).</p>
        </div>

        <div className="flex items-center gap-3 border-t border-stone-200 p-3 dark:border-stone-800">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-stone-200 text-xs font-semibold text-stone-700 dark:bg-stone-700 dark:text-stone-200">
            {me.isSuccess ? initials(isClientOnly ? displayName : name, email) : '…'}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-stone-900 dark:text-stone-100">{displayName}</p>
            <p className="truncate text-xs text-stone-500 dark:text-stone-400">{email}</p>
          </div>
          <button
            type="button"
            onClick={() => logout.mutate()}
            className="shrink-0 rounded-md border border-stone-300 px-2 py-1 text-xs font-medium text-stone-700 transition hover:bg-stone-100 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
          >
            Выйти
          </button>
        </div>
      </aside>

      <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10 lg:py-10">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
