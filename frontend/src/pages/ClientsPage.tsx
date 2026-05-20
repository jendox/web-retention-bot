import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { meApi } from '../api/auth'
import { ApiError } from '../api/client'
import { clientsCreateApi, clientsDeleteApi, clientsListApi, type ClientWithLink } from '../api/clients'
import { invitationsCreateApi } from '../api/invitations'
import { getUserFacingError } from '../lib/apiErrors'
import { formatNoShowCount, shouldWarnFrequentNoShows } from '../lib/clientNoShow'
import { cn } from '../lib/forms'
import { surfacePanelOverflow } from '../lib/surface'
import { parsePage, parsePageSize, type PageSize } from '../lib/pagination'
import { queryClient } from '../lib/query'

type InviteModalTarget = { kind: 'general' } | { kind: 'client'; clientId: string; name: string }

const fieldClass =
  'w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-stone-900 shadow-sm outline-none focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:focus:border-stone-500'

function IconPlus(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
    </svg>
  )
}

function IconLinkInvite(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
      />
    </svg>
  )
}

function IconCalendarSmall(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}

function IconClose(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

function IconTrash(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  )
}

function IconWarning(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"
      />
    </svg>
  )
}

type AddModalProps = {
  open: boolean
  onClose: () => void
  onSubmit: (values: { display_name: string; phone: string; email: string }) => void
  isPending: boolean
  errorMessage?: string
}

