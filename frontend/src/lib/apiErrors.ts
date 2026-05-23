/** Сообщения об ошибках API для UI и парсинг тел FastAPI. */

/** Стабильные коды бэкенда → текст для пользователя (рус.). */
const CODE_RU: Record<string, string> = {
  'auth.user_already_exists': 'Этот email уже зарегистрирован.',
  'auth.invalid_credentials': 'Неверный email или пароль.',
  'auth.email_not_verified': 'Сначала подтвердите email по ссылке из письма.',
  'auth.inactive_user': 'Аккаунт отключён. Обратитесь в поддержку.',
  'auth.invalid_current_password': 'Текущий пароль указан неверно.',
  'auth.invalid_email_verification_token': 'Ссылка недействительна или устарела. Запросите новое письмо.',
  'auth.invalid_password_reset_token': 'Ссылка для сброса пароля недействительна или устарела.',
  'invitations.not_found': 'Приглашение не найдено.',
  'invitations.revoked': 'Приглашение отозвано.',
  'invitations.expired': 'Срок действия приглашения истёк.',
  'invitations.already_accepted': 'Приглашение уже принято.',
  'invitations.client_not_found': 'Клиент не найден.',
  'invitations.client_mismatch': 'Приглашение не соответствует карточке клиента.',
  'invitations.client_already_linked': 'Эта карточка уже привязана к другому аккаунту.',
  'invitations.already_linked_to_master': 'Вы уже связаны с этим мастером.',
  'invitations.own_account': 'Нельзя принять собственное приглашение.',
  'invitations.client_login_already_linked': 'У клиента уже есть вход в приложение.',
  'invitations.active_already_exists': 'Для этого клиента уже есть активное приглашение.',
  'master_profile.empty_patch': 'Нечего сохранить: не переданы поля.',
  'master_profile.no_fields_to_update': 'Нечего сохранить: переданные поля не меняют профиль.',
  'services.not_found': 'Услуга не найдена.',
  'services.has_bookings': 'Нельзя удалить услугу: есть записи, связанные с ней.',
  'services.empty_patch': 'Нечего сохранить: не переданы поля.',
  'services.no_fields_to_update': 'Нечего сохранить: переданные поля не меняют услугу.',
  'clients.not_found': 'Клиент не найден.',
  'clients.profile_not_found': 'Профиль клиента не найден. Примите приглашение мастера.',
  'clients.empty_patch': 'Нечего сохранить: не переданы поля.',
  'clients.email_locked': 'Email подтвержден аккаунтом клиента и не редактируется.',
  'clients.name_locked': 'Имя подтверждено аккаунтом клиента и не редактируется.',
  'clients.has_bookings': 'Нельзя удалить клиента: есть записи.',
  'clients.has_invitation': 'Нельзя удалить клиента: есть привязка по приглашению.',
  'clients.master_link_not_found': 'Вы не связаны с этим мастером.',
  'notifications.not_found': 'Уведомление не найдено.',
  'notification_settings.unknown_topic': 'Неизвестная настройка уведомлений.',
  'notification_settings.unknown_channel': 'Неизвестный канал уведомлений.',
  'notification_settings.channel_unavailable': 'Канал уведомлений недоступен.',
  'notification_settings.channel_not_connectable': 'Этот канал пока нельзя подключить.',
  'notification_settings.channel_contact_required': 'Укажите контакт для канала уведомлений.',
  'notification_settings.channel_not_linked': 'Сначала подключите канал, затем включите уведомления.',
  'notification_settings.email_required': 'Email нельзя отключить.',
  'notification_settings.unsupported_provider': 'Провайдер мессенджера не поддерживается.',
  'schedule.booking_conflict': 'Нельзя сохранить расписание: есть будущие записи вне новых рабочих часов.',
  'availability.master_not_found': 'Профиль мастера не найден.',
  'availability.service_not_found': 'Услуга не найдена.',
  'availability.date_in_past': 'Нельзя выбрать прошедшую дату.',
  'availability.date_outside_horizon': 'Дата слишком далеко. Выберите ближайший доступный день.',
  'booking.service_not_found': 'Услуга не найдена.',
  'booking.master_not_found': 'Профиль мастера не найден.',
  'booking.client_link_not_found': 'Связь с клиентом не найдена.',
  'booking.unknown_client_linkage': 'Клиент не найден в вашей базе.',
  'booking.not_linked_to_master': 'Вы не связаны с этим мастером.',
  'booking.requested_slot_unavailable': 'Это время уже недоступно. Выберите другой слот.',
  'booking.overlapping_exists': 'На это время уже есть запись.',
  'booking.not_found': 'Запись не найдена.',
  'booking.active_not_found': 'Активная запись не найдена.',
  'booking.attendance_not_pending': 'Явка уже отмечена или запись не ждёт подтверждения.',
}

