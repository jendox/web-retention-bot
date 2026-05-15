import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { NavLink, useNavigate } from 'react-router-dom'

import { loginApi } from '../api/auth'
import { queryClient } from '../lib/query'
import { loginSchema } from '../lib/validators'

type LoginForm = {
  email: string
  password: string
}

export function LoginPage() {
  const navigate = useNavigate()
  const form = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })
  const mutation = useMutation({
    mutationFn: (values: LoginForm) => loginApi(values),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['me'] })
      navigate('/dashboard')
    },
    onError: (err) => {
      form.setError('root', { message: `${err}` })
    },
  })

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-8 px-6 py-14 pr-14">
      <div>
        <h1 className="text-3xl font-semibold">Вход мастера</h1>
        <p className="text-slate-600 dark:text-slate-400">Cookies-сессия. Нужна подтверждённая почта после регистрации.</p>
      </div>
      <form
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
        onSubmit={form.handleSubmit((vals) => mutation.mutate(vals))}
      >
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input
            type="email"
            autoComplete="email"
            {...form.register('email')}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Пароль
          <input
            type="password"
            autoComplete="current-password"
            {...form.register('password')}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
          />
        </label>
        {form.formState.errors.root && (
          <p className="text-sm text-rose-600 dark:text-rose-400">{form.formState.errors.root.message}</p>
        )}
        <button
          disabled={mutation.isPending}
          className="w-full rounded-md bg-emerald-600 px-3 py-2 font-semibold text-white disabled:opacity-50 dark:bg-emerald-500 dark:text-slate-950"
          type="submit"
        >
          Войти
        </button>
      </form>
      <div className="text-sm text-slate-600 dark:text-slate-400">
        Нет аккаунта?{' '}
        <NavLink to="/register" className="font-medium text-emerald-600 dark:text-emerald-400">
          Регистрация
        </NavLink>
      </div>
    </div>
  )
}
