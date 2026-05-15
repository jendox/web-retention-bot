import { Navigate, Route, Routes } from 'react-router-dom'

import { AppLayout } from '../components/layout/AppLayout'
import { DashboardPage } from '../pages/DashboardPage'
import { InvitationPage } from '../pages/InvitationPage'
import { LoginPage } from '../pages/LoginPage'
import { PendingVerificationPage } from '../pages/PendingVerificationPage'
import { RegisterPage } from '../pages/RegisterPage'
import { VerifyEmailPage } from '../pages/VerifyEmailPage'
import { ServicesPage } from '../pages/ServicesPage'
import { ClientsPage } from '../pages/ClientsPage'
import { BookingsPage } from '../pages/BookingsPage'
import { SchedulePage } from '../pages/SchedulePage'

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/pending-verification" element={<PendingVerificationPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/invite/:token" element={<InvitationPage />} />

      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/services" element={<ServicesPage />} />
        <Route path="/clients" element={<ClientsPage />} />
        <Route path="/bookings" element={<BookingsPage />} />
        <Route path="/schedule" element={<SchedulePage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" />} />
    </Routes>
  )
}
