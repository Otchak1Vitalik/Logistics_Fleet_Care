import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { repairsApi } from '../../api/repairs'
import { vehiclesApi } from '../../api/vehicles'
import { settingsApi } from '../../api/settings'
import FormField from '../../components/FormField'
import toast from 'react-hot-toast'

function MechanicRepairNew() {
  const navigate = useNavigate()
  const location = useLocation()

  const [vehicles, setVehicles] = useState([])
  const [repairTypes, setRepairTypes] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const [formData, setFormData] = useState({
    vehicle_id: location.state?.vehicleId || '',
    fault_id: location.state?.faultId || '',
    repair_type: '',
    description: '',
    scheduled_date: '',
    odometer: '',
    notes: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [vehiclesRes, categoriesRes] = await Promise.all([
        vehiclesApi.getAll(),
        settingsApi.getCategories()
      ])
      setVehicles(
        vehiclesRes.data.vehicles.map((v) => ({
          value: v._id,
          label: `${v.plate_number} - ${v.brand} ${v.model}`
        }))
      )
      setRepairTypes(categoriesRes.data.repair_types)
    } catch (error) {
      // Ігноруємо
    }
  }

  const handleChange = (name, value) => {
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!formData.vehicle_id || !formData.repair_type || !formData.description) {
      toast.error('Заповніть всі обов\'язкові поля')
      return
    }

    setIsLoading(true)

    try {
      // Готуємо дані, прибираємо порожні рядки
      const payload = {
        vehicle_id: formData.vehicle_id,
        repair_type: formData.repair_type,
        description: formData.description
      }
      if (formData.fault_id) payload.fault_id = formData.fault_id
      if (formData.scheduled_date) payload.scheduled_date = formData.scheduled_date
      if (formData.odometer) payload.odometer = parseInt(formData.odometer)
      if (formData.notes) payload.notes = formData.notes

      const response = await repairsApi.create(payload)
      toast.success(`Ремонт ${response.data.repair.number} створено`)
      navigate('/mechanic/repairs')
    } catch (error) {
      // Помилка вже показана
    }

    setIsLoading(false)
  }

  return (
    <div className="page-container page-narrow">
      <div className="page-header">
        <button className="btn btn-text" onClick={() => navigate(-1)}>
          Назад
        </button>
        <h1>Новий ремонт</h1>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <FormField
            label="Транспортний засіб"
            name="vehicle_id"
            type="select"
            value={formData.vehicle_id}
            onChange={handleChange}
            options={vehicles}
            required
          />

          <FormField
            label="Тип робіт"
            name="repair_type"
            type="select"
            value={formData.repair_type}
            onChange={handleChange}
            options={repairTypes}
            required
          />

          <FormField
            label="Опис робіт"
            name="description"
            type="textarea"
            value={formData.description}
            onChange={handleChange}
            placeholder="Опишіть заплановані роботи..."
            rows={4}
            required
          />

          <div className="form-row">
            <FormField
              label="Запланована дата"
              name="scheduled_date"
              type="date"
              value={formData.scheduled_date}
              onChange={handleChange}
            />

            <FormField
              label="Пробіг (км)"
              name="odometer"
              type="number"
              value={formData.odometer}
              onChange={handleChange}
              min={0}
            />
          </div>

          <FormField
            label="Примітки"
            name="notes"
            type="textarea"
            value={formData.notes}
            onChange={handleChange}
            rows={3}
          />

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
              {isLoading ? 'Збереження...' : 'Створити'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default MechanicRepairNew
