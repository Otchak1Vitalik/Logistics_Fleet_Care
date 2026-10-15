import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { vehiclesApi } from '../../api/vehicles'
import toast from 'react-hot-toast'
import DatePicker from 'react-datepicker'
import Loader from '../../components/Loader'
import StatusBadge from '../../components/StatusBadge'
import ConfirmModal from '../../components/ConfirmModal'
import { formatDate, formatOdometer } from '../../utils/formatters'
import 'react-datepicker/dist/react-datepicker.css'

const STATUSES = {
  active: 'Активний',
  repair: 'В ремонті',
  inspection: 'На огляді',
  decommissioned: 'Списано'
}

const FUEL_TYPES = {
  diesel: 'Дизель',
  petrol: 'Бензин',
  gas: 'Газ'
}

function VehicleDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [vehicle, setVehicle] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [showStatusModal, setShowStatusModal] = useState(false)
  const [newStatus, setNewStatus] = useState('')

  const [form, setForm] = useState({})

  useEffect(() => {
    loadVehicle()
  }, [id])

  const loadVehicle = async () => {
    try {
      const response = await vehiclesApi.getById(id)
      const data = response.data.vehicle
      setVehicle(data)
      setForm({
        plate_number: data.plate_number || '',
        brand: data.brand || '',
        model: data.model || '',
        year: data.year || '',
        vin: data.vin || '',
        fuel_type: data.fuel_type || 'diesel',
        fuel_norm: data.fuel_norm || 25,
        tank_capacity: data.tank_capacity || '',
        odometer: data.odometer || 0,
        next_maintenance_km: data.next_maintenance_km || '',
        next_maintenance_date: data.next_maintenance_date ? new Date(data.next_maintenance_date) : null,
        inspection_expiry: data.inspection_expiry ? new Date(data.inspection_expiry) : null,
        insurance_policy: data.insurance_policy || '',
        insurance_expiry: data.insurance_expiry ? new Date(data.insurance_expiry) : null
      })
    } catch (error) {
      navigate('/manager/vehicles')
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

  const handleSave = async () => {
    if (!form.plate_number.trim() || !form.brand.trim() || !form.model.trim()) {
      toast.error('Заповніть обов\'язкові поля')
      return
    }

    setSaving(true)
    try {
      const data = {
        ...form,
        next_maintenance_date: form.next_maintenance_date?.toISOString().split('T')[0],
        inspection_expiry: form.inspection_expiry?.toISOString().split('T')[0],
        insurance_expiry: form.insurance_expiry?.toISOString().split('T')[0]
      }

      await vehiclesApi.update(id, data)
      toast.success('Дані збережено')
      setIsEditing(false)
      loadVehicle()
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async () => {
    try {
      await vehiclesApi.update(id, { status: newStatus })
      toast.success('Статус змінено')
      setShowStatusModal(false)
      loadVehicle()
    } catch (error) {
      // Помилка оброблена в interceptor
    }
  }

  if (loading) {
    return <Loader text="Завантаження..." />
  }

  if (!vehicle) {
    return (
      <div className="page-container">
        <div className="empty-state">Транспорт не знайдено</div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <Link to="/manager/vehicles" className="back-link">
        &larr; Назад до списку
      </Link>

      <div className="detail-header">
        <div className="detail-title">
          <h1>{vehicle.plate_number}</h1>
          <StatusBadge status={vehicle.status} />
        </div>
        <div className="detail-actions">
          {isEditing ? (
            <>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setIsEditing(false)
                  loadVehicle()
                }}
              >
                Скасувати
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Збереження...' : 'Зберегти'}
              </button>
            </>
          ) : (
            <>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setNewStatus(vehicle.status)
                  setShowStatusModal(true)
                }}
              >
                Змінити статус
              </button>
              <button
                className="btn btn-primary"
                onClick={() => setIsEditing(true)}
              >
                Редагувати
              </button>
            </>
          )}
        </div>
      </div>

      <div className="card">
        {isEditing ? (
          /* Форма редагування */
          <form>
            <h3 className="mb-md">Основна інформація</h3>

            <div className="form-row">
              <div className="form-field">
                <label>Номерний знак</label>
                <input
                  type="text"
                  name="plate_number"
                  className="form-control"
                  value={form.plate_number}
                  onChange={handleChange}
                />
              </div>

              <div className="form-field">
                <label>VIN код</label>
                <input
                  type="text"
                  name="vin"
                  className="form-control"
                  value={form.vin}
                  onChange={handleChange}
                  maxLength={17}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-field">
                <label>Марка</label>
                <input
                  type="text"
                  name="brand"
                  className="form-control"
                  value={form.brand}
                  onChange={handleChange}
                />
              </div>

              <div className="form-field">
                <label>Модель</label>
                <input
                  type="text"
                  name="model"
                  className="form-control"
                  value={form.model}
                  onChange={handleChange}
                />
              </div>

              <div className="form-field">
                <label>Рік</label>
                <input
                  type="number"
                  name="year"
                  className="form-control"
                  value={form.year}
                  onChange={handleChange}
                />
              </div>
            </div>

            <h3 className="mb-md mt-lg">Паливні характеристики</h3>

            <div className="form-row">
              <div className="form-field">
                <label>Тип пального</label>
                <select
                  name="fuel_type"
                  className="form-control"
                  value={form.fuel_type}
                  onChange={handleChange}
                >
                  <option value="diesel">Дизель</option>
                  <option value="petrol">Бензин</option>
                  <option value="gas">Газ</option>
                </select>
              </div>

              <div className="form-field">
                <label>Норма (л/100км)</label>
                <input
                  type="number"
                  name="fuel_norm"
                  className="form-control"
                  value={form.fuel_norm}
                  onChange={handleChange}
                  step="0.1"
                />
              </div>

              <div className="form-field">
                <label>Об'єм баку (л)</label>
                <input
                  type="number"
                  name="tank_capacity"
                  className="form-control"
                  value={form.tank_capacity}
                  onChange={handleChange}
                />
              </div>
            </div>

            <h3 className="mb-md mt-lg">Пробіг та ТО</h3>

            <div className="form-row">
              <div className="form-field">
                <label>Пробіг (км)</label>
                <input
                  type="number"
                  name="odometer"
                  className="form-control"
                  value={form.odometer}
                  onChange={handleChange}
                />
              </div>

              <div className="form-field">
                <label>Наступне ТО (км)</label>
                <input
                  type="number"
                  name="next_maintenance_km"
                  className="form-control"
                  value={form.next_maintenance_km}
                  onChange={handleChange}
                />
              </div>

              <div className="form-field">
                <label>Наступне ТО (дата)</label>
                <DatePicker
                  selected={form.next_maintenance_date}
                  onChange={(date) => setForm((prev) => ({ ...prev, next_maintenance_date: date }))}
                  dateFormat="dd.MM.yyyy"
                  className="form-control"
                />
              </div>
            </div>

            <h3 className="mb-md mt-lg">Документи</h3>

            <div className="form-row">
              <div className="form-field">
                <label>Техогляд до</label>
                <DatePicker
                  selected={form.inspection_expiry}
                  onChange={(date) => setForm((prev) => ({ ...prev, inspection_expiry: date }))}
                  dateFormat="dd.MM.yyyy"
                  className="form-control"
                />
              </div>

              <div className="form-field">
                <label>Страховий поліс</label>
                <input
                  type="text"
                  name="insurance_policy"
                  className="form-control"
                  value={form.insurance_policy}
                  onChange={handleChange}
                />
              </div>

              <div className="form-field">
                <label>Страховка до</label>
                <DatePicker
                  selected={form.insurance_expiry}
                  onChange={(date) => setForm((prev) => ({ ...prev, insurance_expiry: date }))}
                  dateFormat="dd.MM.yyyy"
                  className="form-control"
                />
              </div>
            </div>
          </form>
        ) : (
          /* Перегляд */
          <>
            <div className="detail-section">
              <h3>Основна інформація</h3>
              <div className="info-grid">
                <div className="info-row">
                  <span className="label">Марка</span>
                  <span className="value">{vehicle.brand}</span>
                </div>
                <div className="info-row">
                  <span className="label">Модель</span>
                  <span className="value">{vehicle.model}</span>
                </div>
                <div className="info-row">
                  <span className="label">Рік випуску</span>
                  <span className="value">{vehicle.year || '-'}</span>
                </div>
                <div className="info-row">
                  <span className="label">VIN код</span>
                  <span className="value">{vehicle.vin || '-'}</span>
                </div>
              </div>
            </div>

            <div className="detail-section">
              <h3>Паливні характеристики</h3>
              <div className="info-grid">
                <div className="info-row">
                  <span className="label">Тип пального</span>
                  <span className="value">{FUEL_TYPES[vehicle.fuel_type]}</span>
                </div>
                <div className="info-row">
                  <span className="label">Норма витрат</span>
                  <span className="value">{vehicle.fuel_norm} л/100км</span>
                </div>
                <div className="info-row">
                  <span className="label">Об'єм баку</span>
                  <span className="value">{vehicle.tank_capacity ? `${vehicle.tank_capacity} л` : '-'}</span>
                </div>
              </div>
            </div>

            <div className="detail-section">
              <h3>Пробіг та ТО</h3>
              <div className="info-grid">
                <div className="info-row">
                  <span className="label">Поточний пробіг</span>
                  <span className="value">{formatOdometer(vehicle.odometer)}</span>
                </div>
                <div className="info-row">
                  <span className="label">Останнє ТО (км)</span>
                  <span className="value">{formatOdometer(vehicle.last_maintenance_km)}</span>
                </div>
                <div className="info-row">
                  <span className="label">Останнє ТО (дата)</span>
                  <span className="value">{formatDate(vehicle.last_maintenance_date)}</span>
                </div>
                <div className="info-row">
                  <span className="label">Наступне ТО (км)</span>
                  <span className="value">{vehicle.next_maintenance_km ? formatOdometer(vehicle.next_maintenance_km) : '-'}</span>
                </div>
                <div className="info-row">
                  <span className="label">Наступне ТО (дата)</span>
                  <span className="value">{formatDate(vehicle.next_maintenance_date)}</span>
                </div>
              </div>
            </div>

            <div className="detail-section">
              <h3>Документи</h3>
              <div className="info-grid">
                <div className="info-row">
                  <span className="label">Техогляд дійсний до</span>
                  <span className="value">{formatDate(vehicle.inspection_expiry)}</span>
                </div>
                <div className="info-row">
                  <span className="label">Страховий поліс</span>
                  <span className="value">{vehicle.insurance_policy || '-'}</span>
                </div>
                <div className="info-row">
                  <span className="label">Страховка дійсна до</span>
                  <span className="value">{formatDate(vehicle.insurance_expiry)}</span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Модалка зміни статусу */}
      {showStatusModal && (
        <ConfirmModal
          title="Зміна статусу"
          onClose={() => setShowStatusModal(false)}
          onConfirm={handleStatusChange}
          confirmText="Змінити"
        >
          <div className="form-field">
            <label>Новий статус</label>
            <select
              className="form-control"
              value={newStatus}
              onChange={(e) => setNewStatus(e.target.value)}
            >
              {Object.entries(STATUSES).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>
        </ConfirmModal>
      )}
    </div>
  )
}

export default VehicleDetail
