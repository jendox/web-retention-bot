import { cn } from './forms'

/** Кнопка выбора времени (создание / перенос записи). */
export function bookingSlotButtonClass(selected: boolean): string {
  return cn(
    'rounded-lg border px-2 py-2 text-sm font-medium transition',
    selected
      ? 'border-teal-600 bg-teal-100 text-teal-900 dark:border-teal-500 dark:bg-teal-950/50 dark:text-teal-100'
      : [
          'border-stone-200 bg-white text-stone-700',
          'hover:border-stone-300 hover:bg-stone-100 hover:text-stone-900',
          'dark:border-stone-600 dark:bg-stone-800 dark:text-stone-200',
          'dark:hover:border-stone-500 dark:hover:bg-stone-600 dark:hover:text-stone-50',
        ],
  )
}
