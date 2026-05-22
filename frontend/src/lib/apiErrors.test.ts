import { describe, expect, it } from 'vitest'

import { ApiError, getUserFacingError, parseFastApiError } from './apiErrors'

describe('api error localization', () => {
  it('preserves backend error code and localizes by code', () => {
    const payload = parseFastApiError(
      JSON.stringify({
        code: 'auth.invalid_current_password',
        detail: 'Current password is incorrect.',
      }),
    )

    expect(payload).toEqual({
      code: 'auth.invalid_current_password',
      detail: 'Current password is incorrect.',
    })
    expect(getUserFacingError(new ApiError(400, payload.detail, payload.code))).toBe('Текущий пароль указан неверно.')
  })

  it('preserves structured backend context', () => {
    const payload = parseFastApiError(
      JSON.stringify({
        code: 'schedule.booking_conflict',
        detail: 'Schedule changes affect existing bookings.',
        context: {
          conflicts: [
            {
              id: 'booking-1',
              start_at: '2026-06-01T13:00:00+00:00',
              end_at: '2026-06-01T14:00:00+00:00',
            },
          ],
        },
      }),
    )

    expect(payload.context).toEqual({
      conflicts: [
        {
          id: 'booking-1',
          start_at: '2026-06-01T13:00:00+00:00',
          end_at: '2026-06-01T14:00:00+00:00',
        },
      ],
    })
    expect(new ApiError(409, payload.detail, payload.code, payload.context).context).toEqual(payload.context)
    expect(getUserFacingError(new ApiError(409, payload.detail, payload.code, payload.context))).toBe(
      'Нельзя сохранить расписание: есть будущие записи вне новых рабочих часов.',
    )
  })

  it('localizes booking errors by backend code', () => {
    expect(getUserFacingError(new ApiError(409, 'Overlapping booking exists', 'booking.overlapping_exists'))).toBe(
      'На это время уже есть запись.',
    )
    expect(getUserFacingError(new ApiError(403, 'Not linked to this master', 'booking.not_linked_to_master'))).toBe(
      'Вы не связаны с этим мастером.',
    )
  })

  it('falls back to detail localization for old FastAPI errors without code', () => {
    const payload = parseFastApiError(JSON.stringify({ detail: 'Invalid credentials' }))

    expect(payload).toEqual({ detail: 'Invalid credentials' })
    expect(getUserFacingError(new ApiError(401, payload.detail, payload.code))).toBe('Неверный email или пароль.')
  })

  it('keeps validation errors readable', () => {
    const payload = parseFastApiError(
      JSON.stringify({
        detail: [{ msg: 'Value error, Пароль должен содержать хотя бы одну цифру.' }],
      }),
    )

    expect(payload.detail).toBe('Пароль должен содержать хотя бы одну цифру.')
  })
})
