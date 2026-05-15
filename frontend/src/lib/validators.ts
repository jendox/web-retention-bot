import { z } from 'zod'

export const loginSchema = z.object({
  email: z.string().min(1, 'Введите email').email('Некорректный email'),
  password: z.string().min(1, 'Введите пароль'),
})

export const registerSchema = z.object({
  email: z.string().min(1, 'Введите email').email('Некорректный email'),
  password: z.string().min(8, 'Пароль — не менее 8 символов'),
  master_display_name: z.string().min(2, 'Минимум 2 символа'),
})
