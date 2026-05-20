import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'

import { clientMasterLabel, clientsMyMasterPatchApi } from '../../api/clients'
import { useClientCabinet } from '../../components/client/ClientCabinetContext'
import { getUserFacingError } from '../../lib/apiErrors'
import { cn } from '../../lib/forms'
import { surfaceCard } from '../../lib/surface'
import type { ClientMasterView } from '../../mocks/clientCabinetMocks'

function IconSearch(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35m1.35-5.15a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z" />
    </svg>
  )
}

function IconPencil(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10"
      />
    </svg>
  )
}

function IconCheck(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}

function IconX(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

const aliasActionButtonClass =
  'rounded-md p-1.5 transition disabled:opacity-50 disabled:pointer-events-none'

function masterInitials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ''}${parts[1][0] ?? ''}`.toUpperCase()
  }
  return name.trim().slice(0, 2).toUpperCase() || '?'
}

function aliasDraftValue(master: ClientMasterView) {
  return master.client_alias?.trim() || master.display_name
}

function MasterContacts({ master }: { master: ClientMasterView }) {
  const rows: { label: string; value: string; href?: string }[] = []
  if (master.contact_email) {
    rows.push({ label: 'Email', value: master.contact_email, href: `mailto:${master.contact_email}` })
  }
  if (master.contact_phone) {
    rows.push({ label: 'Телефон', value: master.contact_phone, href: `tel:${master.contact_phone}` })
  }
  if (master.telegram) {
    const handle = master.telegram.replace(/^@/, '')
    rows.push({ label: 'Telegram', value: master.telegram, href: `https://t.me/${handle}` })
  }

  if (rows.length === 0) {
    return <p className="mt-3 text-sm text-stone-500 dark:text-stone-400">Контакты мастера не указаны.</p>
  }

  return (
    <ul className="mt-3 space-y-1.5 text-sm text-stone-600 dark:text-stone-400">
      {rows.map((row) => (
        <li key={row.label}>
          {row.label}:{' '}
          {row.href ? (
            <a
              href={row.href}
              target={row.label === 'Telegram' ? '_blank' : undefined}
              rel={row.label === 'Telegram' ? 'noreferrer' : undefined}
              className="font-medium text-teal-800 hover:underline dark:text-teal-300"
            >
              {row.value}
            </a>
          ) : (
            <span className="font-medium text-stone-800 dark:text-stone-200">{row.value}</span>
          )}
        </li>
      ))}
    </ul>
  )
}

