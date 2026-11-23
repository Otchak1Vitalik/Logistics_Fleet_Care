import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { vehiclesApi } from '../../api/vehicles'
import toast from 'react-hot-toast'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'

// Марки та моделі вантажівок
const TRUCK_DATA = {
  'MAN': ['TGX', 'TGS', 'TGM', 'TGL', 'TGA'],
  'Volvo': ['FH', 'FM', 'FMX', 'FE', 'FL'],
  'DAF': ['XF', 'CF', 'LF', 'XG', 'XG+'],
  'Mercedes-Benz': ['Actros', 'Arocs', 'Atego', 'Axor', 'Antos'],
  'Scania': ['R', 'S', 'G', 'P', 'L'],
  'Iveco': ['S-Way', 'X-Way', 'Eurocargo', 'Daily', 'Stralis'],
  'Renault': ['T', 'C', 'K', 'D', 'Master'],
  'КАМАЗ': ['5490', '65207', '6520', '43118', '65115'],
  'МАЗ': ['5440', '6430', '6501', '5340', '4371']
}

const BRANDS = Object.keys(TRUCK_DATA)

// Генератор років (останні 20 років)
const currentYear = new Date().getFullYear()
const YEARS = Array.from({ length: 21 }, (_, i) => currentYear - i)

// Генератор українського номерного знаку
const generatePlateNumber = () => {
  const regions = ['AA', 'AB', 'AC', 'AE', 'AH', 'AI', 'AK', 'AM', 'AO', 'AP', 'AT', 'AX',
    'BA', 'BB', 'BC', 'BE', 'BH', 'BI', 'BK', 'BM', 'BO', 'BP', 'BT', 'BX',
    'CA', 'CB', 'CE', 'CH', 'CI', 'CK', 'CM', 'CO']
  const letters = 'ABCEHIKMOPTX'
  const region = regions[Math.floor(Math.random() * regions.length)]
  const num = String(Math.floor(Math.random() * 9000) + 1000)
  const suffix = letters[Math.floor(Math.random() * letters.length)] +
    letters[Math.floor(Math.random() * letters.length)]
  return `${region} ${num} ${suffix}`
}

// Генератор VIN коду
const generateVIN = () => {
  const chars = 'ABCDEFGHJKLMNPRSTUVWXYZ0123456789'
  let vin = ''
  for (let i = 0; i < 17; i++) {
    vin += chars[Math.floor(Math.random() * chars.length)]
  }
  return vin
}

