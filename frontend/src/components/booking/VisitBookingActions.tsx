import { IconReschedule, IconTrash } from './bookingActionIcons'

type Props = {
  subjectLabel: string
  onReschedule: () => void
  onCancel: () => void
  cancelDisabled?: boolean
  className?: string
}

export function VisitBookingActions({
  subjectLabel,
  onReschedule,
  onCancel,
  cancelDisabled = false,
  className,
}: Props) {
  return (
    <div className={className ?? 'flex shrink-0 justify-end gap-1 sm:ml-auto'}>
      <button
        type="button"
        onClick={onReschedule}
        className="rounded-lg p-2 text-stone-500 transition hover:bg-teal-50 hover:text-teal-700 dark:text-stone-400 dark:hover:bg-teal-950/40 dark:hover:text-teal-300"
        aria-label={`Перенести запись: ${subjectLabel}`}
        title="Перенести запись"
      >
        <IconReschedule className="h-5 w-5" />
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={cancelDisabled}
        className="rounded-lg p-2 text-stone-400 transition hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50 dark:hover:bg-rose-950/40 dark:hover:text-rose-400"
        aria-label={`Отменить запись: ${subjectLabel}`}
        title="Отменить запись"
      >
        <IconTrash className="h-5 w-5" />
      </button>
    </div>
  )
}
