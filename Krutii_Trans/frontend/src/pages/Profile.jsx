import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import Loader from '../components/Loader'
import { formatDate, formatDateTime, formatNumber } from '../utils/formatters'
import { tr } from '../i18n'

const ROLE_NAMES = { manager: tr("Керівник"), mechanic: tr("Механік"), driver: tr("Водій") }
const ROLE_COLORS = { manager: '#4f46e5', mechanic: '#ea580c', driver: '#059669' }

function Stat({ value, label, tone }) {
  return (
    <div className={`stat-card ${tone || ''}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

// Сторінка «Мій профіль»: контакти користувача і короткий зріз роботи залежно від ролі
function Profile() {
  const navigate = useNavigate()
  const { updateUser } = useAuthStore()
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState({ phone: '', email: '' })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const load = async () => {
    try {
      const res = await authApi.me()
      setUser(res.data.user)
      setProfile(res.data.profile)
      setForm({ phone: res.data.user.phone || '', email: res.data.user.email || '' })
    } catch (e) { /* обробляється в interceptor */ }
  }

  useEffect(() => { load() }, [])

  const save = async (e) => {
    e.preventDefault()
    setErrors({})
    setSaving(true)
    try {
      const res = await authApi.updateMe({ phone: form.phone, email: form.email })
      setUser(res.data.user)
      updateUser(res.data.user)
      toast.success(tr("Контакти оновлено"))
    } catch (err) {
      setErrors(err.response?.data?.details || {})
    }
    setSaving(false)
  }

  if (!user || !profile) return <Loader text={tr("Завантаження...")} />
  const s = profile.stats || {}
  const changed = (form.phone || '') !== (user.phone || '') || (form.email || '') !== (user.email || '')

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{tr("Мій профіль")}</h1>
      </div>

      <div className="card profile-head">
        <div className="profile-avatar" style={{ background: ROLE_COLORS[user.role] }}>
          {user.full_name?.charAt(0) || 'U'}
        </div>
        <div>
          <h2>{user.full_name}</h2>
          <div className="text-muted">
            {ROLE_NAMES[user.role]} · {tr("логін")} <b>{user.username}</b>
          </div>
          <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
            {tr("Останній вхід")}: {user.last_login ? formatDateTime(user.last_login) : '—'}
          </div>
        </div>
      </div>

      {user.role === 'driver' && profile.license_warning && (
        <div className="profile-alert">
          {profile.license_days_left <= 0
            ? tr("Термін дії посвідчення водія минув. Зверніться до керівника.")
            : tr("Посвідчення водія спливає через {0} дн. ({1}).", profile.license_days_left, formatDate(profile.license_expiry))}
        </div>
      )}

      <h3 className="profile-section-title">
        {user.role === 'manager' ? tr("Зріз автопарку") : tr("Моя робота за {0} днів", profile.period_days)}
      </h3>
      {user.role === 'driver' && (
        <div className="dashboard-stats">
          <Stat value={s.waybills} label={tr("Завершених путівок")} />
          <Stat value={tr("{0} км", formatNumber(s.distance))} label={tr("Пробіг")} />
          <Stat value={tr("{0} л", formatNumber(s.fuel_used))} label={tr("Пального")} />
          <Stat value={s.faults_reported} label={tr("Повідомлено несправностей")} />
        </div>
      )}
      {user.role === 'mechanic' && (
        <div className="dashboard-stats">
          <Stat value={s.repairs_completed} label={tr("Завершено ремонтів")} />
          <Stat value={s.repairs_in_progress} label={tr("Зараз у роботі")} tone={s.repairs_in_progress ? 'warning' : ''} />
          <Stat value={s.repairs_planned} label={tr("Заплановано")} />
          <Stat value={s.avg_repair_hours !== null ? tr("{0} год", s.avg_repair_hours) : '—'} label={tr("Середній час ремонту")} />
          <Stat value={s.faults_acknowledged} label={tr("Прийнято несправностей")} />
        </div>
      )}
      {user.role === 'manager' && (
        <div className="dashboard-stats">
          <Stat value={`${s.vehicles_active} / ${s.vehicles_total}`} label={tr("Авто в експлуатації")} />
          <Stat value={s.drivers_active} label={tr("Активних водіїв")} />
          <Stat value={s.open_faults} label={tr("Відкритих несправностей")} tone={s.open_faults ? 'warning' : ''} />
          <Stat value={s.waybills_issued} label={tr("Видано путівок за {0} днів", profile.period_days)} />
        </div>
      )}

      <div className="detail-grid">
        <div className="card">
          <h3>{tr("Контактні дані")}</h3>
          <form onSubmit={save} className="mt-md" noValidate>
            <div className="form-field">
              <label htmlFor="profile-phone">{tr("Телефон")}</label>
              <input id="profile-phone" className={`form-control ${errors.phone ? 'is-invalid' : ''}`} value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+380 67 123 45 67" />
              {errors.phone && <div className="form-error">{tr(errors.phone[0])}</div>}
            </div>
            <div className="form-field">
              <label htmlFor="profile-email">{tr("Email")}</label>
              <input id="profile-email" type="email" className={`form-control ${errors.email ? 'is-invalid' : ''}`} value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="name@company.com" />
              {errors.email && <div className="form-error">{tr(errors.email[0])}</div>}
            </div>
            <button type="submit" className="btn btn-primary" disabled={saving || !changed}>
              {saving ? tr("Збереження...") : tr("Зберегти")}
            </button>
          </form>
        </div>

        <div className="card">
          <h3>{tr("Обліковий запис")}</h3>
          <dl className="info-list mt-md">
            <div className="info-item"><dt>{tr("Роль")}</dt><dd>{ROLE_NAMES[user.role]}</dd></div>
            <div className="info-item"><dt>{tr("Логін")}</dt><dd>{user.username}</dd></div>
            {user.role === 'driver' && (
              <>
                <div className="info-item"><dt>{tr("Номер посвідчення")}</dt><dd>{user.license_number || '—'}</dd></div>
                <div className="info-item">
                  <dt>{tr("Посвідчення дійсне до")}</dt>
                  <dd className={profile.license_warning ? 'text-danger font-bold' : ''}>{formatDate(profile.license_expiry)}</dd>
                </div>
              </>
            )}
            <div className="info-item"><dt>{tr("Зареєстровано")}</dt><dd>{formatDate(user.created_at)}</dd></div>
          </dl>
          <p className="text-muted mt-md" style={{ fontSize: '0.8125rem' }}>
            {tr("ПІБ, роль і дані посвідчення змінює керівник.")}
          </p>
          <button className="btn btn-secondary mt-md" onClick={() => navigate('/change-password')}>{tr("Змінити пароль")}</button>
          {user.role === 'manager' && (
            <button className="btn btn-text mt-md" onClick={() => navigate('/manager/settings')}>{tr("Налаштування системи")}</button>
          )}
        </div>
      </div>
    </div>
  )
}

export default Profile
