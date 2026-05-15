import { useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { meApi } from '../api/auth'
import { getScheduleApi, putScheduleApi } from '../api/masters'
import { queryClient } from '../lib/query'

const defaultWeekday = [0, 1, 2, 3, 4].map((weekday) => ({
  weekday,
  start_time: '10:00',
  end_time: '18:00',
}))

export function SchedulePage() {
  const navigate = useNavigate()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const schedule = useQuery({
    queryKey: ['schedule'],
    queryFn: getScheduleApi,
    enabled: me.isSuccess,
  })

  useEffect(() => {
    if (me.isError) navigate('/login')
  }, [me.isError, navigate])

  const save = useMutation({
    mutationFn: putScheduleApi,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['schedule'] })
    },
  })

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Расписание</h2>
      <p className="text-slate-600 dark:text-slate-400">
        Шаблон Пн–Пт 10:00–18:00 по часовому поясу профиля. Исключения можно расширить позже через API.
      </p>
      <button
        type="button"
        onClick={() =>
          save.mutate({
            weekly_rules: defaultWeekday,
            overrides: [],
          })
        }
        className="rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white dark:bg-emerald-500 dark:text-slate-950"
      >
        Сохранить шаблон
      </button>
      <pre className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200">
        {JSON.stringify(schedule.data, null, 2)}
      </pre>
    </div>
  )
}
