import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useParams } from 'react-router-dom'

import { availabilityApi } from '../api/availability'
import { bookingsCreateApi } from '../api/bookings'
import { loginApi, meApi, registerClientApi } from '../api/auth'
import { invitationAcceptApi, invitationGetApi } from '../api/invitations'
import type { Service } from '../api/services'
import { getUserFacingError } from '../lib/apiErrors'

const storageKey = (t: string) => `inviteClient:${t}`
const POST_VERIFY_KEY = 'invite_post_verify_return'

const inputClass =
  'rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950'

export function InvitationPage() {
  const { token = '' } = useParams()
  const queryClient = useQueryClient()
  const [stagingClientId, setStagingClientId] = useState<string | null>(null)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register')
  const [registeredNotice, setRegisteredNotice] = useState(false)
  const [postAcceptMismatch, setPostAcceptMismatch] = useState(false)

  const landing = useQuery({
    queryKey: ['invite', token],
    queryFn: () => invitationGetApi(token),
    enabled: Boolean(token),
    retry: false,
  })

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })

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

  const acceptForm = useForm({ defaultValues: { display_name: '', phone: '' } })
  const registerForm = useForm({ defaultValues: { email: '', password: '' } })
  const loginForm = useForm({ defaultValues: { email: '', password: '' } })

  const accept = useMutation({
    mutationFn: (body: { display_name: string; phone?: string | null }) => invitationAcceptApi(token, body),
    onSuccess: async (payload) => {
      setPostAcceptMismatch(payload.email_mismatch_with_master_record)
      localStorage.setItem(storageKey(token), payload.client_id)
      setStagingClientId(payload.client_id)
      await landing.refetch()
      await queryClient.invalidateQueries({ queryKey: ['me'] })
      await queryClient.invalidateQueries({ queryKey: ['clients', 'me', 'masters'] })
      setStagingClientId(null)
    },
  })

  const registerMut = useMutation({
    mutationFn: registerClientApi,
    onSuccess: () => {
      setRegisteredNotice(true)
    },
  })

  const loginMut = useMutation({
    mutationFn: loginApi,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })

  useEffect(() => {
    if (token && typeof window !== 'undefined') {
      sessionStorage.setItem('last_invite_url', `${window.location.origin}/invite/${token}`)
    }
  }, [token])

  useEffect(() => {
    if (!landing.data?.accepted_at) {
      return
    }
    const cid = landing.data.linked_client_id
    if (cid && typeof window !== 'undefined') {
      localStorage.setItem(storageKey(token), cid)
    }
  }, [landing.data?.accepted_at, landing.data?.linked_client_id, token])

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
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['bookings', 'me'] })
    },
  })

  if (!token) {
    return <div className="px-6 py-10 text-slate-600 dark:text-slate-400">Некорректная ссылка.</div>
  }

  if (landing.isLoading) {
    return <div className="px-6 py-10 pr-14 text-slate-600 dark:text-slate-400">Открываем инвайт…</div>
  }

  if (landing.isError) {
    return (
      <div className="mx-auto max-w-lg px-6 py-10 pr-14">
        <p className="text-rose-700 dark:text-rose-300">{getUserFacingError(landing.error)}</p>
        <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">
          Попросите у мастера новую ссылку, если приглашение отозвали или срок истёк.
        </p>
      </div>
    )
  }

  const data = landing.data
  const services: Service[] = data.services

  const loggedInVerified = me.isSuccess && me.data?.email_verified === true

  return (
    <div className="mx-auto max-w-4xl space-y-8 px-6 py-10 pr-14">
      <header>
        <p className="text-sm uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Приглашение</p>
        <h1 className="text-3xl font-semibold">{data.master_display_name}</h1>
        <p className="text-slate-600 dark:text-slate-400">
          Часовой пояс мастера: {data.timezone}. Ссылка активна до {new Date(data.expires_at).toLocaleString('ru-RU')}
        </p>
      </header>

      {!data.accepted_at && data.invite_kind === 'client' && data.master_record_has_email ? (
        <div
          className="rounded-xl border border-amber-200/90 bg-amber-50/90 p-4 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/35 dark:text-amber-100"
          role="status"
        >
          <p className="font-medium">Обратите внимание</p>
          <p className="mt-1 text-amber-900/90 dark:text-amber-200">
            В карточке у мастера уже указан email. Если вы войдёте с <span className="font-medium">другим</span> адресом,
            мастер увидит напоминание обновить контакт — иначе уведомления могут уходить не на тот ящик.
          </p>
        </div>
      ) : null}

      {!data.accepted_at && !loggedInVerified ? (
        <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-xl font-semibold">Вход или регистрация</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Чтобы принять приглашение, войдите в существующий аккаунт или создайте новый и подтвердите email.
          </p>

          {me.isSuccess && me.data && !me.data.email_verified ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm dark:border-slate-700 dark:bg-slate-950/50">
              <p className="font-medium text-slate-900 dark:text-slate-100">Подтвердите email</p>
              <p className="mt-1 text-slate-600 dark:text-slate-400">
                Мы отправили письмо на {me.data.email}. После подтверждения откройте эту страницу снова — вы будете
                авторизованы автоматически.
              </p>
              <Link
                to="/login"
                className="mt-3 inline-block text-sm font-medium text-emerald-700 underline hover:text-emerald-600 dark:text-emerald-400"
              >
                Уже подтвердили? Войти
              </Link>
            </div>
          ) : null}

          {registeredNotice ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-100">
              <p className="font-medium">Проверьте почту</p>
              <p className="mt-1">
                Перейдите по ссылке из письма, затем эта страница откроется снова и вы сможете завершить приглашение.
              </p>
            </div>
          ) : null}

          <div className="flex gap-2 border-b border-slate-200 pb-2 dark:border-slate-700">
            <button
              type="button"
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                authMode === 'register'
                  ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
              }`}
              onClick={() => setAuthMode('register')}
            >
              Регистрация
            </button>
            <button
              type="button"
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                authMode === 'login'
                  ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
              }`}
              onClick={() => setAuthMode('login')}
            >
              Вход
            </button>
          </div>

          {authMode === 'register' ? (
            <form
              className="space-y-3"
              onSubmit={registerForm.handleSubmit((vals) => {
                if (typeof window !== 'undefined') {
                  sessionStorage.setItem(POST_VERIFY_KEY, `/invite/${token}`)
                }
                registerMut.mutate({
                  email: vals.email.trim(),
                  password: vals.password,
                })
              })}
            >
              <input
                {...registerForm.register('email', { required: true })}
                type="email"
                autoComplete="email"
                placeholder="Email"
                className={`w-full ${inputClass}`}
              />
              <input
                {...registerForm.register('password', { required: true, minLength: 8 })}
                type="password"
                autoComplete="new-password"
                placeholder="Пароль (мин. 8 символов, буква и цифра)"
                className={`w-full ${inputClass}`}
              />
              {registerMut.isError ? (
                <p className="text-sm text-rose-600 dark:text-rose-300">{getUserFacingError(registerMut.error)}</p>
              ) : null}
              <button
                className="rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white dark:bg-emerald-500 dark:text-slate-950"
                type="submit"
                disabled={registerMut.isPending}
              >
                {registerMut.isPending ? 'Отправка…' : 'Зарегистрироваться'}
              </button>
            </form>
          ) : (
            <form
              className="space-y-3"
              onSubmit={loginForm.handleSubmit((vals) => {
                loginMut.mutate({
                  email: vals.email.trim(),
                  password: vals.password,
                })
              })}
            >
              <input
                {...loginForm.register('email', { required: true })}
                type="email"
                autoComplete="email"
                placeholder="Email"
                className={`w-full ${inputClass}`}
              />
              <input
                {...loginForm.register('password', { required: true })}
                type="password"
                autoComplete="current-password"
                placeholder="Пароль"
                className={`w-full ${inputClass}`}
              />
              {loginMut.isError ? (
                <p className="text-sm text-rose-600 dark:text-rose-300">{getUserFacingError(loginMut.error)}</p>
              ) : null}
              <button
                className="rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white dark:bg-emerald-500 dark:text-slate-950"
                type="submit"
                disabled={loginMut.isPending}
              >
                {loginMut.isPending ? 'Вход…' : 'Войти'}
              </button>
            </form>
          )}
        </div>
      ) : null}

      {!data.accepted_at && loggedInVerified ? (
        <form
          className="space-y-3 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
          onSubmit={acceptForm.handleSubmit((vals) =>
            accept.mutate({
              display_name: vals.display_name.trim(),
              phone: vals.phone?.trim() || null,
            }),
          )}
        >
          <h2 className="text-xl font-semibold">Завершите приглашение</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">Вы вошли как {me.data?.email}.</p>
          <input
            {...acceptForm.register('display_name', { required: true })}
            placeholder="Как к вам обращаться?"
            className={`w-full ${inputClass}`}
          />
          <input {...acceptForm.register('phone')} placeholder="Телефон (необязательно)" className={`w-full ${inputClass}`} />
          {accept.isError ? (
            <p className="text-sm text-rose-600 dark:text-rose-300">{getUserFacingError(accept.error)}</p>
          ) : null}
          <button
            className="rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white dark:bg-emerald-500 dark:text-slate-950"
            type="submit"
            disabled={accept.isPending}
          >
            {accept.isPending ? 'Сохранение…' : 'Принять приглашение'}
          </button>
        </form>
      ) : null}

      {data.accepted_at && postAcceptMismatch ? (
        <div
          className="rounded-xl border border-amber-200/90 bg-amber-50/90 p-4 text-sm dark:border-amber-900/50 dark:bg-amber-950/35 dark:text-amber-100"
          role="status"
        >
          <p className="font-medium">Email не совпадал с карточкой у мастера</p>
          <p className="mt-1 text-amber-900/90 dark:text-amber-200">
            Мы сохранили контакт в карточке как у мастера; вы вошли как {me.data?.email}. Мастер получил напоминание
            проверить email, чтобы уведомления доходили до вас.
          </p>
        </div>
      ) : null}

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
