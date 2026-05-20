import { useEffect } from 'react'
import { Outlet, useNavigate, useOutletContext, useSearchParams } from 'react-router-dom'

import type { AppShellOutletContext } from '../../app/appShellOutletContext'
import { ClientCabinetAlerts } from '../../components/client/ClientCabinetAlerts'
import { ClientCabinetProvider } from '../../components/client/ClientCabinetContext'

function LegacyTabRedirect() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  useEffect(() => {
    const tab = searchParams.get('tab')
    if (!tab) {
      return
    }

    if (tab === 'notifications') {
      navigate('/client/notifications', { replace: true })
      return
    }

    const next = new URLSearchParams()
    if (tab === 'visits') {
      const scope = searchParams.get('visit_scope')
      const page = searchParams.get('visit_page')
      const pageSize = searchParams.get('visit_page_size')
      if (scope) {
        next.set('visit_scope', scope)
      }
      if (page) {
        next.set('visit_page', page)
      }
      if (pageSize) {
        next.set('visit_page_size', pageSize)
      }
      const qs = next.toString()
      navigate(qs ? `/client/visits?${qs}` : '/client/visits', { replace: true })
      return
    }

    if (tab === 'masters') {
      navigate('/client/masters', { replace: true })
      return
    }

    if (tab === 'help') {
      navigate('/client/help', { replace: true })
      return
    }

    navigate('/client', { replace: true })
  }, [navigate, searchParams])

  return null
}

export function ClientCabinetLayout() {
  const shellContext = useOutletContext<AppShellOutletContext>()

  return (
    <ClientCabinetProvider>
      <LegacyTabRedirect />
      <div className="space-y-6">
        <ClientCabinetAlerts />
        <Outlet context={shellContext} />
      </div>
    </ClientCabinetProvider>
  )
}
