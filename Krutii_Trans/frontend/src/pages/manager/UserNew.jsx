import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { usersApi } from '../../api/users'
import toast from 'react-hot-toast'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'

function UserNew() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    username: '',
    password: '',
    full_name: '',
    role: 'driver',
    phone: '',
    email: '',
    license_number: '',
    license_expiry: null
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!form.username.trim() || !form.password || !form.full_name.trim()) {
      toast.error('Заповніть обов\'язкові поля')
      return
    }

    if (form.password.length < 6) {
      toast.error('Пароль має бути не менше 6 символів')
      return
    }

    setLoading(true)
    try {
      const data = {
        ...form,
        license_expiry: form.license_expiry ? form.license_expiry.toISOString().split('T')[0] : null
      }

      await usersApi.create(data)
      toast.success('Користувача створено')
      navigate('/manager/users')
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container">
      <Link to="/manager/users" className="back-link">
        &larr; Назад до списку
      </Link>

      <div className="page-header">
        <h1>Новий користувач</h1>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-field">
              <label>
                Логін <span className="required">*</span>
              </label>
              <input
                type="text"
                name="username"
                className="form-control"
                value={form.username}
                onChange={handleChange}
                placeholder="Латинські букви, цифри, _"
              />
            </div>

            <div className="form-field">
              <label>
                Пароль <span className="required">*</span>
              </label>
              <input
                type="password"
                name="password"
                className="form-control"
                value={form.password}
                onChange={handleChange}
                placeholder="Мінімум 6 символів"
              />
            </div>
          </div>

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

          <div className="form-field">
            <label>
              Роль <span className="required">*</span>
            </label>
            <select
              name="role"
              className="form-control"
              value={form.role}
              onChange={handleChange}
            >
              <option value="driver">Водій</option>
              <option value="mechanic">Механік</option>
              <option value="manager">Керівник</option>
            </select>
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

          {form.role === 'driver' && (
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
              disabled={loading}
            >
              {loading ? 'Збереження...' : 'Створити'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default UserNew
