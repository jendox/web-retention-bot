import { apiFetch } from './client'

export type AuthUser = {
  id: string
  email: string
  email_verified: boolean
  client_display_name?: string | null
  client_phone?: string | null
}

export type RegisterAccepted = {
  id: string
  email: string
  email_verified: false
}

export async function registerApi(body: {
  email: string
  password: string
  master_display_name: string
}) {
  return apiFetch<RegisterAccepted>('/api/auth/register', { method: 'POST', body: JSON.stringify(body) })
}

export async function registerClientApi(body: { email: string; password: string }) {
  return apiFetch<RegisterAccepted>('/api/auth/register-client', { method: 'POST', body: JSON.stringify(body) })
}

export async function verifyEmailApi(body: { token: string }) {
  return apiFetch<AuthUser>('/api/auth/verify-email', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function loginApi(body: { email: string; password: string }) {
  return apiFetch<AuthUser>('/api/auth/login', { method: 'POST', body: JSON.stringify(body) })
}

export async function meApi() {
  return apiFetch<AuthUser>('/api/auth/me')
}

export async function logoutApi() {
  await apiFetch('/api/auth/logout', { method: 'POST' })
}

export async function forgotPasswordApi(body: { email: string }) {
  await apiFetch('/api/auth/forgot-password', { method: 'POST', body: JSON.stringify(body) })
}

export async function resetPasswordApi(body: { token: string; new_password: string }) {
  await apiFetch('/api/auth/reset-password', { method: 'POST', body: JSON.stringify(body) })
}

export async function changePasswordApi(body: { current_password: string; new_password: string }) {
  await apiFetch('/api/auth/change-password', { method: 'POST', body: JSON.stringify(body) })
}
