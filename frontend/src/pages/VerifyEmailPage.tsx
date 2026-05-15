import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { verifyEmailApi } from '../api/auth'
import { queryClient } from '../lib/query'

export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token')
  const [error, setError] = useState<string | null>(null)
  const started = useRef(false)

  useEffect(() => {
    if (!token || started.current) {
      return
    }
    started.current = true
    const run = async () => {
      try {
        await verifyEmailApi({ token: decodeURIComponent(token) })
        await queryClient.invalidateQueries({ queryKey: ['me'] })
        navigate('/dashboard')
      } catch (err) {
        setError(`${err}`)
      }
    }
    void run()
  }, [token, navigate])

  if (!token) {
    return (
      <div className="mx-auto max-w-lg px-6 py-14 pr-14">
        <h1 className="text-xl font-semibold">Некорректная ссылка</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">В этой странице нет параметра token.</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-lg px-6 py-14 pr-14">
        <h1 className="text-xl font-semibold">Ссылка не сработала</h1>
        <p className="mt-2 text-rose-600 dark:text-rose-300">{error}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-lg px-6 py-14 pr-14">
      <p className="text-slate-600 dark:text-slate-400">Подтверждаем email…</p>
    </div>
  )
}
