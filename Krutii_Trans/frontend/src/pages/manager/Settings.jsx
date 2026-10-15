import { useEffect, useState } from 'react'
import { settingsApi } from '../../api/settings'
import toast from 'react-hot-toast'
import Loader from '../../components/Loader'
import ConfirmModal from '../../components/ConfirmModal'

function ManagerSettings() {
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showResetModal, setShowResetModal] = useState(false)

  const [form, setForm] = useState({
    company_name: '',
    default_fuel_norm: 25,
    overspend_threshold: 10,
    winter_coefficient: 1.09,
    maintenance_warning_km: 1000,
    maintenance_warning_days: 14,
    maintenance_interval_km: 10000,
    fault_mechanic_hours: 4,
    fault_manager_hours: 24
  })

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const response = await settingsApi.get()
      const data = response.data.settings
      setSettings(data)
      setForm({
        company_name: data.company_name || '',
        default_fuel_norm: data.default_fuel_norm || 25,
        overspend_threshold: data.overspend_threshold || 10,
        winter_coefficient: data.winter_coefficient || 1.09,
        maintenance_warning_km: data.maintenance_warning_km || 1000,
        maintenance_warning_days: data.maintenance_warning_days || 14,
        maintenance_interval_km: data.maintenance_interval_km || 10000,
        fault_mechanic_hours: data.fault_mechanic_hours || 4,
        fault_manager_hours: data.fault_manager_hours || 24
      })
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    const { name, value, type } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'number' ? (value === '' ? '' : Number(value)) : value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    setSaving(true)
    try {
      await settingsApi.update(form)
      toast.success('Налаштування збережено')
      loadSettings()
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    try {
      await settingsApi.reset()
      toast.success('Налаштування скинуто')
      setShowResetModal(false)
      loadSettings()
    } catch (error) {
      // Помилка оброблена в interceptor
    }
  }

  if (loading) {
    return <Loader text="Завантаження..." />
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Налаштування системи</h1>
        <button
          className="btn btn-secondary"
          onClick={() => setShowResetModal(true)}
        >
          Скинути до замовчування
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="card">
          <h3 className="mb-md">Загальні налаштування</h3>
          <div className="form-field">
            <label>Назва компанії</label>
            <input
              type="text"
              name="company_name"
              className="form-control"
              value={form.company_name}
              onChange={handleChange}
            />
          </div>
        </div>

        <div className="card">
          <h3 className="mb-md">Паливні налаштування</h3>
          <div className="form-row">
            <div className="form-field">
              <label>Норма витрат за замовчуванням (л/100км)</label>
              <input
                type="number"
                name="default_fuel_norm"
                className="form-control"
                value={form.default_fuel_norm}
                onChange={handleChange}
                min={1}
                max={100}
                step="0.1"
              />
              <div className="form-hint">
                Використовується при створенні нового транспорту
              </div>
            </div>

            <div className="form-field">
              <label>Поріг перевитрати (%)</label>
              <input
                type="number"
                name="overspend_threshold"
                className="form-control"
                value={form.overspend_threshold}
                onChange={handleChange}
                min={1}
                max={50}
              />
              <div className="form-hint">
                Перевищення норми, що вважається перевитратою
              </div>
            </div>

            <div className="form-field">
              <label>Зимовий коефіцієнт</label>
              <input
                type="number"
                name="winter_coefficient"
                className="form-control"
                value={form.winter_coefficient}
                onChange={handleChange}
                min={1}
                max={1.5}
                step="0.01"
              />
              <div className="form-hint">
                Множник для зимового періоду (листопад-березень)
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="mb-md">Налаштування ТО</h3>
          <div className="form-row">
            <div className="form-field">
              <label>Попередження (км до ТО)</label>
              <input
                type="number"
                name="maintenance_warning_km"
                className="form-control"
                value={form.maintenance_warning_km}
                onChange={handleChange}
                min={100}
              />
            </div>

            <div className="form-field">
              <label>Попередження (днів до ТО)</label>
              <input
                type="number"
                name="maintenance_warning_days"
                className="form-control"
                value={form.maintenance_warning_days}
                onChange={handleChange}
                min={1}
              />
            </div>

            <div className="form-field">
              <label>Інтервал ТО (км)</label>
              <input
                type="number"
                name="maintenance_interval_km"
                className="form-control"
                value={form.maintenance_interval_km}
                onChange={handleChange}
                min={1000}
              />
              <div className="form-hint">
                Пробіг до наступного ТО після завершення
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="mb-md">Ескалація несправностей</h3>
          <div className="form-row">
            <div className="form-field">
              <label>Сповіщення механіку (годин)</label>
              <input
                type="number"
                name="fault_mechanic_hours"
                className="form-control"
                value={form.fault_mechanic_hours}
                onChange={handleChange}
                min={1}
              />
              <div className="form-hint">
                Час без відповіді до сповіщення механіків
              </div>
            </div>

            <div className="form-field">
              <label>Сповіщення керівнику (годин)</label>
              <input
                type="number"
                name="fault_manager_hours"
                className="form-control"
                value={form.fault_manager_hours}
                onChange={handleChange}
                min={1}
              />
              <div className="form-hint">
                Час без відповіді до ескалації керівнику
              </div>
            </div>
          </div>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? 'Збереження...' : 'Зберегти налаштування'}
          </button>
        </div>
      </form>

      {/* Модалка скидання */}
      {showResetModal && (
        <ConfirmModal
          title="Скидання налаштувань"
          onClose={() => setShowResetModal(false)}
          onConfirm={handleReset}
          confirmText="Скинути"
          confirmVariant="danger"
        >
          <p>
            Ви впевнені, що хочете скинути всі налаштування до значень за замовчуванням?
            Цю дію неможливо скасувати.
          </p>
        </ConfirmModal>
      )}
    </div>
  )
}

export default ManagerSettings
