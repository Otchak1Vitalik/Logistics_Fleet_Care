import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

function ChangePassword() {
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error('Заповніть всі поля')
      return
    }

    if (newPassword.length < 6) {
      toast.error('Новий пароль має бути не менше 6 символів')
      return
    }

    if (newPassword !== confirmPassword) {
      toast.error('Паролі не співпадають')
      return
    }

    setIsLoading(true)

    try {
      await authApi.changePassword(currentPassword, newPassword)
      toast.success('Пароль успішно змінено')
      navigate(`/${user?.role || ''}`)
    } catch (error) {
      // Помилка вже показана через interceptor
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="page-container page-narrow">
      <div className="page-header">
        <h1>Зміна пароля</h1>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="currentPassword">Поточний пароль</label>
            <input
              type="password"
              id="currentPassword"
              className="form-control"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="newPassword">Новий пароль</label>
            <input
              type="password"
              id="newPassword"
              className="form-control"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={6}
            />
            <span className="field-hint">
              Мінімум 6 символів, має містити велику літеру та цифру
            </span>
          </div>

          <div className="form-field">
            <label htmlFor="confirmPassword">Підтвердження пароля</label>
            <input
              type="password"
              id="confirmPassword"
              className="form-control"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate(-1)}
            >
              Скасувати
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading}
            >
              {isLoading ? 'Збереження...' : 'Змінити пароль'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ChangePassword
