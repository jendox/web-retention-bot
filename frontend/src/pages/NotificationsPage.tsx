import { useLocation, useOutletContext, useSearchParams } from 'react-router-dom'

import type { AppShellOutletContext } from '../app/appShellOutletContext'
import { cabinetFromPathname } from '../lib/appCabinet'
import { NotificationsListSection } from '../components/notifications/NotificationsListSection'
import { parseNotificationsPage } from '../components/notifications/notificationsQueries'
import { cn } from '../lib/forms'
import type { PageSize } from '../lib/pagination'
import { surfaceCardClass } from '../lib/surface'

export function NotificationsPage() {
  const { pathname } = useLocation()
  const outletContext = useOutletContext<AppShellOutletContext>()
  const cabinet = outletContext.cabinet ?? cabinetFromPathname(pathname)
  const isClientCabinet = cabinet === 'client'
  const notificationTimeZone = isClientCabinet ? outletContext.clientTimeZone : outletContext.masterTimeZone
  const [searchParams, setSearchParams] = useSearchParams()
  const { page, pageSize } = parseNotificationsPage(searchParams)

  const setPage = (p: number) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('page', String(p))
      n.set('page_size', String(pageSize))
      return n
    })
  }

  const setPageSize = (ps: PageSize) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('page', '1')
      n.set('page_size', String(ps))
      return n
    })
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Уведомления</h1>
        <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
          {isClientCabinet
            ? 'Записи к мастерам, переносы, отмены и подтверждение email.'
            : 'Действия клиентов, записи в студии и служебные сообщения.'}
        </p>
      </header>

      <section className={cn(surfaceCardClass, 'p-5')}>
        <NotificationsListSection
          page={page}
          pageSize={pageSize}
          cabinet={cabinet}
          timeZone={notificationTimeZone}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      </section>
    </div>
  )
}
