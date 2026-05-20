import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { NavLink, useSearchParams } from 'react-router-dom'

import { resetPasswordApi } from '../api/auth'
import { AuthErrorBanner, AuthFieldLabel, AuthScreen } from '../components/auth/AuthScreen'
import { AUTH_FIELD_CLASS, AUTH_LINK_CLASS, AUTH_PRIMARY_BUTTON_CLASS } from '../components/auth/authStyles'
import { getUserFacingError } from '../lib/apiErrors'
import { validatePassword } from '../lib/validators'

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const mutation = useMutation({
    mutationFn: () => resetPasswordApi({ token, new_password: password }),
    onSuccess: () => {
      setError(null)
      setDone(true)
    },
    onError: (err) => setError(getUserFacingError(err)),
  })

  if (!token) {
    return (
      <AuthScreen
        title="Ссылка недействительна"
        subtitle="Токен для сброса пароля отсутствует. Запросите сброс заново."
        footer={
          <NavLink to="/forgot-password" className={AUTH_LINK_CLASS}>
            Запросить сброс пароля
          </NavLink>
        }
      />
    )
  }

  if (done) {
    return (
      <AuthScreen
        title="Пароль обновлён"
        subtitle="Теперь вы можете войти с новым паролем."
        footer={
          <NavLink to="/login" className={AUTH_LINK_CLASS}>
            Войти
          </NavLink>
        }
      />
    )
  }

  return (
    <AuthScreen
      title="Новый пароль"
      subtitle="Придумайте новый пароль для вашего аккаунта."
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
          const result = validatePassword(password)
          if (result !== true) {
            setFieldError(result)
            return
          }
          setFieldError(null)
          mutation.mutate()
        }}
      >
        <label className="flex flex-col">
          <AuthFieldLabel>Новый пароль</AuthFieldLabel>
          <input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value)
              setFieldError(null)
            }}
            className={AUTH_FIELD_CLASS}
            required
          />
          {fieldError ? <p className="mt-1 text-sm text-red-800/90 dark:text-red-300/90">{fieldError}</p> : null}
        </label>
        {error ? <AuthErrorBanner message={error} /> : null}
        <button disabled={mutation.isPending || !password} className={AUTH_PRIMARY_BUTTON_CLASS} type="submit">
          {mutation.isPending ? 'Сохраняем…' : 'Сохранить пароль'}
        </button>
      </form>
    </AuthScreen>
  )
}
