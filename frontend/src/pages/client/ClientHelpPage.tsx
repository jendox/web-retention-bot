export function ClientHelpPage() {
  return (
    <section className="space-y-6 rounded-xl border border-stone-300 bg-white p-6 shadow-[0_1px_3px_0_rgba(28,25,23,0.08),0_4px_12px_-2px_rgba(28,25,23,0.06)] dark:shadow-sm dark:border-stone-700 dark:bg-stone-900/80">
      <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Как это работает</h1>
      <ol className="list-decimal space-y-4 pl-5 text-sm text-stone-600 dark:text-stone-400">
        <li>
          <span className="font-medium text-stone-800 dark:text-stone-200">Приглашение.</span> Мастер отправляет ссылку —
          вы принимаете её и связываете аккаунт с его студией.
        </li>
        <li>
          <span className="font-medium text-stone-800 dark:text-stone-200">Запись.</span> В демо-режиме можно оформить визит в
          разделе «Мои мастера» или через быстрое действие на обзоре; в продакшене слоты проверяются по расписанию мастера.
        </li>
        <li>
          <span className="font-medium text-stone-800 dark:text-stone-200">Напоминания.</span> Письма на email и лента в разделе
          «Уведомления» в меню слева.
        </li>
        <li>
          <span className="font-medium text-stone-800 dark:text-stone-200">Изменения.</span> Предстоящие записи можно перенести
          или отменить в разделе «Записи»; отменённые попадают в «Прошедшие».
        </li>
      </ol>
      <p className="text-xs text-stone-500 dark:text-stone-400">
        Тот же логин может открывать кабинет мастера — переключатель находится в меню, когда доступны оба режима.
      </p>
    </section>
  )
}
