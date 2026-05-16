import { z } from 'zod'

const PASSWORD_MIN_LENGTH = 8
const PASSWORD_MAX_LENGTH = 128

export function validatePassword(value: string): true | string {
  const normalized = value.trim()
  if (!normalized) {
    return 'Введите пароль'
  }
  if (normalized.length < PASSWORD_MIN_LENGTH) {
    return `Пароль должен быть не менее ${PASSWORD_MIN_LENGTH} символов`
  }
  if (normalized.length > PASSWORD_MAX_LENGTH) {
    return `Пароль должен быть не более ${PASSWORD_MAX_LENGTH} символов`
  }
  if (!/\p{L}/u.test(normalized)) {
    return 'Пароль должен содержать хотя бы одну букву'
  }
  if (!/\d/u.test(normalized)) {
    return 'Пароль должен содержать хотя бы одну цифру'
  }
  return true
}

export const loginSchema = z.object({
  email: z.string().min(1, 'Введите email').email('Некорректный email'),
  password: z.string().min(1, 'Введите пароль'),
})

export const registerSchema = z.object({
  email: z.string().min(1, 'Введите email').email('Некорректный email'),
  password: z.string().superRefine((value, ctx) => {
    const result = validatePassword(value)
    if (result !== true) {
      ctx.addIssue({ code: 'custom', message: result })
    }
  }),
  master_display_name: z.string().min(2, 'Минимум 2 символа'),
})
