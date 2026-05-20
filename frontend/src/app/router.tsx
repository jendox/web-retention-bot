import { Navigate, Route, Routes, useParams } from 'react-router-dom'

import { AppLayout } from '../components/layout/AppLayout'
import { HomeRedirect } from '../components/routing/HomeRedirect'
import { RequireMasterOutlet } from '../components/routing/RequireMasterOutlet'
import { BookingsPage } from '../pages/BookingsPage'
import { ClientDashboardPage } from '../pages/ClientDashboardPage'
import { ClientDetailPage } from '../pages/ClientDetailPage'
import { ClientsPage } from '../pages/ClientsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { InvitationPage } from '../pages/InvitationPage'
import { LoginPage } from '../pages/LoginPage'
import { PendingVerificationPage } from '../pages/PendingVerificationPage'
import { RegisterPage } from '../pages/RegisterPage'
import { SchedulePage } from '../pages/SchedulePage'
import { ServicesPage } from '../pages/ServicesPage'
import { NotificationsPage } from '../pages/NotificationsPage'
import { SettingsPage } from '../pages/SettingsPage'
import { VerifyEmailPage } from '../pages/VerifyEmailPage'

function InvitationRoute() {
  const { token = '' } = useParams()
  return <InvitationPage key={token} />
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/pending-verification" element={<PendingVerificationPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/invite/:token" element={<InvitationRoute />} />

      <Route element={<AppLayout />}>
        <Route path="/client" element={<ClientDashboardPage />} />
        <Route path="/my-visits" element={<Navigate to="/client" replace />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route element={<RequireMasterOutlet />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/schedule" element={<SchedulePage />} />
          <Route path="/clients" element={<ClientsPage />} />
          <Route path="/clients/:id" element={<ClientDetailPage />} />
          <Route path="/services" element={<ServicesPage />} />
          <Route path="/bookings" element={<BookingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