function VehicleNew() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    plate_number: '',
    brand: '',
    model: '',
    year: currentYear,
    vin: '',
    fuel_type: 'diesel',
    fuel_norm: 25,
    tank_capacity: '',
    odometer: 0,
    next_maintenance_km: '',
    next_maintenance_date: null,
    inspection_expiry: null,
    insurance_policy: '',
    insurance_expiry: null
  })

  const handleChange = (e) => {
    const { name, value, type } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'number' ? (value === '' ? '' : Number(value)) : value
    }))
  }

  const handleBrandChange = (e) => {
    const brand = e.target.value
    setForm((prev) => ({
      ...prev,
      brand,
      model: '' // Скидаємо модель при зміні марки
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!form.plate_number.trim() || !form.brand.trim() || !form.model.trim()) {
      toast.error('Заповніть обов\'язкові поля')
      return
    }

    setLoading(true)
    try {
      const data = {
        ...form,
        next_maintenance_date: form.next_maintenance_date?.toISOString().split('T')[0],
        inspection_expiry: form.inspection_expiry?.toISOString().split('T')[0],
        insurance_expiry: form.insurance_expiry?.toISOString().split('T')[0]
      }

      // Видаляємо порожні поля
      Object.keys(data).forEach((key) => {
        if (data[key] === '' || data[key] === null || data[key] === undefined) {
          delete data[key]
        }
      })

      await vehiclesApi.create(data)
      toast.success('Транспорт додано')
      navigate('/manager/vehicles')
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const models = form.brand ? TRUCK_DATA[form.brand] || [] : []

  return (
    <div className="page-container">
      <Link to="/manager/vehicles" className="back-link">
        &larr; Назад до списку
      </Link>

      <div className="page-header">
        <h1>Новий транспорт</h1>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <h3 className="mb-md">Основна iнформацiя</h3>

          <div className="form-row">
            <div className="form-field">
              <label>
                Номерний знак <span className="required">*</span>
              </label>
              <div className="input-with-button">
                <input
                  type="text"
                  name="plate_number"
                  className="form-control"
                  value={form.plate_number}
                  onChange={handleChange}
                  placeholder="AA 0000 AA"
                />
                <button
                  type="button"
                  className="btn btn-icon"
                  onClick={() => setForm((prev) => ({ ...prev, plate_number: generatePlateNumber() }))}
                  title="Згенерувати"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="form-field">
              <label>VIN код</label>
              <div className="input-with-button">
                <input
                  type="text"
                  name="vin"
                  className="form-control"
                  value={form.vin}
                  onChange={handleChange}
                  placeholder="17 символiв"
                  maxLength={17}
                />
                <button
                  type="button"
                  className="btn btn-icon"
                  onClick={() => setForm((prev) => ({ ...prev, vin: generateVIN() }))}
                  title="Згенерувати"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>
                Марка <span className="required">*</span>
              </label>
              <select
                name="brand"
                className="form-control"
                value={form.brand}
                onChange={handleBrandChange}
              >
                <option value="">Оберiть марку</option>
                {BRANDS.map((brand) => (
                  <option key={brand} value={brand}>{brand}</option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label>
                Модель <span className="required">*</span>
              </label>
              <select
                name="model"
                className="form-control"
                value={form.model}
                onChange={handleChange}
                disabled={!form.brand}
              >
                <option value="">
                  {form.brand ? 'Оберiть модель' : 'Спочатку оберiть марку'}
                </option>
                {models.map((model) => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label>Рiк випуску</label>
              <select
                name="year"
                className="form-control"
                value={form.year}
                onChange={handleChange}
              >
                {YEARS.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
          </div>

          <h3 className="mb-md mt-lg">Паливнi характеристики</h3>

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
              <label>Норма витрат (л/100км)</label>
              <input
                type="number"
                name="fuel_norm"
                className="form-control"
                value={form.fuel_norm}
                onChange={handleChange}
                step="0.1"
                min={1}
                max={100}
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
                min={10}
              />
            </div>
          </div>

          <h3 className="mb-md mt-lg">Пробiг та ТО</h3>

          <div className="form-row">
            <div className="form-field">
              <label>Поточний пробiг (км)</label>
              <input
                type="number"
                name="odometer"
                className="form-control"
                value={form.odometer}
                onChange={handleChange}
                min={0}
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
                min={0}
              />
            </div>

            <div className="form-field">
              <label>Наступне ТО (дата)</label>
              <DatePicker
                selected={form.next_maintenance_date}
                onChange={(date) => setForm((prev) => ({ ...prev, next_maintenance_date: date }))}
                dateFormat="dd.MM.yyyy"
                className="form-control"
                placeholderText="Оберiть дату"
              />
            </div>
          </div>

          <h3 className="mb-md mt-lg">Документи</h3>

          <div className="form-row">
            <div className="form-field">
              <label>Техогляд дiйсний до</label>
              <DatePicker
                selected={form.inspection_expiry}
                onChange={(date) => setForm((prev) => ({ ...prev, inspection_expiry: date }))}
                dateFormat="dd.MM.yyyy"
                className="form-control"
                placeholderText="Оберiть дату"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Страховий полiс</label>
              <input
                type="text"
                name="insurance_policy"
                className="form-control"
                value={form.insurance_policy}
                onChange={handleChange}
              />
            </div>

            <div className="form-field">
              <label>Страховка дiйсна до</label>
              <DatePicker
                selected={form.insurance_expiry}
                onChange={(date) => setForm((prev) => ({ ...prev, insurance_expiry: date }))}
                dateFormat="dd.MM.yyyy"
                className="form-control"
                placeholderText="Оберiть дату"
              />
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/manager/vehicles')}
            >
              Скасувати
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? 'Збереження...' : 'Додати'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default VehicleNew
