import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { meApi } from '../api/auth'
import { masterMeApi } from '../api/masters'
import {
  serviceDeleteApi,
  servicePatchApi,
  servicesCreateApi,
  servicesListApi,
  type Service,
  type ServiceCreatePayload,
} from '../api/services'
import { getUserFacingError } from '../lib/apiErrors'
import { CURRENCIES, DEFAULT_MASTER_CURRENCY, type CurrencyCode } from '../lib/currency'
import { cn } from '../lib/forms'
import { parsePage, parsePageSize, type PageSize } from '../lib/pagination'
import { queryClient } from '../lib/query'

const fieldClass =
  'w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-stone-900 shadow-sm outline-none focus:border-stone-400 focus:ring-2 focus:ring-stone-400/15 dark:border-stone-600 dark:bg-stone-950 dark:text-stone-100 dark:focus:border-stone-500'

function IconPlus(props: { className?: string }) {
  return (
    <svg className={props.className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
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

type AddModalProps = {
  open: boolean
  onClose: () => void
  defaultCurrency: CurrencyCode
  onSubmit: (values: ServiceCreatePayload) => void
  isPending: boolean
  errorMessage?: string
}

function AddServiceModal({ open, onClose, defaultCurrency, onSubmit, isPending, errorMessage }: AddModalProps) {
  const form = useForm<ServiceCreatePayload>({
    defaultValues: {
      name: '',
      description: '',
      duration_min: 60,
      price: '',
      currency: defaultCurrency,
      is_active: true,
      sort_order: 0,
    },
  })

  useEffect(() => {
    if (open) {
      form.reset({
        name: '',
        description: '',
        duration_min: 60,
        price: '',
        currency: defaultCurrency,
        is_active: true,
        sort_order: 0,
      })
    }
  }, [open, defaultCurrency, form])

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
      aria-labelledby="add-service-title"
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
          <h2 id="add-service-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
            Новая услуга
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
          По умолчанию валюта совпадает с валютой в вашем профиле; при необходимости выберите другую для этой услуги.
        </p>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((vals) => {
            const body: ServiceCreatePayload = {
              name: vals.name.trim(),
              duration_min: vals.duration_min,
              price: String(vals.price).trim(),
              is_active: vals.is_active ?? true,
              sort_order: vals.sort_order ?? 0,
            }
            const desc = vals.description?.trim()
            if (desc) {
              body.description = desc
            }
            const cur = vals.currency as CurrencyCode | undefined
            if (cur && cur !== defaultCurrency) {
              body.currency = cur
            }
            onSubmit(body)
          })}
        >
          <label className="block">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">
              Название <span className="text-red-600 dark:text-red-400">*</span>
            </span>
            <input
              {...form.register('name', { required: true })}
              className={cn(fieldClass, 'mt-1')}
              autoFocus
              aria-required="true"
            />
            {form.formState.errors.name ? (
              <span className="mt-1 block text-xs text-red-700 dark:text-red-300">Укажите название</span>
            ) : null}
          </label>
          <label className="block">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Описание</span>
            <textarea {...form.register('description')} rows={2} className={cn(fieldClass, 'mt-1 resize-y')} />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Длительность (мин) *</span>
              <input
                type="number"
                min={1}
                {...form.register('duration_min', { valueAsNumber: true, required: true, min: 1 })}
                className={cn(fieldClass, 'mt-1')}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Цена *</span>
              <input
                {...form.register('price', { required: true })}
                className={cn(fieldClass, 'mt-1')}
                inputMode="decimal"
                placeholder="0.00"
              />
            </label>
          </div>
          <label className="block">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Валюта</span>
            <select {...form.register('currency')} className={cn(fieldClass, 'mt-1')}>
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300">
            <input type="checkbox" {...form.register('is_active', { valueAsBoolean: true })} className="rounded border-stone-300" />
            Услуга активна (видна при записи)
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

type EditServiceModalProps = {
  service: Service | null
  onClose: () => void
  onSubmit: (id: string, values: ServiceCreatePayload) => void
  isPending: boolean
  errorMessage?: string
}

function serviceToCurrency(currency: string): CurrencyCode {
  return (CURRENCIES as readonly string[]).includes(currency) ? (currency as CurrencyCode) : DEFAULT_MASTER_CURRENCY
}

function EditServiceModal({ service, onClose, onSubmit, isPending, errorMessage }: EditServiceModalProps) {
  const open = service !== null
  const form = useForm<ServiceCreatePayload>({
    defaultValues: {
      name: '',
      description: '',
      duration_min: 60,
      price: '',
      currency: DEFAULT_MASTER_CURRENCY,
      is_active: true,
      sort_order: 0,
    },
  })

  useEffect(() => {
    if (!service) {
      return
    }
    form.reset({
      name: service.name,
      description: service.description ?? '',
      duration_min: service.duration_min,
      price: service.price,
      currency: serviceToCurrency(service.currency),
      is_active: service.is_active,
      sort_order: service.sort_order,
    })
  }, [service, form])

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

  if (!service) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-service-title"
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
          <h2 id="edit-service-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
            Редактировать услугу
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
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((vals) => {
            const body: ServiceCreatePayload = {
              name: vals.name.trim(),
              duration_min: vals.duration_min,
              price: String(vals.price).trim(),
              is_active: vals.is_active ?? true,
              sort_order: vals.sort_order ?? 0,
              currency: vals.currency as CurrencyCode,
            }
            const desc = vals.description?.trim()
            body.description = desc ? desc : null
            onSubmit(service.id, body)
          })}
        >
          <label className="block">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">
              Название <span className="text-red-600 dark:text-red-400">*</span>
            </span>
            <input
              {...form.register('name', { required: true })}
              className={cn(fieldClass, 'mt-1')}
              autoFocus
              aria-required="true"
            />
            {form.formState.errors.name ? (
              <span className="mt-1 block text-xs text-red-700 dark:text-red-300">Укажите название</span>
            ) : null}
          </label>
          <label className="block">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Описание</span>
            <textarea {...form.register('description')} rows={2} className={cn(fieldClass, 'mt-1 resize-y')} />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Длительность (мин) *</span>
              <input
                type="number"
                min={1}
                {...form.register('duration_min', { valueAsNumber: true, required: true, min: 1 })}
                className={cn(fieldClass, 'mt-1')}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Цена *</span>
              <input
                {...form.register('price', { required: true })}
                className={cn(fieldClass, 'mt-1')}
                inputMode="decimal"
                placeholder="0.00"
              />
            </label>
          </div>
          <label className="block">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Валюта</span>
            <select {...form.register('currency')} className={cn(fieldClass, 'mt-1')}>
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300">
            <input type="checkbox" {...form.register('is_active', { valueAsBoolean: true })} className="rounded border-stone-300" />
            Услуга активна (видна при записи)
          </label>
          <label className="block">
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Порядок сортировки</span>
            <input
              type="number"
              {...form.register('sort_order', { valueAsNumber: true })}
              className={cn(fieldClass, 'mt-1')}
            />
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
              {isPending ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function ServicesPage() {
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
  const [editingService, setEditingService] = useState<Service | null>(null)
  const [pendingDelete, setPendingDelete] = useState<Service | null>(null)

  const me = useQuery({ queryKey: ['me'], queryFn: meApi, retry: false })
  const master = useQuery({ queryKey: ['master'], queryFn: masterMeApi, enabled: me.isSuccess, retry: false })
  const list = useQuery({
    queryKey: ['services', page, pageSize],
    queryFn: () => servicesListApi({ page, page_size: pageSize }),
    enabled: me.isSuccess,
  })

  const total = list.data?.total ?? 0
  const rows = list.data?.items ?? []
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const defaultCurrency = (master.data?.default_currency as CurrencyCode) ?? DEFAULT_MASTER_CURRENCY

  useEffect(() => {
    if (!list.isSuccess || !list.data) {
      return
    }
    const tp = Math.max(1, Math.ceil(list.data.total / pageSize))
    if (page > tp) {
      setSearchParams((prev) => {
        const n = new URLSearchParams(prev)
        n.set('page', String(tp))
        n.set('page_size', String(pageSize))
        return n
      })
    }
  }, [list.isSuccess, list.data, page, pageSize, setSearchParams])

  useEffect(() => {
    if (me.isError) {
      navigate('/login')
    }
  }, [me.isError, navigate])

  const create = useMutation({
    mutationFn: servicesCreateApi,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['services'] })
      setAddOpen(false)
    },
  })

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: ServiceCreatePayload }) => servicePatchApi(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['services'] })
      setEditingService(null)
    },
  })

  const remove = useMutation({
    mutationFn: (id: string) => serviceDeleteApi(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['services'] })
      setPendingDelete(null)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">Услуги</h1>
          <p className="mt-1 max-w-xl text-sm text-stone-600 dark:text-stone-400">
            Каталог для записи: длительность, цена и валюта. Валюта по умолчанию в профиле:{' '}
            <span className="font-medium text-stone-800 dark:text-stone-200">{defaultCurrency}</span>.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2 sm:pt-1">
          <button
            type="button"
            onClick={() => {
              create.reset()
              setAddOpen(true)
            }}
            title="Добавить услугу"
            aria-label="Добавить услугу"
            className="flex h-11 w-11 items-center justify-center rounded-full bg-teal-600 text-white shadow-md shadow-teal-900/20 transition hover:bg-teal-500 dark:shadow-teal-950/30"
          >
            <IconPlus className="h-5 w-5" />
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-stone-200/90 bg-white shadow-sm dark:border-stone-700/90 dark:bg-stone-900/80">
        {list.isLoading ? (
          <p className="p-8 text-center text-sm text-stone-500">Загрузка списка…</p>
        ) : total === 0 ? (
          <div className="px-6 py-16 text-center">
            <p className="text-stone-700 dark:text-stone-200">Пока нет услуг</p>
            <p className="mt-2 text-sm text-stone-500 dark:text-stone-400">Нажмите «+», чтобы добавить первую услугу.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-200 bg-stone-50/80 dark:border-stone-700 dark:bg-stone-950/50">
                    <th className="px-4 py-3 font-semibold text-stone-700 dark:text-stone-300">Название</th>
                    <th className="px-4 py-3 font-semibold text-stone-700 dark:text-stone-300">Длительность</th>
                    <th className="px-4 py-3 font-semibold text-stone-700 dark:text-stone-300">Цена</th>
                    <th className="hidden px-4 py-3 font-semibold text-stone-700 dark:text-stone-300 sm:table-cell">
                      Статус
                    </th>
                    <th className="w-14 px-2 py-3 text-right font-semibold text-stone-500">
                      <span className="sr-only">Удалить</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
                  {rows.map((svc) => (
                    <tr
                      key={svc.id}
                      className="cursor-pointer transition hover:bg-stone-50/90 dark:hover:bg-stone-800/30"
                      onClick={() => {
                        update.reset()
                        setEditingService(svc)
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          update.reset()
                          setEditingService(svc)
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      aria-label={`Редактировать услугу: ${svc.name}`}
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-stone-900 dark:text-stone-100">{svc.name}</p>
                        {svc.description ? (
                          <p className="mt-0.5 line-clamp-2 text-xs text-stone-500 dark:text-stone-400">
                            {svc.description}
                          </p>
                        ) : null}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-stone-600 dark:text-stone-400">
                        {svc.duration_min} мин
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-stone-600 dark:text-stone-400">
                        {svc.price} {svc.currency}
                      </td>
                      <td className="hidden px-4 py-3 sm:table-cell">
                        {svc.is_active ? (
                          <span className="rounded-full bg-teal-50 px-2 py-0.5 text-xs font-medium text-teal-800 dark:bg-teal-950/50 dark:text-teal-200">
                            Активна
                          </span>
                        ) : (
                          <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-600 dark:bg-stone-400">
                            Выкл.
                          </span>
                        )}
                      </td>
                      <td className="px-2 py-2 text-right" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            remove.reset()
                            setPendingDelete(svc)
                          }}
                          className="rounded-lg p-2 text-stone-400 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40 dark:hover:text-rose-400"
                          aria-label={`Удалить услугу ${svc.name}`}
                          title="Удалить услугу"
                        >
                          <IconTrash className="h-5 w-5" />
                        </button>
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

      <AddServiceModal
        open={addOpen}
        onClose={() => {
          create.reset()
          setAddOpen(false)
        }}
        defaultCurrency={defaultCurrency}
        isPending={create.isPending}
        errorMessage={create.isError ? 'Не удалось сохранить. Попробуйте ещё раз.' : undefined}
        onSubmit={(body) => create.mutate(body)}
      />

      <EditServiceModal
        service={editingService}
        onClose={() => {
          update.reset()
          setEditingService(null)
        }}
        isPending={update.isPending}
        errorMessage={update.isError ? getUserFacingError(update.error) : undefined}
        onSubmit={(id, body) => update.mutate({ id, body })}
      />

      {pendingDelete ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/45 p-4 backdrop-blur-[2px]"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-service-title"
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
            <h2 id="delete-service-title" className="text-lg font-semibold text-stone-900 dark:text-stone-50">
              Удалить услугу?
            </h2>
            <p className="mt-3 text-sm text-stone-600 dark:text-stone-400">
              Будет удалена «{pendingDelete.name}». Если по услуге уже есть записи, удаление будет недоступно.
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
                onClick={() => remove.mutate(pendingDelete.id)}
                className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-50 dark:bg-rose-600 dark:hover:bg-rose-500"
              >
                {remove.isPending ? 'Удаление…' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
