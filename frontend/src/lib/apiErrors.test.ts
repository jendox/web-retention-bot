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
