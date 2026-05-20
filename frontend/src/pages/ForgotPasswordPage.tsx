import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'

import { forgotPasswordApi } from '../api/auth'
import { AuthErrorBanner, AuthFieldLabel, AuthScreen } from '../components/auth/AuthScreen'
import { AUTH_FIELD_CLASS, AUTH_LINK_CLASS, AUTH_PRIMARY_BUTTON_CLASS } from '../components/auth/authStyles'
import { getUserFacingError } from '../lib/apiErrors'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => forgotPasswordApi({ email: email.trim() }),
    onSuccess: () => {
      setError(null)
      setSent(true)
    },
    onError: (err) => setError(getUserFacingError(err)),
  })

  if (sent) {
    return (
      <AuthScreen
        title="Проверьте почту"
        subtitle={
          <>
            Если аккаунт с адресом <strong className="text-stone-900 dark:text-stone-100">{email.trim()}</strong>{' '}
            существует, мы отправили ссылку для сброса пароля.
          </>
        }
        footer={
          <NavLink to="/login" className={AUTH_LINK_CLASS}>
            Вернуться к входу
          </NavLink>
        }
      />
    )
  }

  return (
    <AuthScreen
      title="Забыли пароль?"
      subtitle="Введите email — мы отправим ссылку для сброса пароля."
      footer={
        <NavLink to="/login" className={AUTH_LINK_CLASS}>
          Вернуться к входу
        </NavLink>
      }
    >
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault()
          setError(null)
          mutation.mutate()
        }}
      >
        <label className="flex flex-col">
          <AuthFieldLabel>Email</AuthFieldLabel>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={AUTH_FIELD_CLASS}
            required
          />
        </label>
        {error ? <AuthErrorBanner message={error} /> : null}
        <button disabled={mutation.isPending || !email.trim()} className={AUTH_PRIMARY_BUTTON_CLASS} type="submit">
          {mutation.isPending ? 'Отправляем…' : 'Отправить ссылку'}
        </button>
      </form>
    </AuthScreen>
  )
}
