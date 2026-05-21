import { ApiError, parseFastApiError } from '../lib/apiErrors'

const base = import.meta.env.VITE_API_BASE_URL ?? ''
const csrfCookieName = 'csrf_token'
const csrfHeaderName = 'X-CSRF-Token'
const csrfPath = '/api/auth/csrf'
const csrfErrorDetail = 'CSRF token missing or invalid'
const unsafeMethods = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

let csrfRequest: Promise<string> | null = null

export { ApiError } from '../lib/apiErrors'

function requestMethod(init: RequestInit): string {
  return (init.method ?? 'GET').toUpperCase()
}

function isUnsafeRequest(init: RequestInit): boolean {
  return unsafeMethods.has(requestMethod(init))
}

function readCookie(name: string): string | null {
  const prefix = `${name}=`
  const item = document.cookie.split('; ').find((row) => row.startsWith(prefix))
  return item ? decodeURIComponent(item.slice(prefix.length)) : null
}

async function fetchCsrfToken(): Promise<string> {
  const res = await fetch(`${base}${csrfPath}`, {
    credentials: 'include',
  })
  if (!res.ok) {
    const text = await res.text()
    const error = parseFastApiError(text || `${res.status}`)
    throw new ApiError(res.status, error.detail, error.code)
  }
  const data = (await res.json()) as { csrf_token?: string }
  const token = data.csrf_token ?? readCookie(csrfCookieName)
  if (!token) {
    throw new ApiError(500, 'CSRF token was not issued')
  }
  return token
}

async function ensureCsrfToken(refresh = false): Promise<string> {
  if (!refresh) {
    const token = readCookie(csrfCookieName)
    if (token) {
      return token
    }
  }
  csrfRequest ??= fetchCsrfToken().finally(() => {
    csrfRequest = null
  })
  return csrfRequest
}

async function requestWithHeaders(path: string, init: RequestInit, headers: Headers): Promise<Response> {
  return fetch(`${base}${path}`, {
    ...init,
    credentials: 'include',
    headers,
  })
}

async function parseResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await responseErrorPayload(res)
    throw new ApiError(res.status, error.detail, error.code)
  }
  if (res.status === 204) {
    return undefined as T
  }
  return (await res.json()) as T
}

async function responseErrorPayload(res: Response) {
  const text = await res.text()
  return parseFastApiError(text || `${res.status}`)
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const shouldAttachCsrf = isUnsafeRequest(init) && path !== csrfPath
  if (shouldAttachCsrf && !headers.has(csrfHeaderName)) {
    headers.set(csrfHeaderName, await ensureCsrfToken())
  }

  const res = await requestWithHeaders(path, init, headers)
  if (res.status === 403 && shouldAttachCsrf) {
    const error = await responseErrorPayload(res)
    if (error.detail !== csrfErrorDetail) {
      throw new ApiError(res.status, error.detail, error.code)
    }
    const refreshedHeaders = new Headers(headers)
    refreshedHeaders.set(csrfHeaderName, await ensureCsrfToken(true))
    return parseResponse(await requestWithHeaders(path, init, refreshedHeaders))
  }

  return parseResponse(res)
}
