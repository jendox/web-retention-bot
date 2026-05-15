import { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate, useSearchParams } from 'react-router-dom'

import { verifyEmailApi } from '../api/auth'
import { AuthErrorBanner, AuthScreen } from '../components/auth/AuthScreen'
import { AUTH_LINK_CLASS } from '../components/auth/authStyles'
import { getUserFacingError } from '../lib/apiErrors'
import { queryClient } from '../lib/query'

export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token')
  const [error, setError] = useState<string | null>(null)
  const started = useRef(false)

  useEffect(() => {
    if (!token || started.current) {
      return
    }
    started.current = true
    const run = async () => {
      try {
        await verifyEmailApi({ token: decodeURIComponent(token) })
        await queryClient.invalidateQueries({ queryKey: ['me'] })
        navigate('/dashboard')
      } catch (err) {
        setError(getUserFacingError(err))
      }
    }
    void run()
  }, [token, navigate])

  if (!token) {
    return (
      <AuthScreen
        title="Некорректная ссылка"
        subtitle="В адресе страницы нет параметра подтверждения. Откройте ссылку из письма целиком."
        footer={
          <NavLink className={AUTH_LINK_CLASS} to="/login">
            На страницу входа
          </NavLink>
        }
      >
        <p className="text-center text-sm text-slate-600 dark:text-slate-400">Обратитесь в поддержку, если проблема повторяется.</p>
      </AuthScreen>
    )
  }

  if (error) {
    return (
      <AuthScreen
        title="Не удалось подтвердить email"
        subtitle="Запросите новую ссылку или войдите, если аккаунт уже активирован."
        footer={
          <NavLink className={AUTH_LINK_CLASS} to="/login">
            На страницу входа
          </NavLink>
        }
      >
        <AuthErrorBanner message={error} />
      </AuthScreen>
    )
  }

  return (
    <AuthScreen title="Подтверждаем email" subtitle="Секунду, выполняем вход…">
      <p className="text-center text-sm text-slate-600 dark:text-slate-400">Пожалуйста, не закрывайте вкладку.</p>
    </AuthScreen>
  )
}