function AddClientModal({ open, onClose, onSubmit, isPending, errorMessage }: AddModalProps) {
  const form = useForm({ defaultValues: { display_name: '', phone: '', email: '' } })

  useEffect(() => {
    if (open) {
      form.reset({ display_name: '', phone: '', email: '' })
    }
  }, [open, form])

  useEffect(() => {
    if (!open) {
      return
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-client-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose()
        }
      }}
    >
      <div
        className="relative w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-xl dark:border-stone-700 dark:bg-stone-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 id="add-client-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
            Новый клиент
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-stone-500 transition hover:bg-stone-100 hover:text-stone-800 dark:hover:bg-stone-800 dark:hover:text-stone-200"
            aria-label="Закрыть"
          >
            <IconClose className="h-5 w-5" />
          </button>
        </div>
        <p className="mb-4 text-sm text-stone-600 dark:text-stone-400">
          Карточка для учёта: без логина в приложении. Позже можно будет пригласить человека по ссылке.
        </p>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((vals) =>
            onSubmit({
              display_name: vals.display_name.trim(),
              phone: vals.phone.trim(),
              email: vals.email.trim(),
            }),
          )}
        >
          <p className="text-xs text-stone-500 dark:text-stone-500">
            <span className="font-medium text-red-600 dark:text-red-400" aria-hidden>
              *
            </span>{' '}
            — обязательно.
          </p>
          <label className="block">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">
              Имя или подпись{' '}
              <abbr title="обязательное поле" className="font-semibold text-red-600 no-underline dark:text-red-400">
                *
              </abbr>
            </span>
            <input
              {...form.register('display_name', { required: true })}
              className={cn(fieldClass, 'mt-1')}
              autoFocus
              aria-required="true"
            />
            {form.formState.errors.display_name ? (
              <span className="mt-1 block text-xs text-red-700 dark:text-red-300">Укажите имя</span>
            ) : null}
          </label>
          <label className="block">
            <span className="flex flex-wrap items-baseline gap-x-2">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Телефон</span>
              <span className="text-xs font-normal text-stone-400 dark:text-stone-500">необязательно</span>
            </span>
            <input {...form.register('phone')} type="tel" className={cn(fieldClass, 'mt-1')} />
          </label>
          <label className="block">
            <span className="flex flex-wrap items-baseline gap-x-2">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Email</span>
              <span className="text-xs font-normal text-stone-400 dark:text-stone-500">необязательно</span>
            </span>
            <input {...form.register('email')} type="email" className={cn(fieldClass, 'mt-1')} />
          </label>
          {errorMessage ? (
            <p className="text-sm text-red-700 dark:text-red-300" role="alert">
              {errorMessage}
            </p>
          ) : null}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-500 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
            >
              {isPending ? 'Сохранение…' : 'Добавить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function ClientsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const page = parsePage(searchParams.get('page'))
  const pageSize = parsePageSize(searchParams.get('page_size'))

  const setPage = (p: number) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('page', String(p))
      n.set('page_size', String(pageSize))
      return n
    })
  }

  const setPageSize = (ps: PageSize) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev)
      n.set('page', '1')
      n.set('page_size', String(ps))
      return n
    })
  }

  const [addOpen, setAddOpen] = useState(false)
  const [inviteModal, setInviteModal] = useState<InviteModalTarget | null>(null)
  const [inviteUrl, setInviteUrl] = useState<string | null>(null)
  const [inviteConflict, setInviteConflict] = useState(false)
  const [inviteCopyDone, setInviteCopyDone] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<ClientWithLink | null>(null)

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const clients = useQuery({
    queryKey: ['clients', page, pageSize],
    queryFn: () => clientsListApi({ page, page_size: pageSize }),
    enabled: me.isSuccess,
  })

  const total = clients.data?.total ?? 0
  const rows = clients.data?.items ?? []
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  useEffect(() => {
    if (!clients.isSuccess || !clients.data) {
      return
    }
    const tp = Math.max(1, Math.ceil(clients.data.total / pageSize))
    if (page > tp) {
      setSearchParams((prev) => {
        const n = new URLSearchParams(prev)
        n.set('page', String(tp))
        n.set('page_size', String(pageSize))
        return n
      })
    }
  }, [clients.isSuccess, clients.data, page, pageSize, setSearchParams])

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  const create = useMutation({
    mutationFn: clientsCreateApi,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['clients'] })
      setAddOpen(false)
    },
  })

  const remove = useMutation({
    mutationFn: (id: string) => clientsDeleteApi(id),
    onSuccess: async (_, id) => {
      await queryClient.invalidateQueries({ queryKey: ['clients'] })
      queryClient.removeQueries({ queryKey: ['client', id] })
      setPendingDelete(null)
    },
  })

  const createInviteLink = useMutation({
    mutationFn: async (input: { target: InviteModalTarget; replace: boolean }) => {
      if (input.target.kind === 'general') {
        return invitationsCreateApi({ replace: input.replace })
      }
      return invitationsCreateApi({ target_client_id: input.target.clientId, replace: input.replace })
    },
    onSuccess: (data) => {
      setInviteUrl(`${window.location.origin}/invite/${data.token}`)
      setInviteConflict(false)
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        setInviteConflict(true)
        setInviteUrl(null)
      }
    },
  })

  const openInviteModal = (target: InviteModalTarget) => {
    setInviteModal(target)
    setInviteUrl(null)
    setInviteConflict(false)
    setInviteCopyDone(false)
    createInviteLink.reset()
    createInviteLink.mutate({ target, replace: false })
  }

  const reissueInvite = () => {
    if (!inviteModal) {
      return
    }
    createInviteLink.mutate({ target: inviteModal, replace: true })
  }

  const copyInviteUrl = async () => {
    if (!inviteUrl) {
      return
    }
    try {
      await navigator.clipboard.writeText(inviteUrl)
      setInviteCopyDone(true)
      window.setTimeout(() => setInviteCopyDone(false), 2000)
    } catch {
      setInviteCopyDone(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Клиенты</h1>
          <p className="mt-1 max-w-xl text-sm text-stone-600 dark:text-stone-400">
            Список клиентов, их контакты, приглашения и записи.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2 sm:pt-1">
          <button
            type="button"
            onClick={() => {
              create.reset()
              setAddOpen(true)
            }}
            title="Добавить клиента вручную — карточка без аккаунта в приложении"
            aria-label="Добавить клиента вручную"
            className="flex h-11 w-11 items-center justify-center rounded-full bg-teal-600 text-white shadow-md shadow-teal-900/20 transition hover:bg-teal-500 dark:shadow-teal-950/30"
          >
            <IconPlus className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={() => openInviteModal({ kind: 'general' })}
            title="Общая ссылка-приглашение: клиент регистрируется и подтверждает email"
            aria-label="Создать общую ссылку-приглашение"
            className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-teal-600/40 bg-white text-teal-700 shadow-sm transition hover:border-teal-600 hover:bg-teal-50 dark:border-teal-500/50 dark:bg-stone-900 dark:text-teal-300 dark:hover:bg-teal-950/40"
          >
            <IconLinkInvite className="h-5 w-5" />
          </button>
        </div>
      </div>

      <div className={surfacePanelOverflow()}>
        {clients.isLoading ? (
          <p className="p-8 text-center text-sm text-stone-500">Загрузка списка…</p>
        ) : total === 0 ? (
          <div className="px-6 py-16 text-center">
            <p className="text-stone-700 dark:text-stone-200">Пока никого нет в списке</p>
            <p className="mt-2 text-sm text-stone-500 dark:text-stone-400">
              Нажмите «+», чтобы добавить клиента вручную,               или ссылку-приглашение (значок цепочки — общая или по строке клиента).
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead>
                <tr className="border-b border-stone-200 bg-stone-50/80 dark:border-stone-700 dark:bg-stone-950/50">
                  <th className="px-4 py-3 font-semibold text-stone-700 dark:text-stone-300">Имя</th>
                  <th className="px-4 py-3 font-semibold text-stone-700 dark:text-stone-300">Email</th>
                  <th className="px-4 py-3 font-semibold text-stone-700 dark:text-stone-300">Телефон</th>
                  <th className="hidden px-4 py-3 font-semibold text-stone-500 md:table-cell">Псевдоним</th>
                  <th className="w-32 px-4 py-3 text-right font-semibold text-stone-500">
                    <span className="sr-only">Действия</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
                {rows.map((row) => (
                  <tr
                    key={row.client.id}
                    className="cursor-pointer transition hover:bg-stone-50/90 dark:hover:bg-stone-800/30"
                    onClick={() => navigate(`/master/clients/${row.client.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        navigate(`/master/clients/${row.client.id}`)
                      }
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <td className="px-4 py-3 font-medium text-stone-900 dark:text-stone-100">
                      <div className="flex items-center gap-2">
                        <span>{row.client.display_name}</span>
                        {shouldWarnFrequentNoShows(row.booking_stats) ? (
                          <span
                            className="inline-flex shrink-0 items-center justify-center text-rose-600 dark:text-rose-400"
                            title={`Частые неявки: ${formatNoShowCount(row.booking_stats!.no_show_count)}`}
                            aria-label={`Частые неявки: ${formatNoShowCount(row.booking_stats!.no_show_count)}`}
                          >
                            <IconWarning className="h-4 w-4" />
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-stone-600 dark:text-stone-400">
                      <div className="flex items-center gap-2">
                        <span className={cn(row.link.invite_email_mismatch && 'text-amber-800 dark:text-amber-200')}>
                          {row.client.email ?? '—'}
                        </span>
                        {row.link.invite_email_mismatch ? (
                          <span
                            className="inline-flex shrink-0 items-center justify-center text-amber-600 dark:text-amber-300"
                            title="Email в карточке отличается от email аккаунта клиента. Проверьте адрес, чтобы клиент получал уведомления."
                            aria-label="Email в карточке отличается от email аккаунта клиента"
                          >
                            <IconWarning className="h-4 w-4" />
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-stone-600 dark:text-stone-400">{row.client.phone ?? '—'}</td>
                    <td className="hidden max-w-xs truncate px-4 py-3 text-stone-500 md:table-cell">
                      {row.link.alias ?? '—'}
                    </td>
                    <td
                      className="px-4 py-2"
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()}
                    >
                      <div className="flex justify-end gap-1">
                        <button
                          type="button"
                          title="Создать запись для клиента"
                          onClick={() =>
                            navigate(`/master/bookings?client_id=${row.client.id}&list_client_id=${row.client.id}`)
                          }
                          className="rounded-lg p-2 text-stone-500 transition hover:bg-teal-50 hover:text-teal-700 dark:text-stone-400 dark:hover:bg-teal-950/40 dark:hover:text-teal-300"
                          aria-label={`Создать запись для клиента ${row.client.display_name}`}
                        >
                          <IconCalendarSmall className="h-5 w-5" />
                        </button>
                        <button
                          type="button"
                          disabled={Boolean(row.client.user_id)}
                          title={
                            row.client.user_id
                              ? 'У клиента уже есть вход'
                              : 'Ссылка для этой карточки клиента'
                          }
                          onClick={() =>
                            openInviteModal({
                              kind: 'client',
                              clientId: row.client.id,
                              name: row.client.display_name,
                            })
                          }
                          className="rounded-lg p-2 text-teal-600 transition enabled:hover:bg-teal-50 disabled:cursor-not-allowed disabled:opacity-40 dark:text-teal-400 dark:enabled:hover:bg-teal-950/40"
                          aria-label={`Пригласить клиента ${row.client.display_name}`}
                        >
                          <IconLinkInvite className="h-5 w-5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            remove.reset()
                            setPendingDelete(row)
                          }}
                          className="rounded-lg p-2 text-stone-400 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40 dark:hover:text-rose-400"
                          aria-label={`Удалить клиента ${row.client.display_name}`}
                          title="Удалить клиента"
                        >
                          <IconTrash className="h-5 w-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-col gap-3 border-t border-stone-200 bg-stone-50/50 px-4 py-3 dark:border-stone-700 dark:bg-stone-950/30 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
            <p className="text-sm text-stone-600 dark:text-stone-400">
              Страница {page} из {totalPages}
              <span className="text-stone-400 dark:text-stone-500"> · </span>
              всего {total}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-2 text-sm text-stone-600 dark:text-stone-400">
                <span className="whitespace-nowrap">На странице</span>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(Number(e.target.value) as PageSize)}
                  className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-stone-900 shadow-sm dark:border-stone-600 dark:bg-stone-900 dark:text-stone-100"
                >
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                </select>
              </label>
              <div className="flex gap-1">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 enabled:hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-stone-600 dark:text-stone-200 dark:enabled:hover:bg-stone-800"
                >
                  Назад
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 enabled:hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-stone-600 dark:text-stone-200 dark:enabled:hover:bg-stone-800"
                >
                  Вперёд
                </button>
              </div>
            </div>
          </div>
          </>
        )}
      </div>

      <AddClientModal
        open={addOpen}
        onClose={() => {
          create.reset()
          setAddOpen(false)
        }}
        isPending={create.isPending}
        errorMessage={create.isError ? 'Не удалось сохранить. Попробуйте ещё раз.' : undefined}
        onSubmit={(vals) =>
          create.mutate({
            display_name: vals.display_name,
            phone: vals.phone || undefined,
            email: vals.email || undefined,
          })
        }
      />

      {pendingDelete ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-client-title"
          onClick={(e) => {
            if (e.target === e.currentTarget && !remove.isPending) {
              setPendingDelete(null)
            }
          }}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-xl dark:border-stone-700 dark:bg-stone-900"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="delete-client-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
              Удалить клиента?
            </h2>
            <p className="mt-3 text-sm text-stone-600 dark:text-stone-400">
              Будет удалена карточка «{pendingDelete.client.display_name}». Это действие необратимо, если у клиента нет
              записей и привязок по приглашению.
            </p>
            {remove.isError ? (
              <p className="mt-3 text-sm text-red-700 dark:text-red-300" role="alert">
                {getUserFacingError(remove.error)}
              </p>
            ) : null}
            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                disabled={remove.isPending}
                onClick={() => setPendingDelete(null)}
                className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
              >
                Отмена
              </button>
              <button
                type="button"
                disabled={remove.isPending}
                onClick={() => remove.mutate(pendingDelete.client.id)}
                className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-50 dark:bg-rose-600 dark:hover:bg-rose-500"
              >
                {remove.isPending ? 'Удаление…' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {inviteModal ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
          role="dialog"
          aria-modal="true"
          aria-labelledby="invite-link-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setInviteModal(null)
            }
          }}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-xl dark:border-stone-700 dark:bg-stone-900"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="invite-link-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
              Ссылка-приглашение
            </h2>
            <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">
              {inviteModal.kind === 'general'
                ? 'Отправьте клиенту. После регистрации и подтверждения email он сможет принять приглашение.'
                : `Для карточки «${inviteModal.name}». Ссылка привяжется к этой записи после принятия.`}
            </p>

            {createInviteLink.isPending && !inviteConflict ? (
              <p className="mt-4 text-sm text-stone-500">Создаём ссылку…</p>
            ) : null}

            {inviteConflict ? (
              <div className="mt-4 space-y-3 rounded-lg border border-amber-200/90 bg-amber-50/90 p-3 text-sm dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100">
                <p>Для этого клиента уже есть активное приглашение. Можно перевыпустить — старая ссылка перестанет работать.</p>
                <button
                  type="button"
                  onClick={() => reissueInvite()}
                  disabled={createInviteLink.isPending}
                  className="rounded-lg bg-amber-700 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50 dark:bg-amber-600 dark:hover:bg-amber-500"
                >
                  {createInviteLink.isPending ? '…' : 'Перевыпустить ссылку'}
                </button>
              </div>
            ) : null}

            {inviteUrl ? (
              <div className="mt-4 space-y-2">
                <button
                  type="button"
                  onClick={() => void copyInviteUrl()}
                  className="w-full break-all rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-left font-mono text-xs text-stone-800 underline decoration-dotted hover:bg-stone-100 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:hover:bg-stone-900"
                >
                  {inviteUrl}
                </button>
                <button
                  type="button"
                  onClick={() => void copyInviteUrl()}
                  className="w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white hover:bg-teal-500 dark:bg-teal-500 dark:text-stone-950"
                >
                  {inviteCopyDone ? 'Скопировано' : 'Копировать'}
                </button>
              </div>
            ) : null}

            {createInviteLink.isError && !inviteConflict ? (
              <p className="mt-3 text-sm text-red-700 dark:text-red-300">{getUserFacingError(createInviteLink.error)}</p>
            ) : null}

            <button
              type="button"
              onClick={() => setInviteModal(null)}
              className="mt-5 w-full rounded-lg border border-stone-300 py-2.5 text-sm font-medium text-stone-700 hover:bg-stone-50 dark:border-stone-600 dark:text-stone-200 dark:hover:bg-stone-800"
            >
              Закрыть
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
