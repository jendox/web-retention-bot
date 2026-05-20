import { useSearchParams } from 'react-router-dom'

import { NotificationsListSection, parseNotificationsPage } from '../components/notifications/NotificationsListSection'
import type { PageSize } from '../lib/pagination'

export function NotificationsPage() {
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
          Сообщения о записях, приглашениях и других событиях в кабинете.
        </p>
      </header>

      <section className="rounded-xl border border-stone-200/90 bg-white p-5 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
        <NotificationsListSection
          page={page}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      </section>
    </div>
  )
}
