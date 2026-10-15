import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

const QUICK_LOGIN = [
  { username: 'admin', password: 'Admin1234', role: 'manager', label: 'Керівник' },
  { username: 'mech_koval', password: 'Mech1234', role: 'mechanic', label: 'Механік' },
  { username: 'driver_ivanov', password: 'Driver1234', role: 'driver', label: 'Водій' }
]

function Login() {
  const navigate = useNavigate()
  const { login, isLoading } = useAuthStore()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!username.trim() || !password) {
      toast.error('Введіть логін та пароль')
      return
    }

    const result = await login(username.trim(), password)

    if (result.success) {
      toast.success('Вхід виконано успішно')
      navigate(`/${result.user.role}`)
    } else {
      toast.error(result.error)
    }
  }

  const handleQuickLogin = async (credentials) => {
    const result = await login(credentials.username, credentials.password)

    if (result.success) {
      toast.success(`Вхід як ${credentials.label}`)
      navigate(`/${result.user.role}`)
    } else {
      toast.error(result.error)
    }
  }

  return (
    <div className="login-form">
      <h2>Вхід в систему</h2>

      <form onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="username">Логін</label>
          <input
            type="text"
            id="username"
            className="form-control"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Введіть логін"
            autoComplete="username"
            autoFocus
          />
        </div>

        <div className="form-field">
          <label htmlFor="password">Пароль</label>
          <input
            type="password"
            id="password"
            className="form-control"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Введіть пароль"
            autoComplete="current-password"
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={isLoading}
        >
          {isLoading ? 'Вхід...' : 'Увійти'}
        </button>
      </form>

      <div className="quick-login">
        <p className="quick-login-title">Швидкий вхід:</p>
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
    </div>
  )
}

export default Login
