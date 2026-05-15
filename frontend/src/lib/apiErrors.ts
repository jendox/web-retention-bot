/** Сообщения об ошибках API для UI и парсинг тел FastAPI. */

/** Сообщения бэкенда (англ.) → текст для пользователя (рус.). */
const DETAIL_RU: Record<string, string> = {
  'User already exists.': 'Этот email уже зарегистрирован.',
  'Invalid credentials': 'Неверный email или пароль.',
  'Email address is not verified yet': 'Сначала подтвердите email по ссылке из письма.',
  'Account is disabled': 'Аккаунт отключён. Обратитесь в поддержку.',
  'Invalid or expired verification link': 'Ссылка недействительна или устарела. Запросите новое письмо.',
  'Not authenticated': 'Требуется вход.',
  'Email address is not verified': 'Сначала подтвердите email.',
  'Master profile not found': 'Профиль мастера не найден.',
  'Client not found.': 'Клиент не найден.',
  'No fields to update.': 'Нечего сохранить: не переданы поля.',
  'Client has bookings and cannot be deleted.': 'Нельзя удалить клиента: есть записи.',
  'Client is linked to an invitation and cannot be deleted.': 'Нельзя удалить клиента: есть привязка по приглашению.',
}

export class ApiError extends Error {
  readonly status: number
  /** Сообщение с бэкенда до локализации. */
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export function translateApiDetail(detail: string): string {
  const trimmed = detail.trim()
  return DETAIL_RU[trimmed] ?? DETAIL_RU[detail] ?? detail
}

/** Разбор тела ответа FastAPI (строка или validation errors). */
export function parseFastApiDetail(rawBody: string): string {
  try {
    const j = JSON.parse(rawBody) as { detail?: unknown }
    if (typeof j.detail === 'string') {
      return j.detail
    }
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((item: unknown) => {
          if (item && typeof item === 'object' && 'msg' in item) {
            return String((item as { msg: string }).msg)
          }
          return JSON.stringify(item)
        })
        .join(' ')
    }
  } catch {
    /* не JSON */
  }
  return rawBody
}

export function getUserFacingError(err: unknown): string {
  if (err instanceof ApiError) {
    return translateApiDetail(err.detail)
  }
  if (err instanceof Error) {
    return err.message
  }
  return 'Что-то пошло не так. Попробуйте ещё раз.'
}
