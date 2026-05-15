import { useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { meApi } from '../api/auth'
import { bookingsCancelApi, bookingsListApi } from '../api/bookings'
import { queryClient } from '../lib/query'

export function BookingsPage() {
  const navigate = useNavigate()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const bookings = useQuery({
    queryKey: ['bookings'],
    queryFn: bookingsListApi,
    enabled: me.isSuccess,
  })

  useEffect(() => {
    if (me.isError) navigate('/login')
  }, [me.isError, navigate])

  const cancel = useMutation({
    mutationFn: bookingsCancelApi,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['bookings'] })
    },
  })

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Записи</h2>
      <div className="space-y-3">
        {(bookings.data ?? []).map((b) => (
          <div
            key={b.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-4 dark:border-slate-800"
          >
            <div>
              <p className="font-semibold">{new Date(b.start_at).toLocaleString()}</p>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {b.duration_min} мин · {b.price_snapshot} {b.currency_snapshot} · {b.status}
              </p>
            </div>
            {b.status === 'scheduled' && (
              <button
                type="button"
                onClick={() => cancel.mutate(b.id)}
                className="rounded-md border border-slate-300 px-3 py-1 text-sm dark:border-slate-600"
              >
                Отменить
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
