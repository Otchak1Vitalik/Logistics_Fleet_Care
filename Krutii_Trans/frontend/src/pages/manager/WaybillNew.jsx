import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { waybillsApi } from '../../api/waybills'
import { vehiclesApi } from '../../api/vehicles'
import { usersApi } from '../../api/users'
import toast from 'react-hot-toast'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'

function WaybillNew() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [vehicles, setVehicles] = useState([])
  const [drivers, setDrivers] = useState([])

  const [form, setForm] = useState({
    vehicle_id: '',
    driver_id: '',
    issue_date: new Date(),
    valid_from: new Date(),
    valid_until: new Date(Date.now() + 24 * 60 * 60 * 1000), // +1 день
    route_from: '',
    route_to: '',
    route_description: '',
    odometer_start: '',
    fuel_issued: '',
    notes: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [vehiclesRes, driversRes] = await Promise.all([
        vehiclesApi.getAll({ status: 'active' }),
        usersApi.getDrivers()
      ])
      setVehicles(vehiclesRes.data.vehicles)
      setDrivers(driversRes.data.drivers)
    } catch (error) {
      // Помилка оброблена в interceptor
    }
  }

  const handleChange = (e) => {
    const { name, value, type } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'number' ? (value === '' ? '' : Number(value)) : value
    }))
  }

  const handleVehicleChange = (e) => {
    const vehicleId = e.target.value
    const vehicle = vehicles.find((v) => v._id === vehicleId)

    setForm((prev) => ({
      ...prev,
      vehicle_id: vehicleId,
      odometer_start: vehicle?.odometer || ''
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!form.vehicle_id || !form.driver_id) {
      toast.error('Оберіть транспорт та водія')
      return
    }

    if (form.valid_until <= form.valid_from) {
      toast.error('Дата закінчення має бути пізніше дати початку')
      return
    }

    setLoading(true)
    try {
      const data = {
        ...form,
        issue_date: form.issue_date.toISOString().split('T')[0],
        valid_from: form.valid_from.toISOString(),
        valid_until: form.valid_until.toISOString()
      }

      // Видаляємо порожні поля
      Object.keys(data).forEach((key) => {
        if (data[key] === '' || data[key] === null || data[key] === undefined) {
          delete data[key]
        }
      })

      const response = await waybillsApi.create(data)
      toast.success(`Путівку ${response.data.waybill.number} створено`)
      navigate('/manager/waybills')
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const selectedVehicle = vehicles.find((v) => v._id === form.vehicle_id)

  return (
    <div className="page-container">
      <Link to="/manager/waybills" className="back-link">
        &larr; Назад до списку
      </Link>

      <div className="page-header">
        <h1>Нова путівка</h1>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <h3 className="mb-md">Транспорт та водій</h3>

          <div className="form-row">
            <div className="form-field">
              <label>
                Транспорт <span className="required">*</span>
              </label>
              <select
                name="vehicle_id"
                className="form-control"
                value={form.vehicle_id}
                onChange={handleVehicleChange}
              >
                <option value="">Оберіть транспорт</option>
                {vehicles.map((v) => (
                  <option key={v._id} value={v._id}>
                    {v.plate_number} - {v.brand} {v.model}
                  </option>
                ))}
              </select>
              {selectedVehicle && (
                <div className="form-hint">
                  Пробіг: {selectedVehicle.odometer?.toLocaleString()} км |
                  Норма: {selectedVehicle.fuel_norm} л/100км
                </div>
              )}
            </div>

            <div className="form-field">
              <label>
                Водій <span className="required">*</span>
              </label>
              <select
                name="driver_id"
                className="form-control"
                value={form.driver_id}
                onChange={handleChange}
              >
                <option value="">Оберіть водія</option>
                {drivers.map((d) => (
                  <option key={d._id} value={d._id}>
                    {d.full_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <h3 className="mb-md mt-lg">Термін дії</h3>

          <div className="form-row">
            <div className="form-field">
              <label>Дата видачі</label>
              <DatePicker
                selected={form.issue_date}
                onChange={(date) => setForm((prev) => ({ ...prev, issue_date: date }))}
                dateFormat="dd.MM.yyyy"
                className="form-control"
              />
            </div>

            <div className="form-field">
              <label>Дійсна з</label>
              <DatePicker
                selected={form.valid_from}
                onChange={(date) => setForm((prev) => ({ ...prev, valid_from: date }))}
                showTimeSelect
                timeFormat="HH:mm"
                timeIntervals={15}
                dateFormat="dd.MM.yyyy HH:mm"
                className="form-control"
              />
            </div>

            <div className="form-field">
              <label>Дійсна до</label>
              <DatePicker
                selected={form.valid_until}
                onChange={(date) => setForm((prev) => ({ ...prev, valid_until: date }))}
                showTimeSelect
                timeFormat="HH:mm"
                timeIntervals={15}
                dateFormat="dd.MM.yyyy HH:mm"
                className="form-control"
                minDate={form.valid_from}
              />
            </div>
          </div>

          <h3 className="mb-md mt-lg">Маршрут</h3>

          <div className="form-row">
            <div className="form-field">
              <label>Пункт відправлення</label>
              <input
                type="text"
                name="route_from"
                className="form-control"
                value={form.route_from}
                onChange={handleChange}
                placeholder="Київ, склад"
              />
            </div>

            <div className="form-field">
              <label>Пункт призначення</label>
              <input
                type="text"
                name="route_to"
                className="form-control"
                value={form.route_to}
                onChange={handleChange}
                placeholder="Одеса, порт"
              />
            </div>
          </div>

          <div className="form-field">
            <label>Опис маршруту</label>
            <textarea
              name="route_description"
              className="form-control"
              value={form.route_description}
              onChange={handleChange}
              rows={3}
              placeholder="Додаткові деталі маршруту..."
            />
          </div>

          <h3 className="mb-md mt-lg">Пробіг та пальне</h3>

          <div className="form-row">
            <div className="form-field">
              <label>Початковий пробіг (км)</label>
              <input
                type="number"
                name="odometer_start"
                className="form-control"
                value={form.odometer_start}
                onChange={handleChange}
                min={0}
              />
            </div>

            <div className="form-field">
              <label>Видано пального (л)</label>
              <input
                type="number"
                name="fuel_issued"
                className="form-control"
                value={form.fuel_issued}
                onChange={handleChange}
                min={0}
                step="0.1"
              />
            </div>
          </div>

          <div className="form-field">
            <label>Примітки</label>
            <textarea
              name="notes"
              className="form-control"
              value={form.notes}
              onChange={handleChange}
              rows={2}
            />
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/manager/waybills')}
            >
              Скасувати
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? 'Створення...' : 'Видати путівку'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default WaybillNew
