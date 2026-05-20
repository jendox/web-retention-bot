import { cn } from './forms'

/** Raised panel on page background — stronger edge in light theme; dark unchanged. */
export const surfaceCardClass =
  'rounded-xl border border-stone-300 bg-white shadow-[0_1px_3px_0_rgba(28,25,23,0.08),0_4px_12px_-2px_rgba(28,25,23,0.06)] dark:border-stone-700 dark:bg-stone-900/80 dark:shadow-sm'

export const surfacePanelClass =
  'rounded-2xl border border-stone-300 bg-white shadow-[0_1px_3px_0_rgba(28,25,23,0.08),0_4px_12px_-2px_rgba(28,25,23,0.06)] dark:border-stone-700 dark:bg-stone-900/80 dark:shadow-sm'

/** Nested block inside a card (form sections, grouped fields). */
export const surfaceInsetClass =
  'rounded-lg border border-stone-200 bg-stone-50 dark:border-stone-700 dark:bg-stone-950/40'

/** Standalone row in a list (visit, notification) on page or inside a panel. */
export const surfaceListItemClass =
  'rounded-xl border border-stone-300 bg-white shadow-[0_1px_2px_0_rgba(28,25,23,0.06)] dark:border-stone-700 dark:bg-stone-900/80 dark:shadow-none'

export function surfaceCard(extra?: string) {
  return cn(surfaceCardClass, extra)
}

export function surfacePanel(extra?: string) {
  return cn(surfacePanelClass, extra)
}

export function surfaceInset(extra?: string) {
  return cn(surfaceInsetClass, extra)
}

export function surfacePanelOverflow(extra?: string) {
  return cn(surfacePanelClass, 'overflow-hidden', extra)
}
