import type { ReactNode } from 'react'

type AuthScreenProps = {
  title: string
  subtitle?: ReactNode
  children?: ReactNode
  footer?: ReactNode
}

export function AuthScreen({ title, subtitle, children, footer }: AuthScreenProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-stone-100/70 via-stone-50 to-slate-100/60 dark:from-stone-950 dark:via-stone-950 dark:to-slate-950">
      <div
        className="pointer-events-none absolute -left-40 top-[-10%] h-[32rem] w-[32rem] rounded-full bg-stone-300/15 blur-3xl dark:bg-stone-600/10"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-32 bottom-[-15%] h-[24rem] w-[24rem] rounded-full bg-slate-400/10 blur-3xl dark:bg-slate-500/8"
        aria-hidden
      />
      <div className="relative mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10 sm:px-6">
        <header className="mb-6 text-center sm:mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-stone-900 dark:text-stone-50 sm:text-3xl">{title}</h1>
          {subtitle ? (
            <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-stone-600 dark:text-stone-400">
              {subtitle}
            </p>
          ) : null}
        </header>
        {children != null ? <AuthFormCard>{children}</AuthFormCard> : null}
        {footer ? <div className="mt-6 text-center text-sm text-stone-600 dark:text-stone-400">{footer}</div> : null}
      </div>
    </div>
  )
}

export function AuthFormCard({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-stone-200/80 bg-white/85 p-6 shadow-lg shadow-stone-300/25 ring-1 ring-stone-200/40 backdrop-blur-sm dark:border-stone-700/80 dark:bg-stone-900/80 dark:shadow-black/25 dark:ring-stone-800/60">
      {children}
    </div>
  )
}

export function AuthFieldLabel({ children }: { children: ReactNode }) {
  return <span className="text-sm font-medium text-stone-700 dark:text-stone-300">{children}</span>
}

export function AuthErrorBanner({ message }: { message: string }) {
  return (
    <div
      className="rounded-lg border border-red-200/70 bg-red-50/90 px-3 py-2 text-sm text-red-950/85 dark:border-red-900/45 dark:bg-red-950/35 dark:text-red-100/90"
      role="alert"
    >
      {message}
    </div>
  )
}
