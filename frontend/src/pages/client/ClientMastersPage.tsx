import { useMemo, useState } from 'react'

import { useClientCabinet } from '../../components/client/ClientCabinetContext'
import { cn } from '../../lib/forms'
import type { ClientMasterView } from '../../mocks/clientCabinetMocks'

function IconSearch(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35m1.35-5.15a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z" />
    </svg>
  )
}

function masterInitials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ''}${parts[1][0] ?? ''}`.toUpperCase()
  }
  return name.trim().slice(0, 2).toUpperCase() || '?'
}

function MasterCard({
  master,
  onBook,
}: {
  master: ClientMasterView
  onBook: () => void
}) {
  return (
    <li className="flex flex-col rounded-xl border border-stone-200/90 bg-white p-5 shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
      <div className="flex items-start gap-3">
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-teal-100 text-sm font-semibold text-teal-800 dark:bg-teal-950/60 dark:text-teal-200"
          aria-hidden
        >
          {masterInitials(master.display_name)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="font-semibold text-stone-900 dark:text-stone-50">{master.display_name}</p>
              {master.public_slug ? (
                <p className="text-xs text-stone-500 dark:text-stone-400">@{master.public_slug}</p>
              ) : null}
            </div>
            <span className="shrink-0 rounded-full bg-teal-50 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-teal-800 dark:bg-teal-950/50 dark:text-teal-300">
              активна
            </span>
          </div>
          {master.alias ? (
            <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">У мастера вы: {master.alias}</p>
          ) : null}
        </div>
      </div>

      <p className="mt-3 text-sm text-stone-600 dark:text-stone-400">
        Email:{' '}
        <a
          href={`mailto:${master.contact_email}`}
          className="font-medium text-teal-800 hover:underline dark:text-teal-300"
        >
          {master.contact_email}
        </a>
      </p>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={onBook}
          className="flex-1 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-500 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400"
        >
          Записаться
        </button>
        <button
          type="button"
          disabled
          className="rounded-lg border border-stone-200 px-4 py-2.5 text-sm font-medium text-stone-400 dark:border-stone-600 sm:flex-initial"
          title="Скоро"
        >
          Написать
        </button>
      </div>
    </li>
  )
}

export function ClientMastersPage() {
  const { masters, overviewLoading, openBookingModal } = useClientCabinet()
  const [masterSearch, setMasterSearch] = useState('')

  const filteredMasters = useMemo(() => {
    const q = masterSearch.trim().toLowerCase()
    if (!q) {
      return masters
    }
    return masters.filter(
      (m) =>
        m.display_name.toLowerCase().includes(q) ||
        (m.alias?.toLowerCase().includes(q) ?? false) ||
        m.contact_email.toLowerCase().includes(q),
    )
  }, [masters, masterSearch])

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Мои мастера</h1>
          <p className="mt-1 max-w-2xl text-sm text-stone-600 dark:text-stone-400">
            Студии и специалисты, с которыми вы связаны. Здесь можно записаться на визит или написать мастеру по email.
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:max-w-md">
          <label className="relative block">
            <span className="sr-only">Поиск по имени мастера</span>
            <IconSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
            <input
              value={masterSearch}
              onChange={(e) => setMasterSearch(e.target.value)}
              placeholder="Поиск по имени, email или alias"
              className={cn(
                'w-full rounded-lg border border-stone-200 bg-white py-2.5 pl-10 text-sm text-stone-900 shadow-sm outline-none',
                'focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20',
                'dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100',
                masterSearch ? 'pr-10' : 'pr-3',
              )}
            />
            {masterSearch ? (
              <button
                type="button"
                onClick={() => setMasterSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-stone-400 hover:bg-stone-100 hover:text-stone-600 dark:hover:bg-stone-800 dark:hover:text-stone-200"
                aria-label="Очистить поиск"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            ) : null}
          </label>
        </div>
      </header>

      {overviewLoading ? (
        <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем…</p>
      ) : filteredMasters.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/60 px-6 py-14 text-center dark:border-stone-600 dark:bg-stone-900/40">
          <p className="font-medium text-stone-800 dark:text-stone-200">
            {masters.length === 0 ? 'Пока нет привязанных мастеров' : 'Ничего не найдено'}
          </p>
          <p className="mx-auto mt-2 max-w-md text-sm text-stone-500 dark:text-stone-400">
            {masters.length === 0
              ? 'Примите приглашение по ссылке от мастера — он появится в этом списке.'
              : 'Измените запрос или очистите поле поиска.'}
          </p>
        </div>
      ) : (
        <ul
          className={cn(
            'grid gap-4',
            filteredMasters.length === 1 ? 'max-w-lg' : 'sm:grid-cols-2 xl:grid-cols-3',
          )}
        >
          {filteredMasters.map((m) => (
            <MasterCard key={m.link_id} master={m} onBook={() => openBookingModal(m.master_id)} />
          ))}
        </ul>
      )}
    </div>
  )
}
