import { useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { meApi } from '../api/auth'
import {
  serviceDeleteApi,
  servicesCreateApi,
  servicesListApi,
  type ServicePayload,
} from '../api/services'
import { queryClient } from '../lib/query'

const inputClass =
  'rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950'

export function ServicesPage() {
  const navigate = useNavigate()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const services = useQuery({
    queryKey: ['services'],
    queryFn: servicesListApi,
    enabled: me.isSuccess,
  })
  const form = useForm<ServicePayload>({
    defaultValues: {
      name: 'Консультация',
      description: '',
      duration_min: 60,
      price: '1500.00',
      currency: 'RUB',
      is_active: true,
      sort_order: 0,
    },
  })

  useEffect(() => {
    if (me.isError) navigate('/login')
  }, [me.isError, navigate])

  const create = useMutation({
    mutationFn: servicesCreateApi,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['services'] })
    },
  })

  const remove = useMutation({
    mutationFn: serviceDeleteApi,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['services'] })
    },
  })

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-semibold">Услуги</h2>
      <form
        className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 md:grid-cols-2 dark:border-slate-800 dark:bg-slate-900"
        onSubmit={form.handleSubmit((vals) => create.mutate(vals))}
      >
        <input {...form.register('name')} className={inputClass} />
        <input
          type="number"
          {...form.register('duration_min', { valueAsNumber: true })}
          className={inputClass}
        />
        <input {...form.register('price')} className={inputClass} />
        <input {...form.register('currency')} className={inputClass} />
        <button
          className="rounded-md bg-emerald-600 px-3 py-2 font-semibold text-white dark:bg-emerald-500 dark:text-slate-950"
          type="submit"
        >
          Добавить
        </button>
      </form>

      <div className="space-y-3">
        {(services.data ?? []).map((svc) => (
          <div
            key={svc.id}
            className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 p-4 dark:border-slate-800"
          >
            <div>
              <p className="text-lg font-medium">{svc.name}</p>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {svc.duration_min} мин · {svc.price} {svc.currency}
              </p>
            </div>
            <button
              type="button"
              onClick={() => remove.mutate(svc.id)}
              className="rounded-md border border-rose-500 px-3 py-1 text-sm text-rose-700 dark:text-rose-300"
            >
              Деактивировать
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
