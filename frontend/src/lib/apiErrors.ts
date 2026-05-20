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
  'Client profile not found': 'Профиль клиента не найден. Примите приглашение мастера.',
  'Client not found.': 'Клиент не найден.',
  'No fields to update.': 'Нечего сохранить: не переданы поля.',
  'Client has bookings and cannot be deleted.': 'Нельзя удалить клиента: есть записи.',
  'Client is linked to an invitation and cannot be deleted.': 'Нельзя удалить клиента: есть привязка по приглашению.',
  'Client email is linked to the client account and cannot be changed.':
    'Email подтвержден аккаунтом клиента и не редактируется.',
  'Client name is linked to the client account and cannot be changed.':
    'Имя подтверждено аккаунтом клиента и не редактируется.',
  'You cannot accept your own invitation.': 'Нельзя принять собственное приглашение.',
  'Invitation revoked': 'Приглашение отозвано.',
  'Client already has a login linked.': 'У клиента уже есть вход в приложение.',
  'An active invitation already exists for this client.': 'Для этого клиента уже есть активное приглашение.',
  'This client card is already linked to another account.': 'Эта карточка уже привязана к другому аккаунту.',
  'You are already linked to this master.': 'Вы уже связаны с этим мастером.',
  'Service not found.': 'Услуга не найдена.',
  'Service has bookings and cannot be deleted.': 'Нельзя удалить услугу: есть записи, связанные с ней.',
  'Service not found': 'Услуга не найдена.',
  'Unknown client linkage': 'Клиент не найден в вашей базе.',
  'Requested slot unavailable': 'Это время уже недоступно. Выберите другой слот.',
  'Overlapping booking exists': 'На это время уже есть запись.',
  'Booking not found': 'Запись не найдена.',
  'Active booking not found': 'Активная запись не найдена.',
  'Attendance already marked or booking is not awaiting confirmation':
    'Явка уже отмечена или запись не ждёт подтверждения.',
  'Too many requests': 'Слишком много попыток. Попробуйте позже.',
  'Schedule intervals must not overlap.': 'Интервалы рабочего времени не должны пересекаться.',
  'Schedule interval start_time must be before end_time.': 'Начало интервала должно быть раньше окончания.',
  'Closed override must not contain intervals.': 'У выходного дня не должно быть рабочих интервалов.',
  'Working override requires at least one interval.': 'Для рабочего дня нужен хотя бы один интервал.',
  'Weekly schedule must contain each weekday at most once.': 'Каждый день недели можно указать только один раз.',
  'Schedule overrides must contain each date at most once.': 'Каждую дату исключения можно указать только один раз.',
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
  const trimmed = detail.trim().replace(/^Value error,\s*/i, '')
  return DETAIL_RU[trimmed] ?? DETAIL_RU[detail] ?? trimmed
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
            return String((item as { msg: string }).msg).replace(/^Value error,\s*/i, '')
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
