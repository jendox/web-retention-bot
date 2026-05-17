import { useQuery } from '@tanstack/react-query'

import { ApiError } from '../api/client'
import { masterMeApi } from '../api/masters'

/** Общий запрос профиля мастера: один кэш на приложение, меньше лишних refetch при смене экранов. */
export function useMasterMe(enabled: boolean) {
  return useQuery({
    queryKey: ['master'],
    queryFn: masterMeApi,
    enabled,
    retry: false,
    staleTime: 120_000,
    gcTime: 600_000,
    /** Не дергать повторный запрос при новом наблюдателе, если уже знаем «мастера нет» — иначе UI на миг считает пользователя мастером. */
    refetchOnMount: (query) => {
      const err = query.state.error
      if (query.state.status === 'error' && err instanceof ApiError && err.status === 404) {
        return false
      }
      return true
    },
  })
}
