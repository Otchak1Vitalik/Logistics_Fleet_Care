import { Outlet, Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { tr } from '../i18n'

function AuthLayout() {
  const { isAuthenticated, user, _hasHydrated } = useAuthStore()

  // Чекаємо на завершення гідратації
  if (!_hasHydrated) {
    return (
      <div className="auth-layout">
        <div className="auth-container">
          <div className="auth-logo">
            <h1>KRUTII TRANS</h1>
            <p>{tr("Завантаження...")}</p>
          </div>
        </div>
      </div>
    )
  }

  // Якщо вже авторизований і є роль - перенаправляємо
  if (isAuthenticated && user?.role) {
    return <Navigate to={`/${user.role}`} replace />
  }

  return (
    <div className="auth-layout">
      <div className="auth-container">
        <div className="auth-logo">
          <h1>KRUTII TRANS</h1>
          <p>{tr("Система управління автопарком")}</p>
        </div>
        <Outlet />
      </div>
    </div>
  )
}

export default AuthLayout
