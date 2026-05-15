import { ApiError, parseFastApiDetail } from '../lib/apiErrors'

const base = import.meta.env.VITE_API_BASE_URL ?? ''

export { ApiError } from '../lib/apiErrors'

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(`${base}${path}`, {
    ...init,
    credentials: 'include',
    headers,
  })
  if (!res.ok) {
    const text = await res.text()
    const detail = parseFastApiDetail(text || `${res.status}`)
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) {
    return undefined as T
  }
  return (await res.json()) as T
}
