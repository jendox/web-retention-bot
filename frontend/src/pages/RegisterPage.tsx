import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { NavLink, useNavigate } from 'react-router-dom'

import { registerApi } from '../api/auth'
import { AuthErrorBanner, AuthFieldLabel, AuthScreen } from '../components/auth/AuthScreen'
import { AUTH_FIELD_CLASS, AUTH_LINK_CLASS, AUTH_PRIMARY_BUTTON_CLASS } from '../components/auth/authStyles'
import { getUserFacingError } from '../lib/apiErrors'
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
    onError: (err) => form.setError('root', { message: getUserFacingError(err) }),
  })

  return (
    <AuthScreen
      title="Регистрация"
      subtitle="Создайте аккаунт и укажите отображаемое имя — например, название студии или салона."
      footer={
        <NavLink to="/login" className={AUTH_LINK_CLASS}>
          Уже есть аккаунт — войти
        </NavLink>
      }
    >
      <form className="space-y-4" onSubmit={form.handleSubmit((vals) => mutation.mutate(vals))}>
        <label className="flex flex-col">
          <AuthFieldLabel>Email</AuthFieldLabel>
          <input {...form.register('email')} type="email" autoComplete="email" className={AUTH_FIELD_CLASS} />
          {form.formState.errors.email && (
            <p className="mt-1 text-sm text-red-800/90 dark:text-red-300/90">{form.formState.errors.email.message}</p>
          )}
        </label>
        <label className="flex flex-col">
          <AuthFieldLabel>Пароль</AuthFieldLabel>
          <input
            type="password"
            {...form.register('password')}
            autoComplete="new-password"
            className={AUTH_FIELD_CLASS}
          />
          {form.formState.errors.password && (
            <p className="mt-1 text-sm text-red-800/90 dark:text-red-300/90">{form.formState.errors.password.message}</p>
          )}
        </label>
        <label className="flex flex-col">
          <AuthFieldLabel>Отображаемое имя</AuthFieldLabel>
          <input {...form.register('master_display_name')} autoComplete="organization" className={AUTH_FIELD_CLASS} />
          {form.formState.errors.master_display_name && (
            <p className="mt-1 text-sm text-red-800/90 dark:text-red-300/90">
              {form.formState.errors.master_display_name.message}
            </p>
          )}
        </label>
        {form.formState.errors.root && <AuthErrorBanner message={form.formState.errors.root.message ?? ''} />}
        <button disabled={mutation.isPending} className={AUTH_PRIMARY_BUTTON_CLASS} type="submit">
          {mutation.isPending ? 'Отправляем…' : 'Зарегистрироваться'}
        </button>
      </form>
    </AuthScreen>
  )
}
