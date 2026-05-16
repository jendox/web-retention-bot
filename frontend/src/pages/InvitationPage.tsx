import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useNavigate, useParams } from 'react-router-dom'

import { loginApi, meApi, registerClientApi } from '../api/auth'
import { invitationAcceptApi, invitationGetApi } from '../api/invitations'
import { getUserFacingError } from '../lib/apiErrors'
import { validatePassword } from '../lib/validators'

const POST_VERIFY_KEY = 'invite_post_verify_return'

const inputClass =
  'rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950'

const stepBaseClass = 'rounded-md border px-3 py-2 transition'
const stepCurrentClass =
  'border-emerald-500 bg-emerald-50 text-emerald-950 shadow-sm ring-1 ring-emerald-200 dark:border-emerald-500 dark:bg-emerald-950/30 dark:text-emerald-50 dark:ring-emerald-900'
const stepDoneClass =
  'border-emerald-200 bg-white text-slate-600 dark:border-emerald-900/50 dark:bg-slate-900 dark:text-slate-400'
const stepUpcomingClass =
  'border-slate-200 bg-white text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500'
const stepTitleBaseClass = 'font-medium'

type AcceptFormValues = {
  display_name: string
  phone: string
}

type AuthFormValues = {
  email: string
  password: string
}

function stepClass(state: 'current' | 'done' | 'upcoming') {
  const stateClass = state === 'current' ? stepCurrentClass : state === 'done' ? stepDoneClass : stepUpcomingClass
  return `${stepBaseClass} ${stateClass}`
}

function stepTitleClass(state: 'current' | 'done' | 'upcoming') {
  if (state === 'current') {
    return `${stepTitleBaseClass} text-emerald-900 dark:text-emerald-100`
  }
  if (state === 'done') {
    return `${stepTitleBaseClass} text-slate-900 dark:text-slate-100`
  }
  return `${stepTitleBaseClass} text-slate-500 dark:text-slate-500`
}

