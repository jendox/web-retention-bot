import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { NavLink, useNavigate } from 'react-router-dom'

import { loginApi } from '../api/auth'
import { AuthErrorBanner, AuthFieldLabel, AuthScreen } from '../components/auth/AuthScreen'
import { AUTH_FIELD_CLASS, AUTH_LINK_CLASS, AUTH_PRIMARY_BUTTON_CLASS } from '../components/auth/authStyles'
import { getUserFacingError } from '../lib/apiErrors'
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
      navigate('/')
    },
    onError: (err) => {
      form.setError('root', { message: getUserFacingError(err) })
    },
  })

  return (
    <AuthScreen
      title="Вход"
      footer={
        <div className="space-y-2">
          <div>
            Нет аккаунта?{' '}
            <NavLink to="/register" className={AUTH_LINK_CLASS}>
              Регистрация
            </NavLink>
          </div>
          <div>
            <NavLink to="/forgot-password" className={AUTH_LINK_CLASS}>
              Забыли пароль?
            </NavLink>
          </div>
        </div>
      }
    >
      <form className="space-y-4" onSubmit={form.handleSubmit((vals) => mutation.mutate(vals))}>
        <label className="flex flex-col">
          <AuthFieldLabel>Email</AuthFieldLabel>
          <input
            type="email"
            autoComplete="email"
            {...form.register('email')}
            className={AUTH_FIELD_CLASS}
          />
          {form.formState.errors.email && (
            <p className="mt-1 text-sm text-red-800/90 dark:text-red-300/90">{form.formState.errors.email.message}</p>
          )}
        </label>
        <label className="flex flex-col">
          <AuthFieldLabel>Пароль</AuthFieldLabel>
          <input
            type="password"
            autoComplete="current-password"
            {...form.register('password')}
            className={AUTH_FIELD_CLASS}
          />
          {form.formState.errors.password && (
            <p className="mt-1 text-sm text-red-800/90 dark:text-red-300/90">{form.formState.errors.password.message}</p>
          )}
        </label>
        {form.formState.errors.root && <AuthErrorBanner message={form.formState.errors.root.message ?? ''} />}
        <button disabled={mutation.isPending} className={AUTH_PRIMARY_BUTTON_CLASS} type="submit">
          {mutation.isPending ? 'Входим…' : 'Войти'}
        </button>
      </form>
    </AuthScreen>
  )
}
