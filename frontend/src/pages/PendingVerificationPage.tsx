import { NavLink, useLocation } from 'react-router-dom'

type LocationState = { email?: string }

export function PendingVerificationPage() {
  const state = useLocation().state as LocationState | undefined
  const email = state?.email

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-8 px-6 py-14 pr-14">
      <div>
        <h1 className="text-3xl font-semibold">Проверьте почту</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">
          Мы создали учётную запись. Перейдите по ссылке из письма, чтобы активировать аккаунт и войти. В режиме
          разработки ссылка дублируется в{' '}
          <span className="font-medium text-slate-800 dark:text-slate-300">лог сервера</span>.
        </p>
      </div>
      {email && (
        <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
          Отправили на адрес{' '}
          <span className="font-semibold text-emerald-700 dark:text-emerald-300">{email}</span>
        </p>
      )}
      <NavLink className="text-sm font-medium text-emerald-600 dark:text-emerald-400" to="/login">
        На страницу входа
      </NavLink>
    </div>
  )
}
