import { cn } from './forms'
import { surfaceListItemClass } from './surface'

/** Цветная полоса слева у карточки визита (светлая и тёмная тема). */
export const VISIT_ACCENT_BARS = [
  'border-l-teal-600 dark:border-l-teal-400',
  'border-l-amber-500 dark:border-l-amber-400',
  'border-l-rose-400 dark:border-l-rose-400',
  'border-l-sky-500 dark:border-l-sky-400',
] as const

const visitCardShell = cn(surfaceListItemClass, 'border-l-4')

export function visitCardAccentClass(index: number, extra?: string) {
  return cn(visitCardShell, VISIT_ACCENT_BARS[index % VISIT_ACCENT_BARS.length], extra)
}