function MasterCard({
  master,
  onBook,
  onAliasSaved,
}: {
  master: ClientMasterView
  onBook: () => void
  onAliasSaved: () => void
}) {
  const label = clientMasterLabel(master)
  const hasCustomAlias = Boolean(master.client_alias?.trim())
  const [editingAlias, setEditingAlias] = useState(false)
  const [aliasDraft, setAliasDraft] = useState(() => aliasDraftValue(master))
  const [aliasError, setAliasError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editingAlias) {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editingAlias])

  const saveAlias = useMutation({
    mutationFn: (nextAlias: string) => {
      const trimmed = nextAlias.trim()
      const payload =
        trimmed === master.display_name.trim() || !trimmed ? null : trimmed
      return clientsMyMasterPatchApi(master.master_id, { client_alias: payload })
    },
    onSuccess: () => {
      setEditingAlias(false)
      setAliasError(null)
      onAliasSaved()
    },
    onError: (err) => setAliasError(getUserFacingError(err)),
  })

  const commitAlias = () => {
    const trimmed = aliasDraft.trim()
    if (!trimmed) {
      setAliasDraft(master.display_name)
      setEditingAlias(false)
      setAliasError(null)
      return
    }
    const currentStored = master.client_alias?.trim() || master.display_name
    if (trimmed === currentStored) {
      setEditingAlias(false)
      setAliasError(null)
      return
    }
    saveAlias.mutate(trimmed)
  }

  const cancelAliasEdit = () => {
    setAliasDraft(aliasDraftValue(master))
    setEditingAlias(false)
    setAliasError(null)
  }

  return (
    <li className={surfaceCard('flex flex-col p-5')}>
      <div className="flex items-start gap-3">
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-teal-100 text-sm font-semibold text-teal-800 dark:bg-teal-950/60 dark:text-teal-200"
          aria-hidden
        >
          {masterInitials(label)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              {editingAlias ? (
                <div className="space-y-1">
                  <div className="flex items-center gap-1">
                    <input
                      ref={inputRef}
                      value={aliasDraft}
                      onChange={(e) => setAliasDraft(e.target.value)}
                      maxLength={200}
                      disabled={saveAlias.isPending}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          commitAlias()
                        }
                        if (e.key === 'Escape') {
                          e.preventDefault()
                          cancelAliasEdit()
                        }
                      }}
                      className={cn(
                        'min-w-0 flex-1 rounded-md border border-teal-500 bg-white px-2 py-1 text-base font-semibold',
                        'outline-none ring-2 ring-teal-500/20 dark:border-teal-500 dark:bg-stone-950 dark:text-stone-50',
                      )}
                      aria-label="Как вы называете этого мастера"
                    />
                    <button
                      type="button"
                      disabled={saveAlias.isPending}
                      onClick={() => commitAlias()}
                      className={cn(
                        aliasActionButtonClass,
                        'text-teal-700 hover:bg-teal-50 dark:text-teal-300 dark:hover:bg-teal-950/50',
                      )}
                      aria-label="Сохранить название"
                      title="Сохранить"
                    >
                      <IconCheck className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      disabled={saveAlias.isPending}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={cancelAliasEdit}
                      className={cn(
                        aliasActionButtonClass,
                        'text-stone-500 hover:bg-stone-100 dark:text-stone-400 dark:hover:bg-stone-800',
                      )}
                      aria-label="Отменить редактирование"
                      title="Отмена"
                    >
                      <IconX className="h-4 w-4" />
                    </button>
                  </div>
                  {aliasError ? <p className="text-xs text-red-600 dark:text-red-400">{aliasError}</p> : null}
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <p className="font-semibold text-stone-900 dark:text-stone-50">{label}</p>
                  <button
                    type="button"
                    onClick={() => {
                      setAliasDraft(aliasDraftValue(master))
                      setEditingAlias(true)
                    }}
                    className="rounded-md p-1 text-stone-400 transition hover:bg-stone-100 hover:text-teal-700 dark:hover:bg-stone-800 dark:hover:text-teal-300"
                    aria-label="Изменить название мастера"
                    title="Изменить название"
                  >
                    <IconPencil className="h-4 w-4" />
                  </button>
                </div>
              )}
              {hasCustomAlias && !editingAlias ? (
                <p className="text-xs text-stone-500 dark:text-stone-400">Мастер: {master.display_name}</p>
              ) : master.public_slug && !hasCustomAlias && !editingAlias ? (
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

      <MasterContacts master={master} />

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
  const queryClient = useQueryClient()
  const [masterSearch, setMasterSearch] = useState('')

  const refreshMasters = () => {
    void queryClient.invalidateQueries({ queryKey: ['clients', 'me', 'masters'] })
  }

  const filteredMasters = useMemo(() => {
    const q = masterSearch.trim().toLowerCase()
    if (!q) {
      return masters
    }
    return masters.filter((m) => {
      const label = clientMasterLabel(m).toLowerCase()
      return (
        label.includes(q) ||
        m.display_name.toLowerCase().includes(q) ||
        (m.alias?.toLowerCase().includes(q) ?? false) ||
        (m.client_alias?.toLowerCase().includes(q) ?? false) ||
        (m.contact_email?.toLowerCase().includes(q) ?? false) ||
        (m.contact_phone?.toLowerCase().includes(q) ?? false) ||
        (m.telegram?.toLowerCase().includes(q) ?? false)
      )
    })
  }, [masters, masterSearch])

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Мои мастера</h1>
          <p className="mt-1 max-w-2xl text-sm text-stone-600 dark:text-stone-400">
            Студии и специалисты, с которыми вы связаны. Название можно изменить у карандаша, затем записаться на визит.
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:max-w-md">
          <label className="relative block">
            <span className="sr-only">Поиск по имени мастера</span>
            <IconSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
            <input
              value={masterSearch}
              onChange={(e) => setMasterSearch(e.target.value)}
              placeholder="Поиск по имени, контактам или alias"
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
            <MasterCard
              key={m.link_id}
              master={m}
              onBook={() => openBookingModal(m.master_id)}
              onAliasSaved={refreshMasters}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
