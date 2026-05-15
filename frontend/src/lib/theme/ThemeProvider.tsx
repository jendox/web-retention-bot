import type { PropsWithChildren } from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { THEME_STORAGE_KEY, ThemeContext, type Theme, type ThemeContextValue } from './context'

function readStoredTheme(): Theme | null {
  if (typeof window === 'undefined') {
    return null
  }
  const raw = localStorage.getItem(THEME_STORAGE_KEY)
  if (raw === 'light' || raw === 'dark') {
    return raw
  }
  return null
}

function systemTheme(): Theme {
  if (typeof window === 'undefined') {
    return 'dark'
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function resolveTheme(): Theme {
  return readStoredTheme() ?? systemTheme()
}

function applyDom(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const [theme, setThemeState] = useState<Theme>(resolveTheme)

  useEffect(() => {
    applyDom(theme)
  }, [theme])

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onPref = () => {
      if (readStoredTheme()) {
        return
      }
      const next: Theme = mq.matches ? 'dark' : 'light'
      setThemeState(next)
      applyDom(next)
    }
    mq.addEventListener('change', onPref)
    return () => mq.removeEventListener('change', onPref)
  }, [])

  const setTheme = useCallback((t: Theme) => {
    localStorage.setItem(THEME_STORAGE_KEY, t)
    setThemeState(t)
    applyDom(t)
  }, [])

  const toggle = useCallback(() => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
  }, [theme, setTheme])

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, setTheme, toggle }),
    [theme, setTheme, toggle],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
