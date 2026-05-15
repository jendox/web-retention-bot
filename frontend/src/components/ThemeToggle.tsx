import { cn } from '../lib/forms'
import { useTheme } from '../lib/theme'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()

  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggle}
      className={cn(
        'fixed right-4 top-4 z-50 flex size-10 items-center justify-center rounded-full border text-base leading-none shadow-sm backdrop-blur-sm transition-colors',
        'border-slate-300/80 bg-white/90 text-slate-800 hover:bg-white',
        'dark:border-slate-600 dark:bg-slate-900/90 dark:text-slate-100 dark:hover:bg-slate-900',
      )}
      aria-pressed={isDark}
      aria-label={isDark ? 'Переключить на дневную тему' : 'Переключить на ночную тему'}
      title={isDark ? 'Светлая тема' : 'Тёмная тема'}
    >
      <span aria-hidden>{isDark ? '☀️' : '🌙'}</span>
    </button>
  )
}
