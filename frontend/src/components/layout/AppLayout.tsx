import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import type { AppCabinet, AppShellOutletContext } from '../../app/appShellOutletContext'

import { logoutApi, meApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { useMasterMe } from '../../hooks/useMasterMe'
import { cn } from '../../lib/forms'
import { queryClient } from '../../lib/query'
import {
  IconBell,
  IconAnalytics,
  IconBriefcase,
  IconCalendar,
  IconClipboard,
  IconLogout,
  IconMenu,
  IconOverview,
  IconSettings,
  IconUserCircle,
  IconUsers,
  IconX,
} from './navIcons'
import { useNotificationsUnreadCount } from '../notifications/notificationsQueries'

type NavItem = {
  to: string
  label: string
  icon: typeof IconOverview
  badge?: number
}

const clientNav = (unread: number): NavItem[] => [
  { to: '/client', label: 'Обзор', icon: IconOverview },
  { to: '/client/masters', label: 'Мои мастера', icon: IconUsers },
  { to: '/client/visits', label: 'Записи', icon: IconClipboard },
  {
    to: '/client/notifications',
    label: 'Уведомления',
    icon: IconBell,
    badge: unread > 0 ? unread : undefined,
  },
  { to: '/client/settings', label: 'Настройки', icon: IconSettings },
]

const masterNav = (unread: number): NavItem[] => [
  { to: '/master', label: 'Обзор', icon: IconOverview },
  { to: '/master/schedule', label: 'Расписание', icon: IconCalendar },
  { to: '/master/analytics', label: 'Аналитика', icon: IconAnalytics },
  { to: '/master/clients', label: 'Клиенты', icon: IconUsers },
  { to: '/master/services', label: 'Услуги', icon: IconBriefcase },
  { to: '/master/bookings', label: 'Записи', icon: IconClipboard },
  {
    to: '/master/notifications',
    label: 'Уведомления',
    icon: IconBell,
    badge: unread > 0 ? unread : undefined,
  },
  { to: '/master/settings', label: 'Настройки', icon: IconSettings },
]

function initials(displayName: string | undefined, email: string) {
  if (displayName?.trim()) {
    const parts = displayName.trim().split(/\s+/)
    const a = parts[0]?.[0]
    const b = parts.length > 1 ? parts[parts.length - 1]?.[0] : parts[0]?.[1]
    return `${a ?? ''}${b ?? ''}`.toUpperCase().slice(0, 2) || email.slice(0, 2).toUpperCase()
  }
  return email.slice(0, 2).toUpperCase()
}

function cabinetFromPath(pathname: string): AppCabinet {
  return pathname.startsWith('/master') ? 'master' : 'client'
}

export function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useMasterMe(me.isSuccess)
  const cabinet = cabinetFromPath(location.pathname)

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

  const liveMaster404 =
    master.isFetched &&
    master.isError &&
    master.error instanceof ApiError &&
    master.error.status === 404

  const isMasterUser = Boolean(master.data)
  const isClientOnly = Boolean(me.isSuccess && email) && !isMasterUser && liveMaster404
  const isClientCabinet = cabinet === 'client'
  const showClientCabinetLink = isMasterUser && !isClientCabinet
  const showMasterCabinetLink = isMasterUser && isClientCabinet

  const shellLoading = me.isLoading || (me.isSuccess && !master.isFetched)

  const clientDisplayName = me.data?.client_display_name?.trim()
  const displayName = isClientCabinet
    ? clientDisplayName || email.split('@')[0] || 'Клиент'
    : (name ?? 'Мастер')
  const cabinetLabel = isClientCabinet ? 'кабинет клиента' : 'кабинет мастера'
  const homePath = isClientCabinet ? '/client' : '/master'
  const notificationsUnread = useNotificationsUnreadCount(me.isSuccess, cabinet)
  const navItems = isClientCabinet ? clientNav(notificationsUnread) : masterNav(notificationsUnread)

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

  const renderSidebarContent = (mode: 'full' | 'rail' | 'drawer') => {
    const compact = mode === 'rail'

    return (
      <>
        <NavLink
          to={homePath}
          title={compact ? 'Retention Studio' : undefined}
          onClick={mode === 'drawer' ? () => setMobileNavOpen(false) : undefined}
          className={cn(
            'flex items-center border-b border-stone-200/80 dark:border-stone-800',
            compact ? 'justify-center px-3 py-4' : 'gap-3 px-4 py-5',
          )}
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-600 text-sm font-semibold text-white shadow-sm shadow-teal-900/20">
            R
          </div>
          {!compact ? (
            <div className="min-w-0">
              <p className="truncate font-semibold tracking-tight text-stone-900 dark:text-stone-50">Retention Studio</p>
              <p className="text-xs text-stone-500 dark:text-stone-400">{cabinetLabel}</p>
            </div>
          ) : null}
        </NavLink>

        {!compact ? (
          <p className="px-4 pt-4 text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500 dark:text-stone-400">
            Меню
          </p>
        ) : null}
        <nav className={cn('flex flex-1 flex-col gap-0.5 py-3', compact ? 'px-2' : 'px-2')}>
          {navItems.map(({ to, label, icon: Icon, badge }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/client' || to === '/master'}
              title={compact ? label : undefined}
              onClick={mode === 'drawer' ? () => setMobileNavOpen(false) : undefined}
              className={({ isActive }) =>
                cn(
                  'flex items-center rounded-lg text-sm font-medium transition-colors',
                  compact ? 'justify-center px-2 py-3' : 'gap-3 px-3 py-2.5',
                  isActive
                    ? 'bg-stone-200/90 text-stone-900 dark:bg-stone-800 dark:text-stone-50'
                    : 'text-stone-600 hover:bg-stone-200/50 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-stone-800/60 dark:hover:text-stone-100',
                )
              }
            >
              <Icon className="h-5 w-5 shrink-0 opacity-80" />
              {!compact ? (
                <>
                  <span className="min-w-0 flex-1">{label}</span>
                  {badge != null ? (
                    <span className="rounded-full bg-teal-600 px-2 py-0.5 text-[10px] font-semibold text-white dark:bg-teal-500 dark:text-stone-950">
                      {badge > 99 ? '99+' : badge}
                    </span>
                  ) : null}
                </>
              ) : (
                <span className="sr-only">{label}</span>
              )}
            </NavLink>
          ))}
        </nav>

        {showClientCabinetLink ? (
          compact ? (
            <div className="mx-2 mb-2 border-t border-stone-200 pt-2 dark:border-stone-800">
              <NavLink
                to="/client"
                title="Личный кабинет"
                className={({ isActive }) =>
                  cn(
                    'flex items-center justify-center rounded-lg px-2 py-3 transition-colors',
                    isActive
                      ? 'bg-teal-100 text-teal-900 dark:bg-teal-950/50 dark:text-teal-100'
                      : 'text-teal-800 hover:bg-teal-50 dark:text-teal-300 dark:hover:bg-teal-950/30',
                  )
                }
              >
                <IconUserCircle className="h-5 w-5 shrink-0" />
                <span className="sr-only">Личный кабинет</span>
              </NavLink>
            </div>
          ) : (
            <div className="mx-2 mb-2 rounded-lg border border-dashed border-stone-300 bg-white/60 px-3 py-3 dark:border-stone-600 dark:bg-stone-950/40">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">
                Как клиент
              </p>
              <p className="mt-1 text-xs leading-snug text-stone-600 dark:text-stone-400">
                Ваши записи к другим мастерам — в личном кабинете, отдельно от расписания студии.
              </p>
              <NavLink
                to="/client"
                onClick={mode === 'drawer' ? () => setMobileNavOpen(false) : undefined}
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
          )
        ) : null}

        {showMasterCabinetLink ? (
          compact ? (
            <div className="mx-2 mb-2 border-t border-stone-200 pt-2 dark:border-stone-800">
              <NavLink
                to="/master"
                title="Кабинет мастера"
                className={({ isActive }) =>
                  cn(
                    'flex items-center justify-center rounded-lg px-2 py-3 transition-colors',
                    isActive
                      ? 'bg-teal-100 text-teal-900 dark:bg-teal-950/50 dark:text-teal-100'
                      : 'text-teal-800 hover:bg-teal-50 dark:text-teal-300 dark:hover:bg-teal-950/30',
                  )
                }
              >
                <IconBriefcase className="h-5 w-5 shrink-0" />
                <span className="sr-only">Кабинет мастера</span>
              </NavLink>
            </div>
          ) : (
            <div className="mx-2 mb-2 rounded-lg border border-dashed border-stone-300 bg-white/60 px-3 py-3 dark:border-stone-600 dark:bg-stone-950/40">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">
                Как мастер
              </p>
              <p className="mt-1 text-xs leading-snug text-stone-600 dark:text-stone-400">
                Расписание, клиенты и услуги вашей студии — в кабинете мастера.
              </p>
              <NavLink
                to="/master"
                onClick={mode === 'drawer' ? () => setMobileNavOpen(false) : undefined}
                className={({ isActive }) =>
                  cn(
                    'mt-2 flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-teal-100 text-teal-900 dark:bg-teal-950/50 dark:text-teal-100'
                      : 'text-teal-800 hover:bg-teal-50 dark:text-teal-300 dark:hover:bg-teal-950/30',
                  )
                }
              >
                <IconBriefcase className="h-4 w-4 shrink-0" />
                Кабинет мастера
              </NavLink>
            </div>
          )
        ) : null}

        {!compact ? (
          <div className="mt-auto border-t border-stone-200 p-3 dark:border-stone-800">
            <p className="px-1 text-xs text-stone-500 dark:text-stone-400">Нужна помощь?</p>
            <p className="px-1 text-xs text-stone-600 dark:text-stone-500">Напишите в поддержку из настроек (скоро).</p>
          </div>
        ) : (
          <div className="mt-auto" />
        )}

        <div
          className={cn(
            'flex items-center border-t border-stone-200 p-3 dark:border-stone-800',
            compact ? 'justify-center' : 'gap-3',
          )}
        >
          <div
            title={compact ? `${displayName} · ${email}` : undefined}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-stone-200 text-xs font-semibold text-stone-700 dark:bg-stone-700 dark:text-stone-200"
          >
            {me.isSuccess ? initials(isClientCabinet ? displayName : name, email) : '…'}
          </div>
          {!compact ? (
            <>
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
            </>
          ) : null}
        </div>

        {compact ? (
          <div className="border-t border-stone-200 p-2 dark:border-stone-800">
            <button
              type="button"
              title="Выйти"
              onClick={() => logout.mutate()}
              className="flex w-full items-center justify-center rounded-lg px-2 py-3 text-stone-600 transition hover:bg-stone-200/50 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-stone-800/60 dark:hover:text-stone-100"
            >
              <IconLogout className="h-5 w-5" />
              <span className="sr-only">Выйти</span>
            </button>
          </div>
        ) : null}
      </>
    )
  }

  return (
    <div className="flex h-dvh min-h-0 overflow-hidden bg-stone-100 dark:bg-stone-950">
      <aside className="hidden h-full min-h-0 w-20 shrink-0 flex-col overflow-y-auto border-r border-stone-200 bg-stone-50 md:flex lg:hidden dark:border-stone-800 dark:bg-stone-900">
        {renderSidebarContent('rail')}
      </aside>

      <aside className="hidden h-full min-h-0 w-64 shrink-0 flex-col overflow-y-auto border-r border-stone-200 bg-stone-50 lg:flex dark:border-stone-800 dark:bg-stone-900">
        {renderSidebarContent('full')}
      </aside>

      {mobileNavOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            aria-label="Закрыть меню"
            className="absolute inset-0 bg-stone-950/40"
            onClick={() => setMobileNavOpen(false)}
          />
          <aside className="relative flex h-full min-h-0 w-[min(20rem,calc(100vw-3rem))] flex-col overflow-y-auto border-r border-stone-200 bg-stone-50 shadow-xl dark:border-stone-800 dark:bg-stone-900">
            <button
              type="button"
              aria-label="Закрыть меню"
              onClick={() => setMobileNavOpen(false)}
              className="absolute right-3 top-3 rounded-lg p-2 text-stone-500 transition hover:bg-stone-200/60 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-stone-800 dark:hover:text-stone-100"
            >
              <IconX className="h-5 w-5" />
            </button>
            {renderSidebarContent('drawer')}
          </aside>
        </div>
      ) : null}

      <main className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-stone-200 bg-stone-50 px-4 md:hidden dark:border-stone-800 dark:bg-stone-900">
          <button
            type="button"
            aria-label="Открыть меню"
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen(true)}
            className="rounded-lg p-2 text-stone-600 transition hover:bg-stone-200/60 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-stone-800 dark:hover:text-stone-100"
          >
            <IconMenu className="h-6 w-6" />
          </button>
          <NavLink to={homePath} className="min-w-0 px-2 text-center">
            <p className="truncate text-sm font-semibold text-stone-900 dark:text-stone-50">Retention Studio</p>
            <p className="truncate text-xs text-stone-500 dark:text-stone-400">{cabinetLabel}</p>
          </NavLink>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-stone-200 text-xs font-semibold text-stone-700 dark:bg-stone-700 dark:text-stone-200">
            {me.isSuccess ? initials(isClientCabinet ? displayName : name, email) : '…'}
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 md:px-8 lg:px-10 lg:py-10">
            <Outlet
              context={{ isClientOnly, cabinet, masterTimeZone: master.data?.timezone } satisfies AppShellOutletContext}
            />
          </div>
        </div>
      </main>
    </div>
  )
}
