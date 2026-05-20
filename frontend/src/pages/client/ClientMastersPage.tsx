import { useMemo, useState } from 'react'

import { useClientCabinet } from '../../components/client/ClientCabinetContext'
import type { ClientMasterView } from '../../mocks/clientCabinetMocks'

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
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Мои мастера</h1>
        <label className="block max-w-md flex-1">
          <span className="sr-only">Поиск</span>
          <input
            value={masterSearch}
            onChange={(e) => setMasterSearch(e.target.value)}
            placeholder="Поиск по имени мастера"
            className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100"
          />
        </label>
      </div>
      {overviewLoading ? (
        <p className="text-sm text-stone-500 dark:text-stone-400">Загружаем…</p>
      ) : filteredMasters.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-stone-400">
          {masters.length === 0
            ? 'Пока нет привязанных мастеров. Примите приглашение по ссылке — мастер появится здесь.'
            : 'Ничего не найдено. Измените запрос.'}
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {filteredMasters.map((m: ClientMasterView) => (
            <li
              key={m.link_id}
              className="flex flex-col gap-2 rounded-xl border border-stone-100 bg-stone-50/80 px-4 py-4 dark:border-stone-800 dark:bg-stone-950/40"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-semibold text-stone-900 dark:text-stone-100">{m.display_name}</p>
                  {m.public_slug ? (
                    <p className="text-xs text-stone-500 dark:text-stone-400">@{m.public_slug}</p>
                  ) : null}
                </div>
                <span className="shrink-0 rounded-md bg-white px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-teal-800 shadow-sm dark:bg-stone-900 dark:text-teal-200">
                  активна
                </span>
              </div>
              {m.alias ? (
                <p className="text-sm text-stone-600 dark:text-stone-400">Как вас зовут у мастера: {m.alias}</p>
              ) : null}
              <p className="text-sm text-stone-600 dark:text-stone-300">
                <span className="text-stone-500 dark:text-stone-400">Email: </span>
                <a
                  href={`mailto:${m.contact_email}`}
                  className="font-medium text-teal-800 hover:underline dark:text-teal-300"
                >
                  {m.contact_email}
                </a>
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => openBookingModal(m.master_id)}
                  className="rounded-lg border border-teal-600 bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-500 dark:bg-teal-500 dark:text-stone-950 dark:hover:bg-teal-400"
                >
                  Записаться
                </button>
                <button
                  type="button"
                  disabled
                  className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-400 dark:border-stone-600"
                  title="Скоро"
                >
                  Написать
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
