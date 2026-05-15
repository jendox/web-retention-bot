import { QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'

import { ThemeToggle } from '../components/ThemeToggle'
import { queryClient } from '../lib/query'
import { ThemeProvider } from '../lib/theme'

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        {children}
        <ThemeToggle />
      </ThemeProvider>
    </QueryClientProvider>
  )
}
