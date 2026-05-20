import { cn } from './forms'

/** Цветная полоса слева у карточки визита (светлая и тёмная тема). */
export const VISIT_ACCENT_BARS = [
  'border-l-teal-600 dark:border-l-teal-400',
  'border-l-amber-500 dark:border-l-amber-400',
  'border-l-rose-400 dark:border-l-rose-400',
  'border-l-sky-500 dark:border-l-sky-400',
] as const

const visitCardShell =
  'rounded-lg border-y border-r border-stone-100 bg-stone-50/80 border-l-4 dark:border-y-stone-800 dark:border-r-stone-800 dark:bg-stone-950/40'

export function visitCardAccentClass(index: number, extra?: string) {
  return cn(visitCardShell, VISIT_ACCENT_BARS[index % VISIT_ACCENT_BARS.length], extra)
}
