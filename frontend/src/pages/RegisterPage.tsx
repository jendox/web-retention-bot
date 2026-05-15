import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { NavLink, useNavigate } from 'react-router-dom'

import { registerApi } from '../api/auth'
import { registerSchema } from '../lib/validators'

type RegisterForm = {
  email: string
  password: string
  master_display_name: string
}

export function RegisterPage() {
  const navigate = useNavigate()
  const form = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) })

  const mutation = useMutation({
    mutationFn: (values: RegisterForm) =>
      registerApi({
        email: values.email.trim(),
        password: values.password,
        master_display_name: values.master_display_name.trim(),
      }),
    onSuccess: async (data) => {
      navigate('/pending-verification', { state: { email: data.email } })
    },
    onError: (err) => form.setError('root', { message: `${err}` }),
  })

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-8 px-6 py-14 pr-14">
      <div>
        <h1 className="text-3xl font-semibold">Регистрация мастера</h1>
        <p className="text-slate-600 dark:text-slate-400">
          Ссылка подтверждения отправляется на email (пока см. логи сервера).
        </p>
      </div>

      <form
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
        onSubmit={form.handleSubmit((vals) => mutation.mutate(vals))}
      >
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input
            {...form.register('email')}
            type="email"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Пароль
          <input
            type="password"
            {...form.register('password')}
            autoComplete="new-password"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Отображаемое имя
          <input
            {...form.register('master_display_name')}
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
          Зарегистрироваться
        </button>
      </form>
      <NavLink className="text-sm font-medium text-emerald-600 dark:text-emerald-400" to="/login">
        Уже есть аккаунт
      </NavLink>
    </div>
  )
}
