import { NavLink } from 'react-router-dom'

import { AUTH_LINK_CLASS } from '../components/auth/authStyles'

export function MyVisitsAsClientPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Мои визиты</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-stone-600 dark:text-stone-400">
          Здесь будут отображаться ваши записи к <strong className="font-medium text-stone-800 dark:text-stone-200">другим</strong>{' '}
          мастерам — например, если вы приняли приглашение и записались не как владелец студии. Тот же логин и пароль,
          другой сценарий: вы не управляете чужим расписанием, только свои визиты.
        </p>
      </div>
      <div className="rounded-xl border border-dashed border-stone-300 bg-white/80 p-6 dark:border-stone-600 dark:bg-stone-900/60">
        <p className="text-sm text-stone-600 dark:text-stone-400">
          Бэкенд для списка «визитов клиента» ещё не подключён: понадобятся привязка пользователя к клиентским
          профилям и отдельный API. Когда появится — этот экран заменит заглушку без смены идеи навигации.
        </p>
        <p className="mt-4 text-sm">
          <NavLink to="/dashboard" className={AUTH_LINK_CLASS}>
            ← Вернуться к обзору мастера
          </NavLink>
        </p>
      </div>
    </div>
  )
}
