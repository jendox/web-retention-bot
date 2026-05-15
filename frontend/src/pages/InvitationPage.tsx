import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useParams } from 'react-router-dom'

import { availabilityApi } from '../api/availability'
import { bookingsCreateApi } from '../api/bookings'
import { invitationAcceptApi, invitationGetApi } from '../api/invitations'
import type { Service } from '../api/services'

const storageKey = (token: string) => `inviteClient:${token}`

const inputClass =
  'rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950'

export function InvitationPage() {
  const { token = '' } = useParams()
  const [stagingClientId, setStagingClientId] = useState<string | null>(null)

  const landing = useQuery({
    queryKey: ['invite', token],
    queryFn: () => invitationGetApi(token),
    enabled: Boolean(token),
  })

  const clientId = useMemo(() => {
    if (landing.data?.linked_client_id) {
      return landing.data.linked_client_id
    }
    if (stagingClientId) {
      return stagingClientId
    }
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(storageKey(token))
      return stored ?? null
    }
    return null
  }, [landing.data?.linked_client_id, stagingClientId, token])

  const acceptForm = useForm({ defaultValues: { display_name: '', phone: '', email: '' } })
  const accept = useMutation({
    mutationFn: (body: { display_name: string; phone?: string; email?: string }) =>
      invitationAcceptApi(token, body),
    onSuccess: async (payload) => {
      localStorage.setItem(storageKey(token), payload.client_id)
      setStagingClientId(payload.client_id)
      await landing.refetch()
      setStagingClientId(null)
    },
  })

  const [serviceId, setServiceId] = useState<string>()
  const [day, setDay] = useState<string>(() => new Date().toISOString().slice(0, 10))
  const masterId = useMemo(() => {
    const services = landing.data?.services ?? []
    return services[0]?.master_id
  }, [landing.data?.services])

  const slotsQuery = useQuery({
    queryKey: ['slots', masterId, serviceId, day],
    queryFn: () =>
      availabilityApi({
        master_id: masterId ?? '',
        service_id: serviceId ?? '',
        date: day,
      }),
    enabled: Boolean(masterId && serviceId && clientId && landing.data?.accepted_at),
  })

  const booking = useMutation({
    mutationFn: (start: string) =>
      bookingsCreateApi({
        client_id: clientId ?? '',
        service_id: serviceId ?? '',
        start_at: start,
        invite_token: token,
      }),
  })

  if (landing.isLoading || !landing.data) {
    return <div className="px-6 py-10 pr-14 text-slate-600 dark:text-slate-400">Открываем инвайт…</div>
  }

  const data = landing.data
  const services: Service[] = data.services

  return (
    <div className="mx-auto max-w-4xl space-y-8 px-6 py-10 pr-14">
      <header>
        <p className="text-sm uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Приглашение</p>
        <h1 className="text-3xl font-semibold">{data.master_display_name}</h1>
        <p className="text-slate-600 dark:text-slate-400">
          Часовой пояс мастера: {data.timezone}. Ссылка активна до {new Date(data.expires_at).toLocaleString()}
        </p>
      </header>

      {!data.accepted_at && (
        <form
          className="space-y-3 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
          onSubmit={acceptForm.handleSubmit((vals) =>
            accept.mutate({
              display_name: vals.display_name,
              phone: vals.phone || undefined,
              email: vals.email || undefined,
            }),
          )}
        >
          <h2 className="text-xl font-semibold">Примите инвайт</h2>
          <input
            {...acceptForm.register('display_name', { required: true })}
            placeholder="Как к вам обращаться?"
            className={`w-full ${inputClass}`}
          />
          <div className="grid gap-3 md:grid-cols-2">
            <input {...acceptForm.register('phone')} placeholder="Телефон" className={inputClass} />
            <input {...acceptForm.register('email')} placeholder="Email" className={inputClass} />
          </div>
          <button
            className="rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white dark:bg-emerald-500 dark:text-slate-950"
            type="submit"
          >
            Продолжить
          </button>
        </form>
      )}

      {data.accepted_at && (
        <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-xl font-semibold">Запись</h2>
          <select className={`w-full ${inputClass}`} value={serviceId} onChange={(e) => setServiceId(e.target.value)}>
            <option value="">Выберите услугу</option>
            {services.map((svc) => (
              <option key={svc.id} value={svc.id}>
                {svc.name} · {svc.duration_min} мин
              </option>
            ))}
          </select>

          <input type="date" value={day} onChange={(e) => setDay(e.target.value)} className={inputClass} />

          {!clientId && (
            <p className="text-sm text-rose-600 dark:text-rose-300">
              Клиентская связка не найдена — примите инвайт ещё раз.
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            {(slotsQuery.data ?? []).map((slot) => (
              <button
                type="button"
                key={slot.start_at}
                disabled={booking.isPending}
                className="rounded-md border border-slate-300 px-3 py-1 text-sm dark:border-slate-700"
                onClick={() => booking.mutate(slot.start_at)}
              >
                {new Date(slot.start_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </button>
            ))}
          </div>

          {booking.isSuccess && (
            <p className="text-emerald-700 dark:text-emerald-300">Запись создана — ждём вас!</p>
          )}
        </section>
      )}
    </div>
  )
}
