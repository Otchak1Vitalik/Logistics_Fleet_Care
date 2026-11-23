import { useEffect, useState, useRef } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'

// Layouts
import AuthLayout from './layouts/AuthLayout'
import DriverLayout from './layouts/DriverLayout'
import MechanicLayout from './layouts/MechanicLayout'
import ManagerLayout from './layouts/ManagerLayout'

// Auth pages
import Login from './pages/Login'
import ChangePassword from './pages/ChangePassword'

// Driver pages
import DriverDashboard from './pages/driver/Dashboard'
import DriverWaybills from './pages/driver/Waybills'
import DriverWaybillDetail from './pages/driver/WaybillDetail'
import DriverFaults from './pages/driver/Faults'
import DriverFaultNew from './pages/driver/FaultNew'
import DriverFaultDetail from './pages/driver/FaultDetail'
import DriverFuel from './pages/driver/Fuel'

// Mechanic pages
import MechanicDashboard from './pages/mechanic/Dashboard'
import MechanicFleet from './pages/mechanic/Fleet'
import MechanicVehicleDetail from './pages/mechanic/VehicleDetail'
import MechanicFaults from './pages/mechanic/Faults'
import MechanicFaultDetail from './pages/mechanic/FaultDetail'
import MechanicRepairs from './pages/mechanic/Repairs'
import MechanicRepairNew from './pages/mechanic/RepairNew'
import MechanicRepairDetail from './pages/mechanic/RepairDetail'
import MechanicAlerts from './pages/mechanic/Alerts'

// Manager pages
import ManagerDashboard from './pages/manager/Dashboard'
import ManagerUsers from './pages/manager/Users'
import ManagerUserNew from './pages/manager/UserNew'
import ManagerUserEdit from './pages/manager/UserEdit'
import ManagerVehicles from './pages/manager/Vehicles'
import ManagerVehicleNew from './pages/manager/VehicleNew'
import ManagerVehicleDetail from './pages/manager/VehicleDetail'
import ManagerWaybills from './pages/manager/Waybills'
import ManagerWaybillNew from './pages/manager/WaybillNew'
import ManagerWaybillDetail from './pages/manager/WaybillDetail'
import ManagerFuel from './pages/manager/Fuel'
import ManagerFuelInvoiceNew from './pages/manager/FuelInvoiceNew'
import ManagerReports from './pages/manager/Reports'
import ManagerFuelPlan from './pages/manager/FuelPlan'
import ManagerAlerts from './pages/manager/Alerts'
import ManagerSettings from './pages/manager/Settings'

// Компонент завантаження
function LoadingScreen() {
  return (
    <div className="loader-container" style={{ minHeight: '100vh' }}>
      <div className="loader"></div>
      <p className="loader-text">Завантаження...</p>
    </div>
  )
}

function ProtectedRoute({ children, allowedRoles }) {
  const { user, isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    const roleRoutes = {
      driver: '/driver',
      mechanic: '/mechanic',
      manager: '/manager'
    }
    return <Navigate to={roleRoutes[user?.role] || '/login'} replace />
  }

  return children
}

function App() {
  const { isAuthenticated, user, _hasHydrated, checkAuth, logout } = useAuthStore()
  const [isVerifying, setIsVerifying] = useState(true)
  const hasVerified = useRef(false)

  // Перевіряємо авторизацію при завантаженні (один раз)
  useEffect(() => {
    const verifyAuth = async () => {
      if (!_hasHydrated || hasVerified.current) return
      hasVerified.current = true

      // Якщо є дані в localStorage, перевіряємо чи валідна сесія
      const state = useAuthStore.getState()
      if (state.isAuthenticated && state.user) {
        const isValid = await checkAuth()
        if (!isValid) {
          await logout()
        }
      }
      setIsVerifying(false)
    }

    verifyAuth()
  }, [_hasHydrated, checkAuth, logout])

  // Чекаємо на гідратацію та перевірку
  if (!_hasHydrated || isVerifying) {
    return <LoadingScreen />
  }

  return (
    <Routes>
      {/* Auth routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
      </Route>

      {/* Change password - доступно всім авторизованим */}
      <Route
        path="/change-password"
        element={
          <ProtectedRoute>
            <ChangePassword />
          </ProtectedRoute>
        }
      />

      {/* Driver routes */}
      <Route
        path="/driver"
        element={
          <ProtectedRoute allowedRoles={['driver']}>
            <DriverLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DriverDashboard />} />
        <Route path="waybills" element={<DriverWaybills />} />
        <Route path="waybills/:id" element={<DriverWaybillDetail />} />
        <Route path="faults" element={<DriverFaults />} />
        <Route path="faults/new" element={<DriverFaultNew />} />
        <Route path="faults/:id" element={<DriverFaultDetail />} />
        <Route path="fuel" element={<DriverFuel />} />
      </Route>

      {/* Mechanic routes */}
      <Route
        path="/mechanic"
        element={
          <ProtectedRoute allowedRoles={['mechanic']}>
            <MechanicLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<MechanicDashboard />} />
        <Route path="fleet" element={<MechanicFleet />} />
        <Route path="fleet/:id" element={<MechanicVehicleDetail />} />
        <Route path="faults" element={<MechanicFaults />} />
        <Route path="faults/:id" element={<MechanicFaultDetail />} />
        <Route path="repairs" element={<MechanicRepairs />} />
        <Route path="repairs/new" element={<MechanicRepairNew />} />
        <Route path="repairs/:id" element={<MechanicRepairDetail />} />
        <Route path="alerts" element={<MechanicAlerts />} />
      </Route>

      {/* Manager routes */}
      <Route
        path="/manager"
        element={
          <ProtectedRoute allowedRoles={['manager']}>
            <ManagerLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<ManagerDashboard />} />
        <Route path="users" element={<ManagerUsers />} />
        <Route path="users/new" element={<ManagerUserNew />} />
        <Route path="users/:id" element={<ManagerUserEdit />} />
        <Route path="vehicles" element={<ManagerVehicles />} />
        <Route path="vehicles/new" element={<ManagerVehicleNew />} />
        <Route path="vehicles/:id" element={<ManagerVehicleDetail />} />
        <Route path="waybills" element={<ManagerWaybills />} />
        <Route path="waybills/new" element={<ManagerWaybillNew />} />
        <Route path="waybills/:id" element={<ManagerWaybillDetail />} />
        <Route path="fuel" element={<ManagerFuel />} />
        <Route path="fuel/new" element={<ManagerFuelInvoiceNew />} />
        <Route path="reports" element={<ManagerReports />} />
        <Route path="fuel-plan" element={<ManagerFuelPlan />} />
        <Route path="alerts" element={<ManagerAlerts />} />
        <Route path="settings" element={<ManagerSettings />} />
      </Route>

      {/* Root redirect */}
      <Route
        path="/"
        element={
          isAuthenticated && user?.role ? (
            <Navigate to={`/${user.role}`} replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      {/* 404 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
