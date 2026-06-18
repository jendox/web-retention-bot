import { Navigate, Route, Routes, useParams } from 'react-router-dom'

import { AppLayout } from '../components/layout/AppLayout'
import { AnalyticsPage } from '../pages/AnalyticsPage'
import { HomeRedirect } from '../components/routing/HomeRedirect'
import { RequireGuestOutlet } from '../components/routing/RequireGuestOutlet'
import { RequireMasterOutlet } from '../components/routing/RequireMasterOutlet'
import { BookingsPage } from '../pages/BookingsPage'
import { ClientCabinetLayout } from '../pages/client/ClientCabinetLayout'
import { ClientHelpPage } from '../pages/client/ClientHelpPage'
import { ClientMastersPage } from '../pages/client/ClientMastersPage'
import { ClientOverviewPage } from '../pages/client/ClientOverviewPage'
import { ClientVisitsPage } from '../pages/client/ClientVisitsPage'
import { ClientDetailPage } from '../pages/ClientDetailPage'
import { ClientsPage } from '../pages/ClientsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { InvitationPage } from '../pages/InvitationPage'
import { ForgotPasswordPage } from '../pages/ForgotPasswordPage'
import { LoginPage } from '../pages/LoginPage'
import { PendingVerificationPage } from '../pages/PendingVerificationPage'
import { RegisterPage } from '../pages/RegisterPage'
import { ResetPasswordPage } from '../pages/ResetPasswordPage'
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
      <Route element={<RequireGuestOutlet />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/pending-verification" element={<PendingVerificationPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/invite/:token" element={<InvitationRoute />} />

      <Route element={<AppLayout />}>
        <Route path="/client">
          <Route element={<ClientCabinetLayout />}>
            <Route index element={<ClientOverviewPage />} />
            <Route path="masters" element={<ClientMastersPage />} />
            <Route path="visits" element={<ClientVisitsPage />} />
            <Route path="help" element={<ClientHelpPage />} />
          </Route>
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="/master" element={<RequireMasterOutlet />}>
          <Route index element={<DashboardPage />} />
          <Route path="schedule" element={<SchedulePage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="clients/:id" element={<ClientDetailPage />} />
          <Route path="services" element={<ServicesPage />} />
          <Route path="bookings" element={<BookingsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