export function InvitationPage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register')
  const [registeredNotice, setRegisteredNotice] = useState(false)
  const [postAcceptMismatch, setPostAcceptMismatch] = useState(false)
  const [acceptedClientId, setAcceptedClientId] = useState<string | null>(null)

  const landing = useQuery({
    queryKey: ['invite', token],
    queryFn: () => invitationGetApi(token),
    enabled: Boolean(token),
    retry: false,
  })

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })

  const acceptForm = useForm<AcceptFormValues>({ defaultValues: { display_name: '', phone: '' }, mode: 'onTouched' })
  const registerForm = useForm<AuthFormValues>({ defaultValues: { email: '', password: '' }, mode: 'onTouched' })
  const loginForm = useForm<AuthFormValues>({ defaultValues: { email: '', password: '' }, mode: 'onTouched' })

  const accept = useMutation({
    mutationFn: (body: { display_name: string; phone?: string | null }) => invitationAcceptApi(token, body),
    onSuccess: async (payload) => {
      setPostAcceptMismatch(payload.email_mismatch_with_master_record)
      setAcceptedClientId(payload.client_id)
      await Promise.all([
        landing.refetch(),
        queryClient.invalidateQueries({ queryKey: ['me'] }),
        queryClient.invalidateQueries({ queryKey: ['clients', 'me', 'masters'] }),
        queryClient.invalidateQueries({ queryKey: ['bookings', 'me'] }),
      ])
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
      setRegisteredNotice(false)
      await queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })

  useEffect(() => {
    if (token && typeof window !== 'undefined') {
      const inviteUrl = `${window.location.origin}/invite/${token}`
      sessionStorage.setItem('last_invite_url', inviteUrl)
      localStorage.setItem('last_invite_url', inviteUrl)
    }
  }, [token])

  useEffect(() => {
    if (!token || typeof window === 'undefined') {
      return
    }
    const returnPath = `/invite/${token}`
    sessionStorage.setItem(POST_VERIFY_KEY, returnPath)
    localStorage.setItem(POST_VERIFY_KEY, returnPath)
  }, [token])

  useEffect(() => {
    if (!me.data?.email_verified || acceptForm.getValues('display_name')) {
      return
    }
    const fallbackName = me.data.email.split('@')[0]?.trim()
    if (fallbackName) {
      acceptForm.setValue('display_name', fallbackName)
    }
  }, [acceptForm, me.data?.email, me.data?.email_verified])

  useEffect(() => {
    if (!acceptedClientId) {
      return
    }
    const timer = window.setTimeout(() => navigate('/client'), 1800)
    return () => window.clearTimeout(timer)
  }, [acceptedClientId, navigate])

  if (!token) {
    return <div className="px-6 py-10 text-slate-600 dark:text-slate-400">Некорректная ссылка.</div>
  }

  if (landing.isLoading) {
    return <div className="px-6 py-10 pr-14 text-slate-600 dark:text-slate-400">Открываем приглашение...</div>
  }

  if (landing.isError) {
    return (
      <div className="mx-auto max-w-lg px-6 py-10 pr-14">
        <p className="text-rose-700 dark:text-rose-300">{getUserFacingError(landing.error)}</p>
        <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">
          Попросите у мастера новую ссылку, если приглашение отозвали или срок истек.
        </p>
      </div>
    )
  }

  const data = landing.data
  if (!data) {
    return null
  }

  const loggedInVerified = me.isSuccess && me.data?.email_verified === true
  const loggedInUnverified = me.isSuccess && me.data && !me.data.email_verified
  const accepted = Boolean(data.accepted_at || acceptedClientId)
  const linkedClientId = data.linked_client_id ?? acceptedClientId
  const masterInitial = data.master_display_name.trim().charAt(0).toUpperCase() || 'M'
  const currentStep = accepted ? 4 : loggedInVerified ? 3 : registeredNotice || loggedInUnverified ? 2 : 1
  const firstStepState = currentStep === 1 ? 'current' : 'done'
  const secondStepState = currentStep === 2 ? 'current' : currentStep > 2 ? 'done' : 'upcoming'
  const thirdStepState = currentStep === 3 ? 'current' : currentStep > 3 ? 'done' : 'upcoming'

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-8 pr-14 sm:py-12">
      <header className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="border-b border-slate-100 bg-emerald-50/80 px-6 py-5 dark:border-slate-800 dark:bg-emerald-950/20">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-2xl font-semibold text-white dark:bg-emerald-500 dark:text-slate-950">
              {masterInitial}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-emerald-800 dark:text-emerald-200">Личный кабинет клиента</p>
              <h1 className="text-2xl font-semibold text-slate-950 dark:text-slate-50">
                Вас пригласил {data.master_display_name}
              </h1>
            </div>
          </div>
        </div>
        <div className="space-y-4 px-6 py-5">
          <p className="max-w-2xl text-base text-slate-700 dark:text-slate-300">
            Войдите или создайте аккаунт, чтобы принять приглашение
          </p>
          <div className="grid gap-3 text-sm sm:grid-cols-3">
            <div className={stepClass(firstStepState)}>
              <p className={stepTitleClass(firstStepState)}>1. Войдите</p>
              <p className="mt-0.5">или создайте аккаунт</p>
            </div>
            <div className={stepClass(secondStepState)}>
              <p className={stepTitleClass(secondStepState)}>2. Подтвердите email</p>
              <p className="mt-0.5">если аккаунт новый</p>
            </div>
            <div className={stepClass(thirdStepState)}>
              <p className={stepTitleClass(thirdStepState)}>3. Примите приглашение</p>
              <p className="mt-0.5">мастер появится в кабинете</p>
            </div>
          </div>
        </div>
      </header>

      {!accepted && !loggedInVerified ? (
        <section className="space-y-6 rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold text-slate-950 dark:text-slate-50">
              {loggedInUnverified ? 'Подтвердите email' : 'Войдите или создайте аккаунт'}
            </h2>
            {loggedInUnverified ? (
              <p className="text-sm text-slate-600 dark:text-slate-400">
                После подтверждения email вы вернетесь сюда и сможете принять приглашение.
              </p>
            ) : null}
          </div>

          {loggedInUnverified ? (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-4 text-sm dark:border-slate-700 dark:bg-slate-950/50">
              <p className="font-medium text-slate-900 dark:text-slate-100">Письмо отправлено на {me.data.email}</p>
              <p className="mt-1 text-slate-600 dark:text-slate-400">
                Откройте ссылку из письма. После подтверждения останется один шаг: принять приглашение.
              </p>
            </div>
          ) : null}

          {registeredNotice ? (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-100">
              <p className="font-medium">Проверьте почту</p>
              <p className="mt-1">
                Перейдите по ссылке из письма. Мы вернем вас сюда, чтобы завершить приглашение.
              </p>
            </div>
          ) : null}

          {!loggedInUnverified ? (
            <>
              <div className="flex gap-2 border-b border-slate-200 pb-2 dark:border-slate-700">
                <button
                  type="button"
                  className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                    authMode === 'register'
                      ? 'bg-emerald-600 text-white dark:bg-emerald-500 dark:text-slate-950'
                      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
                  }`}
                  onClick={() => setAuthMode('register')}
                >
                  Создать аккаунт
                </button>
                <button
                  type="button"
                  className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                    authMode === 'login'
                      ? 'bg-emerald-600 text-white dark:bg-emerald-500 dark:text-slate-950'
                      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
                  }`}
                  onClick={() => setAuthMode('login')}
                >
                  Войти
                </button>
              </div>

              {authMode === 'register' ? (
                <form
                  className="space-y-3"
                  onSubmit={registerForm.handleSubmit((vals) => {
                    if (typeof window !== 'undefined') {
                      const returnPath = `/invite/${token}`
                      sessionStorage.setItem(POST_VERIFY_KEY, returnPath)
                      localStorage.setItem(POST_VERIFY_KEY, returnPath)
                    }
                    registerMut.mutate({
                      email: vals.email.trim(),
                      password: vals.password,
                    })
                  })}
                >
                  <input
                    {...registerForm.register('email', { required: 'Введите email' })}
                    type="email"
                    autoComplete="email"
                    placeholder="Email"
                    className={`w-full ${inputClass}`}
                  />
                  {registerForm.formState.errors.email ? (
                    <p className="text-sm text-rose-600 dark:text-rose-300">
                      {registerForm.formState.errors.email.message}
                    </p>
                  ) : null}
                  <input
                    {...registerForm.register('password', {
                      validate: validatePassword,
                    })}
                    type="password"
                    autoComplete="new-password"
                    placeholder="Пароль: минимум 8 символов, буква и цифра"
                    className={`w-full ${inputClass}`}
                  />
                  {registerForm.formState.errors.password ? (
                    <p className="text-sm text-rose-600 dark:text-rose-300">
                      {registerForm.formState.errors.password.message}
                    </p>
                  ) : null}
                  {registerMut.isError ? (
                    <p className="text-sm text-rose-600 dark:text-rose-300">{getUserFacingError(registerMut.error)}</p>
                  ) : null}
                  <button
                    className="rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white disabled:opacity-60 dark:bg-emerald-500 dark:text-slate-950"
                    type="submit"
                    disabled={registerMut.isPending}
                  >
                    {registerMut.isPending ? 'Отправка...' : 'Создать аккаунт'}
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
                    {...loginForm.register('email', { required: 'Введите email' })}
                    type="email"
                    autoComplete="email"
                    placeholder="Email"
                    className={`w-full ${inputClass}`}
                  />
                  {loginForm.formState.errors.email ? (
                    <p className="text-sm text-rose-600 dark:text-rose-300">{loginForm.formState.errors.email.message}</p>
                  ) : null}
                  <input
                    {...loginForm.register('password', { required: 'Введите пароль' })}
                    type="password"
                    autoComplete="current-password"
                    placeholder="Пароль"
                    className={`w-full ${inputClass}`}
                  />
                  {loginForm.formState.errors.password ? (
                    <p className="text-sm text-rose-600 dark:text-rose-300">
                      {loginForm.formState.errors.password.message}
                    </p>
                  ) : null}
                  {loginMut.isError ? (
                    <p className="text-sm text-rose-600 dark:text-rose-300">{getUserFacingError(loginMut.error)}</p>
                  ) : null}
                  <button
                    className="rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white disabled:opacity-60 dark:bg-emerald-500 dark:text-slate-950"
                    type="submit"
                    disabled={loginMut.isPending}
                  >
                    {loginMut.isPending ? 'Вход...' : 'Войти'}
                  </button>
                </form>
              )}
            </>
          ) : null}
        </section>
      ) : null}

      {!accepted && loggedInVerified ? (
        <form
          className="space-y-4 rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
          onSubmit={acceptForm.handleSubmit((vals) =>
            accept.mutate({
              display_name: vals.display_name.trim(),
              phone: vals.phone?.trim() || null,
            }),
          )}
        >
          <div className="space-y-1">
            <h2 className="text-xl font-semibold text-slate-950 dark:text-slate-50">Остался последний шаг</h2>
          </div>

          <label className="block space-y-1">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Как к вам обращаться?</span>
            <input
              {...acceptForm.register('display_name', { required: true })}
              autoComplete="name"
              className={`w-full ${inputClass}`}
            />
          </label>
          <label className="block space-y-1">
            <span className="flex items-baseline gap-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Телефон</span>
              <span className="text-xs text-slate-400 dark:text-slate-500">необязательно</span>
            </span>
            <input {...acceptForm.register('phone')} autoComplete="tel" className={`w-full ${inputClass}`} />
          </label>
          {accept.isError ? (
            <p className="text-sm text-rose-600 dark:text-rose-300">{getUserFacingError(accept.error)}</p>
          ) : null}
          <button
            className="rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white disabled:opacity-60 dark:bg-emerald-500 dark:text-slate-950"
            type="submit"
            disabled={accept.isPending}
          >
            {accept.isPending ? 'Принимаем...' : 'Принять приглашение'}
          </button>
        </form>
      ) : null}

      {accepted ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-sm">
          <div
            className="w-full max-w-sm rounded-lg border border-emerald-200 bg-white p-6 text-center shadow-xl dark:border-emerald-900/50 dark:bg-slate-900"
            role="dialog"
            aria-modal="true"
          >
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-2xl text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
              ✓
            </div>
            <h2 className="mt-4 text-xl font-semibold text-slate-950 dark:text-slate-50">Приглашение принято</h2>
            {postAcceptMismatch ? (
              <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">
                Email отличается от карточки мастера. Мы сохранили приглашение.
              </p>
            ) : null}
            {!linkedClientId ? (
              <p className="mt-3 text-xs text-rose-700 dark:text-rose-300">
                Если мастер не появится в кабинете, обновите страницу.
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}
