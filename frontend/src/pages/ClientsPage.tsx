import { useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { meApi } from '../api/auth'
import { clientsCreateApi, clientsListApi } from '../api/clients'
import { queryClient } from '../lib/query'

const inputClass =
  'rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950'

export function ClientsPage() {
  const navigate = useNavigate()
  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const clients = useQuery({
    queryKey: ['clients'],
    queryFn: clientsListApi,
    enabled: me.isSuccess,
  })
  const form = useForm({ defaultValues: { display_name: '', phone: '', email: '' } })

  useEffect(() => {
    if (me.isError) navigate('/login')
  }, [me.isError, navigate])

  const create = useMutation({
    mutationFn: clientsCreateApi,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['clients'] })
      form.reset()
    },
  })

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Клиенты</h2>
      <form
        className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 md:grid-cols-2 dark:border-slate-800 dark:bg-slate-900"
        onSubmit={form.handleSubmit((vals) =>
          create.mutate({
            display_name: vals.display_name,
            phone: vals.phone || undefined,
            email: vals.email || undefined,
          }),
        )}
      >
        <input {...form.register('display_name', { required: true })} placeholder="Имя" className={inputClass} />
        <input {...form.register('phone')} placeholder="Телефон" className={inputClass} />
        <input {...form.register('email')} placeholder="Email" className={inputClass} />
        <button
          className="rounded-md bg-emerald-600 px-3 py-2 font-semibold text-white dark:bg-emerald-500 dark:text-slate-950"
          type="submit"
        >
          Добавить
        </button>
      </form>

      <div className="space-y-3">
        {(clients.data ?? []).map((row) => (
          <div key={row.client.id} className="rounded-lg border border-slate-200 p-4 dark:border-slate-800">
            <p className="text-lg font-medium">{row.client.display_name}</p>
            <p className="text-sm text-slate-600 dark:text-slate-400">{row.client.phone ?? '—'}</p>
            <p className="text-sm text-slate-600 dark:text-slate-400">{row.client.email ?? '—'}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
