import { NavLink, useLocation } from 'react-router-dom'

import { AuthScreen } from '../components/auth/AuthScreen'
import { AUTH_LINK_CLASS } from '../components/auth/authStyles'

type LocationState = { email?: string }

export function PendingVerificationPage() {
  const state = useLocation().state as LocationState | undefined
  const email = state?.email

  return (
    <AuthScreen
      title="Проверьте почту"
      subtitle={
        email ? (
          <>
            Мы отправили письмо со ссылкой для подтверждения на{' '}
            <span className="font-semibold text-stone-800 dark:text-stone-200">{email}</span>. Перейдите по ссылке из
            письма, чтобы активировать аккаунт и войти в систему. Если письма нет — загляните в папку «Спам».
          </>
        ) : (
          'Мы отправили письмо со ссылкой для подтверждения. Перейдите по ссылке из письма, чтобы активировать аккаунт и войти в систему. Если письма нет — загляните в папку «Спам».'
        )
      }
      footer={
        <NavLink className={AUTH_LINK_CLASS} to="/login">
          На страницу входа
        </NavLink>
      }
    />
  )
}
