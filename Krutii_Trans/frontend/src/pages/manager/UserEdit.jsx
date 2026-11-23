import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { usersApi } from '../../api/users'
import toast from 'react-hot-toast'
import DatePicker from 'react-datepicker'
import Loader from '../../components/Loader'
import ConfirmModal from '../../components/ConfirmModal'
import 'react-datepicker/dist/react-datepicker.css'

const ROLES = {
  manager: 'Керівник',
  mechanic: 'Механік',
  driver: 'Водій'
}

function UserEdit() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showResetModal, setShowResetModal] = useState(false)
  const [newPassword, setNewPassword] = useState('')

  const [form, setForm] = useState({
    full_name: '',
    phone: '',
    email: '',
    is_active: true,
    license_number: '',
    license_expiry: null
  })

  useEffect(() => {
    loadUser()
  }, [id])

  const loadUser = async () => {
    try {
      const response = await usersApi.getById(id)
      const userData = response.data.user
      setUser(userData)
      setForm({
        full_name: userData.full_name || '',
        phone: userData.phone || '',
        email: userData.email || '',
        is_active: userData.is_active !== false,
        license_number: userData.license_number || '',
        license_expiry: userData.license_expiry ? new Date(userData.license_expiry) : null
      })
    } catch (error) {
      navigate('/manager/users')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!form.full_name.trim()) {
      toast.error('Введіть ПІБ')
      return
    }

    setSaving(true)
    try {
      const data = {
        ...form,
        license_expiry: form.license_expiry ? form.license_expiry.toISOString().split('T')[0] : null
      }

      await usersApi.update(id, data)
      toast.success('Дані збережено')
      navigate('/manager/users')
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setSaving(false)
    }
  }

  const handleResetPassword = async () => {
    if (!newPassword || newPassword.length < 6) {
      toast.error('Пароль має бути не менше 6 символів')
      return
    }

    try {
      await usersApi.resetPassword(id, newPassword)
      toast.success('Пароль скинуто')
      setShowResetModal(false)
      setNewPassword('')
    } catch (error) {
      // Помилка оброблена в interceptor
    }
  }

  if (loading) {
    return <Loader text="Завантаження..." />
  }

  if (!user) {
    return (
      <div className="page-container">
        <div className="empty-state">Користувача не знайдено</div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <Link to="/manager/users" className="back-link">
        &larr; Назад до списку
      </Link>

      <div className="page-header">
        <h1>Редагування: {user.full_name}</h1>
        <button
          className="btn btn-secondary"
          onClick={() => setShowResetModal(true)}
        >
          Скинути пароль
        </button>
      </div>

      <div className="card">
        <div className="info-grid mb-lg">
          <div className="info-row">
            <span className="label">Логін</span>
            <span className="value">{user.username}</span>
          </div>
          <div className="info-row">
            <span className="label">Роль</span>
            <span className="value">{ROLES[user.role]}</span>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label>
              ПІБ <span className="required">*</span>
            </label>
            <input
              type="text"
              name="full_name"
              className="form-control"
              value={form.full_name}
              onChange={handleChange}
            />
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Телефон</label>
              <input
                type="tel"
                name="phone"
                className="form-control"
                value={form.phone}
                onChange={handleChange}
                placeholder="+380..."
              />
            </div>

            <div className="form-field">
              <label>Email</label>
              <input
                type="email"
                name="email"
                className="form-control"
                value={form.email}
                onChange={handleChange}
              />
            </div>
          </div>

          {user.role === 'driver' && (
            <div className="form-row">
              <div className="form-field">
                <label>Номер посвідчення</label>
                <input
                  type="text"
                  name="license_number"
                  className="form-control"
                  value={form.license_number}
                  onChange={handleChange}
                />
              </div>

              <div className="form-field">
                <label>Дійсне до</label>
                <DatePicker
                  selected={form.license_expiry}
                  onChange={(date) => setForm((prev) => ({ ...prev, license_expiry: date }))}
                  dateFormat="dd.MM.yyyy"
                  className="form-control"
                  placeholderText="Оберіть дату"
                />
              </div>
            </div>
          )}

          <div className="form-field">
            <label className="flex items-center gap-sm">
              <input
                type="checkbox"
                name="is_active"
                checked={form.is_active}
                onChange={handleChange}
              />
              Активний
            </label>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/manager/users')}
            >
              Скасувати
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
            >
              {saving ? 'Збереження...' : 'Зберегти'}
            </button>
          </div>
        </form>
      </div>

      {/* Модалка скидання пароля */}
      {showResetModal && (
        <ConfirmModal
          title="Скидання пароля"
          onClose={() => {
            setShowResetModal(false)
            setNewPassword('')
          }}
          onConfirm={handleResetPassword}
          confirmText="Скинути"
          confirmVariant="danger"
        >
          <div className="form-field">
            <label>Новий пароль</label>
            <input
              type="password"
              className="form-control"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Мінімум 6 символів"
              autoFocus
            />
          </div>
        </ConfirmModal>
      )}
    </div>
  )
}

export default UserEdit
