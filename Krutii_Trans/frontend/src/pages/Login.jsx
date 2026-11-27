import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import { tr, lang, setLang } from '../i18n'
import ContactDock from '../components/ContactDock'
import EmailCodeLogin from '../components/EmailCodeLogin'
import { afterLoginPath } from '../utils/afterLogin'

const QUICK_LOGIN = [
  { username: 'admin', password: 'Admin1234', role: 'manager', label: tr("Керівник") },
  { username: 'mech_koval', password: 'Mech1234', role: 'mechanic', label: tr("Механік") },
  { username: 'driver_ivanov', password: 'Driver1234', role: 'driver', label: tr("Водій") }
]

function LangSwitch() {
  return (
    <div className="login-lang" role="group" aria-label="Мова / Language">
      {[['uk', 'UA'], ['en', 'EN']].map(([code, label]) => (
        <button key={code} type="button" className={lang === code ? 'active' : ''}
          onClick={() => setLang(code)} aria-pressed={lang === code}
          title={code === 'uk' ? 'Українська' : 'English'}>
          {label}
        </button>
      ))}
    </div>
  )
}

function Login() {
  const navigate = useNavigate()
  const { login, isLoading } = useAuthStore()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  // password | email; режим зберігається, щоб перемикання мови (перезавантаження) не скидало екран коду
  const [mode, setModeState] = useState(() => {
    try { return sessionStorage.getItem('krutii-login-mode') === 'email' ? 'email' : 'password' } catch (e) { return 'password' }
  })
  const setMode = (m) => {
    try { sessionStorage.setItem('krutii-login-mode', m === 'email' ? 'email' : 'password') } catch (e) { /* ignore */ }
    setModeState(m)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!username.trim() || !password) {
      toast.error(tr("Введіть логін та пароль"))
      return
    }

    const result = await login(username.trim(), password)

    if (result.success) {
      toast.success(tr("Вхід виконано успішно"))
      navigate(afterLoginPath(result.user.role))
    } else {
      toast.error(result.error)
    }
  }

  const handleQuickLogin = async (credentials) => {
    const result = await login(credentials.username, credentials.password)

    if (result.success) {
      toast.success(tr("Вхід як {0}", credentials.label))
      navigate(afterLoginPath(result.user.role))
    } else {
      toast.error(result.error)
    }
  }

  if (mode === 'email') {
    return (
      <div className="login-form login-flip" key="email">
        <LangSwitch />
        <EmailCodeLogin onBack={() => setMode('password-back')} />
      </div>
    )
  }

  return (
    <div className={`login-form ${mode === 'password-back' ? 'login-flip' : ''}`} key="password">
      <LangSwitch />
      <h2>{tr("Вхід в систему")}</h2>

      <form onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="username">{tr("Логін")}</label>
          <input
            type="text"
            id="username"
            className="form-control"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={tr("Введіть логін")}
            autoComplete="username"
            autoFocus
          />
        </div>

        <div className="form-field">
          <label htmlFor="password">{tr("Пароль")}</label>
          <input
            type="password"
            id="password"
            className="form-control"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={tr("Введіть пароль")}
            autoComplete="current-password"
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={isLoading}
        >
          {isLoading ? tr("Вхід...") : tr("Увійти")}
        </button>
      </form>

      <button type="button" className="login-alt" onClick={() => setMode('email')}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <polyline points="22 6 12 13 2 6" />
        </svg>
        {tr("Увійти за кодом з пошти")}
      </button>

      <div className="quick-login">
        <p className="quick-login-title">{tr("Швидкий вхід:")}</p>
        <div className="quick-login-buttons">
          {QUICK_LOGIN.map((cred) => (
            <button
              key={cred.username}
              type="button"
              className={`btn btn-quick btn-quick-${cred.role}`}
              onClick={() => handleQuickLogin(cred)}
              disabled={isLoading}
            >
              {cred.label}
            </button>
          ))}
        </div>
      </div>

      <ContactDock />
    </div>
  )
}

export default Login
