export const NO_SHOW_WARNING_THRESHOLD = 2

export type ClientBookingStats = {
  no_show_count: number
  completed_count: number
}

export function shouldWarnFrequentNoShows(stats: ClientBookingStats | undefined): boolean {
  return (stats?.no_show_count ?? 0) >= NO_SHOW_WARNING_THRESHOLD
}

/** «1 неявка», «2 неявки», «5 неявок». */
export function formatNoShowCount(count: number): string {
  const n = Math.abs(Math.trunc(count))
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) {
    return `${n} неявка`
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) {
    return `${n} неявки`
  }
  return `${n} неявок`
}

export function formatClientVisitStats(stats: ClientBookingStats): string {
  const parts: string[] = []
  if (stats.completed_count > 0) {
    parts.push(`визитов: ${stats.completed_count}`)
  }
  if (stats.no_show_count > 0) {
    parts.push(formatNoShowCount(stats.no_show_count))
  }
  return parts.length ? parts.join(' · ') : 'нет завершённых визитов'
}
