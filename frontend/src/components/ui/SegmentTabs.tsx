import type { ReactNode } from 'react'

import { cn } from '../../lib/forms'

export type SegmentTabItem<T extends string> = {
  value: T
  label: ReactNode
}

type SegmentTabsProps<T extends string> = {
  tabs: readonly SegmentTabItem<T>[]
  value: T
  onChange: (value: T) => void
  className?: string
  /** Растянуть панель на всю ширину; вкладки делят пространство поровну. */
  fullWidth?: boolean
  ariaLabel?: string
}

export function SegmentTabs<T extends string>({
  tabs,
  value,
  onChange,
  className,
  fullWidth = false,
  ariaLabel,
}: SegmentTabsProps<T>) {
  return (
    <div
      role={ariaLabel ? 'tablist' : undefined}
      aria-label={ariaLabel}
      className={cn(
        'inline-flex rounded-xl border border-stone-300 bg-white p-1 shadow-[0_1px_3px_0_rgba(28,25,23,0.08),0_4px_12px_-2px_rgba(28,25,23,0.06)] dark:shadow-sm dark:border-stone-700 dark:bg-stone-900/80',
        fullWidth && 'flex w-full',
        className,
      )}
    >
      {tabs.map((tab) => (
        <button
          key={tab.value}
          type="button"
          role={ariaLabel ? 'tab' : undefined}
          aria-selected={ariaLabel ? value === tab.value : undefined}
          onClick={() => onChange(tab.value)}
          className={cn(
            'rounded-lg px-4 py-2 text-sm font-medium transition',
            fullWidth && 'flex-1 text-center',
            value === tab.value
              ? 'bg-teal-100 text-teal-900 dark:bg-teal-950/60 dark:text-teal-100'
              : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-stone-800 dark:hover:text-stone-50',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
