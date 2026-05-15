import { NavLink, Outlet } from 'react-router-dom'

import { cn } from '../../lib/forms'

const links = [
  { to: '/dashboard', label: 'Дашборд' },
  { to: '/services', label: 'Услуги' },
  { to: '/clients', label: 'Клиенты' },
  { to: '/bookings', label: 'Записи' },
  { to: '/schedule', label: 'Расписание' },
]

export function AppLayout() {
  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-8 pr-14">
      <header className="mb-10 flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-6 dark:border-slate-800">
        <NavLink
          to="/dashboard"
          className="text-xl font-semibold tracking-tight text-emerald-700 dark:text-emerald-300"
        >
          Retention Studio
        </NavLink>
        <nav className="flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-300">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                cn(
                  'rounded-md px-2 py-1 transition-colors hover:text-slate-900 dark:hover:text-white',
                  isActive ? 'bg-slate-200 text-slate-900 dark:bg-slate-800 dark:text-white' : '',
                )
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}
