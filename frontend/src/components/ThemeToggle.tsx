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
        'fixed bottom-[calc(1rem+env(safe-area-inset-bottom))] right-4 z-50 flex size-10 items-center justify-center rounded-full border text-base leading-none shadow-sm backdrop-blur-sm transition-colors sm:bottom-5 sm:right-5 sm:size-11 sm:text-lg lg:bottom-6 lg:right-6',
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
