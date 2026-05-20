import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { bookingsMyListApi, type BookingListScope } from '../../api/bookings'
import { useClientCabinet } from '../../components/client/ClientCabinetContext'
import { ClientVisitRow } from '../../components/client/clientCabinetUi'
import { ListPagination } from '../../components/ui/ListPagination'
import { SegmentTabs } from '../../components/ui/SegmentTabs'
import { isBookingUpcoming } from '../../lib/bookingStatus'
import { parsePage, parsePageSize, type PageSize } from '../../lib/pagination'

type VisitScope = 'upcoming' | 'past'

function visitScopeFromParams(params: URLSearchParams): VisitScope {
  return params.get('visit_scope') === 'past' ? 'past' : 'upcoming'
}

function visitScopeToApi(scope: VisitScope): BookingListScope {
  return scope === 'upcoming' ? 'upcoming' : 'history'
}

export function ClientVisitsPage() {
  const { useMocks, me, mockBookings, canManageVisit, setVisitManage } = useClientCabinet()
  const [searchParams, setSearchParams] = useSearchParams()
  const visitScope = visitScopeFromParams(searchParams)
  const visitPage = parsePage(searchParams.get('visit_page'))
  const visitPageSize = parsePageSize(searchParams.get('visit_page_size'))

  const setVisitScope = (scope: VisitScope) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('visit_scope', scope)
      n.set('visit_page', '1')
      n.set('visit_page_size', String(visitPageSize))
      return n
    })
  }

  const setVisitPage = (p: number) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('visit_page', String(p))
      n.set('visit_page_size', String(visitPageSize))
      if (!n.get('visit_scope')) {
        n.set('visit_scope', visitScope)
      }
      return n
    })
  }

  const setVisitPageSize = (ps: PageSize) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('visit_scope', visitScope)
      n.set('visit_page', '1')
      n.set('visit_page_size', String(ps))
      return n
    })
  }

  const visitsLive = useQuery({
    queryKey: ['bookings', 'me', visitScope, visitPage, visitPageSize],
    queryFn: () =>
      bookingsMyListApi({
        scope: visitScopeToApi(visitScope),
        page: visitPage,
        page_size: visitPageSize,
      }),
    enabled: !useMocks && Boolean(me),
    retry: false,
  })

  useEffect(() => {
    if (!visitsLive.isSuccess || !visitsLive.data) {
      return
    }
    const totalPages = Math.max(1, Math.ceil(visitsLive.data.total / visitPageSize))
    if (visitPage > totalPages) {
      setVisitPage(totalPages)
    }
  }, [visitsLive.isSuccess, visitsLive.data, visitPage, visitPageSize])

  const mockVisitsForScope = useMocks
    ? mockBookings.filter((b) =>
        visitScope === 'upcoming' ? isBookingUpcoming(b, new Date()) : !isBookingUpcoming(b, new Date()),
      )
    : []

  const visitItems = useMocks ? mockVisitsForScope : (visitsLive.data?.items ?? [])
  const visitTotal = useMocks ? mockVisitsForScope.length : (visitsLive.data?.total ?? 0)
  const visitsLoading = !useMocks && visitsLive.isLoading

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Записи</h1>

      <SegmentTabs
        tabs={[
          { value: 'upcoming', label: 'Предстоящие' },
          { value: 'past', label: 'Прошедшие' },
        ]}
        value={visitScope}
        onChange={setVisitScope}
        ariaLabel="Фильтр записей"
      />
      <p className="text-sm text-stone-500 dark:text-stone-400">
        {visitScope === 'past'
          ? 'Завершённые, отменённые и прошедшие визиты. Отменённые отмечены в списке.'
          : 'Активные записи, которые ещё предстоят.'}
      </p>
      {visitsLoading ? (
        <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем записи…</p>
      ) : visitItems.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-stone-400">В этой категории пока пусто.</p>
      ) : (
        <>
          <ul className="space-y-2">
            {visitItems.map((b, i) => (
              <ClientVisitRow
                key={b.id}
                b={b}
                i={i}
                showActions={!useMocks && visitScope === 'upcoming' && canManageVisit(b)}
                onReschedule={() => setVisitManage({ booking: b, mode: 'reschedule' })}
                onCancel={() => setVisitManage({ booking: b, mode: 'cancel' })}
              />
            ))}
          </ul>
          {!useMocks && visitTotal > 0 ? (
            <ListPagination
              page={visitPage}
              pageSize={visitPageSize}
              total={visitTotal}
              onPageChange={setVisitPage}
              onPageSizeChange={setVisitPageSize}
            />
          ) : null}
        </>
      )}
    </section>
  )
}
