const STORAGE_KEY = 'retention_client_shell_v1'

export type StoredShellRole = {
  email: string
  /** client — в аккаунте нет профиля мастера (или мы это уже надёжно зафиксировали). */
  mode: 'client' | 'master'
}

/** Прочитать сохранённый режим оболочки только если совпадает email сессии. */
export function readPersistedShellRole(email: string): 'client' | 'master' | null {
  if (!email || typeof sessionStorage === 'undefined') {
    return null
  }
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw) as StoredShellRole
    if (parsed.email !== email || (parsed.mode !== 'client' && parsed.mode !== 'master')) {
      return null
    }
    return parsed.mode
  } catch {
    return null
  }
}

export function persistClientShellRole(email: string, mode: 'client' | 'master') {
  if (!email || typeof sessionStorage === 'undefined') {
    return
  }
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ email, mode } satisfies StoredShellRole))
}

export function clearClientShellRole() {
  if (typeof sessionStorage === 'undefined') {
    return
  }
  sessionStorage.removeItem(STORAGE_KEY)
}
