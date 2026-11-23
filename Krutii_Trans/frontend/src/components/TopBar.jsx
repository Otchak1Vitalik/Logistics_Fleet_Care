import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import AlertBell from './AlertBell'
import { useThemeStore } from '../store/themeStore'
import { tr, lang, setLang } from '../i18n'

const ROLE_NAMES = {
  manager: tr("Керiвник"),
  mechanic: tr("Механiк"),
  driver: tr("Водiй")
}

const ROLE_COLORS = {
  manager: '#4f46e5',
  mechanic: '#ea580c',
  driver: '#059669'
}

function TopBar() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()

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
        <button
          className="btn-topbar btn-lang"
          onClick={() => setLang(lang === 'en' ? 'uk' : 'en')}
          title={lang === 'en' ? 'Українська' : 'English'}
          aria-label={lang === 'en' ? 'Перейти на українську' : 'Switch to English'}
        >
          {lang === 'en' ? 'UA' : 'EN'}
        </button>

        <button
          className="btn-topbar"
          onClick={toggleTheme}
          title={theme === 'dark' ? tr("Світла тема") : tr("Темна тема")}
          aria-label={theme === 'dark' ? tr("Увімкнути світлу тему") : tr("Увімкнути темну тему")}
        >
          {theme === 'dark' ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="5" />
              <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
              <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          )}
        </button>

        <AlertBell />

        <button
          type="button"
          className="topbar-user"
          onClick={() => navigate(`/${user?.role}/profile`)}
          title={tr("Мій профіль")}
        >
          <div className="user-avatar" style={{ background: ROLE_COLORS[user?.role] }}>
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <div className="user-info">
            <span className="user-name">{user?.full_name}</span>
            <span className="user-role">{ROLE_NAMES[user?.role]}</span>
          </div>
        </button>

        <div className="topbar-divider"></div>

        <button
          className="btn-topbar"
          onClick={() => navigate('/change-password')}
          title={tr("Змiнити пароль")}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </button>

        <button
          className="btn-topbar btn-logout"
          onClick={handleLogout}
          title={tr("Вийти")}
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
