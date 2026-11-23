import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import AlertBell from './AlertBell'

const ROLE_NAMES = {
  manager: 'Керiвник',
  mechanic: 'Механiк',
  driver: 'Водiй'
}

const ROLE_COLORS = {
  manager: '#4f46e5',
  mechanic: '#ea580c',
  driver: '#059669'
}

function TopBar() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="topbar-brand">
          <span className="brand-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="1" y="3" width="15" height="13" />
              <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
              <circle cx="5.5" cy="18.5" r="2.5" />
              <circle cx="18.5" cy="18.5" r="2.5" />
            </svg>
          </span>
          <span className="brand-text">KRUTII TRANS</span>
        </div>
      </div>

      <div className="topbar-right">
        <AlertBell />

        <div className="topbar-user">
          <div className="user-avatar" style={{ background: ROLE_COLORS[user?.role] }}>
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <div className="user-info">
            <span className="user-name">{user?.full_name}</span>
            <span className="user-role">{ROLE_NAMES[user?.role]}</span>
          </div>
        </div>

        <div className="topbar-divider"></div>

        <button
          className="btn-topbar"
          onClick={() => navigate('/change-password')}
          title="Змiнити пароль"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </button>

        <button
          className="btn-topbar btn-logout"
          onClick={handleLogout}
          title="Вийти"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </header>
  )
}

export default TopBar