/** Сообщения бэкенда (англ.) → текст для пользователя (рус.). */
const DETAIL_RU: Record<string, string> = {
  'User already exists.': 'Этот email уже зарегистрирован.',
  'Invalid credentials': 'Неверный email или пароль.',
  'Email address is not verified yet': 'Сначала подтвердите email по ссылке из письма.',
  'Account is disabled': 'Аккаунт отключён. Обратитесь в поддержку.',
  'Current password is incorrect.': 'Текущий пароль указан неверно.',
  'Invalid or expired verification link': 'Ссылка недействительна или устарела. Запросите новое письмо.',
  'Invalid password reset token.': 'Ссылка для сброса пароля недействительна или устарела.',
  'Not authenticated': 'Требуется вход.',
  'Email address is not verified': 'Сначала подтвердите email.',
  'CSRF token missing or invalid': 'Сессия устарела. Повторите действие.',
  'CSRF token was not issued': 'Не удалось подготовить запрос. Обновите страницу.',
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
  /** Стабильный машинный код ошибки, если бэкенд его вернул. */
  readonly code?: string
  /** Дополнительные структурированные данные ошибки. */
  readonly context?: Record<string, unknown>

  constructor(status: number, detail: string, code?: string, context?: Record<string, unknown>) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.code = code
    this.context = context
  }
}

export type ApiErrorPayload = {
  detail: string
  code?: string
  context?: Record<string, unknown>
}

function apiErrorPayload(detail: string, code?: string, context?: Record<string, unknown>): ApiErrorPayload {
  return {
    detail,
    ...(code ? { code } : {}),
    ...(context ? { context } : {}),
  }
}

export function translateApiCode(code: string | undefined): string | null {
  return code ? (CODE_RU[code] ?? null) : null
}

export function translateApiDetail(detail: string): string {
  const trimmed = detail.trim().replace(/^Value error,\s*/i, '')
  return DETAIL_RU[trimmed] ?? DETAIL_RU[detail] ?? trimmed
}

/** Разбор тела ответа FastAPI: новый {code, detail}, строка или validation errors. */
export function parseFastApiError(rawBody: string): ApiErrorPayload {
  try {
    const j = JSON.parse(rawBody) as { code?: unknown; detail?: unknown; context?: unknown }
    const context =
      j.context && typeof j.context === 'object' && !Array.isArray(j.context)
        ? (j.context as Record<string, unknown>)
        : undefined
    if (typeof j.detail === 'string') {
      return apiErrorPayload(j.detail, typeof j.code === 'string' ? j.code : undefined, context)
    }
    if (Array.isArray(j.detail)) {
      return apiErrorPayload(
        j.detail
          .map((item: unknown) => {
            if (item && typeof item === 'object' && 'msg' in item) {
              return String((item as { msg: string }).msg).replace(/^Value error,\s*/i, '')
            }
            return JSON.stringify(item)
          })
          .join(' '),
        typeof j.code === 'string' ? j.code : undefined,
        context,
      )
    }
  } catch {
    /* не JSON */
  }
  return { detail: rawBody }
}

/** @deprecated Use parseFastApiError to preserve backend error codes. */
export function parseFastApiDetail(rawBody: string): string {
  return parseFastApiError(rawBody).detail
}

export function getUserFacingError(err: unknown): string {
  if (err instanceof ApiError) {
    return translateApiCode(err.code) ?? translateApiDetail(err.detail)
  }
  if (err instanceof Error) {
    return err.message
  }
  return 'Что-то пошло не так. Попробуйте ещё раз.'
}
