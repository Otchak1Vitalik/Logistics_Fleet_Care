import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { faultsApi } from '../../api/faults'
import { vehiclesApi } from '../../api/vehicles'
import { settingsApi } from '../../api/settings'
import FormField from '../../components/FormField'
import toast from 'react-hot-toast'

function DriverFaultNew() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)

  const [vehicles, setVehicles] = useState([])
  const [categories, setCategories] = useState([])
  const [severities, setSeverities] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isDataLoading, setIsDataLoading] = useState(true)

  // Фото для завантаження
  const [photos, setPhotos] = useState([]) // { type: 'file' | 'url', data: File | string, preview: string }
  const [photoUrl, setPhotoUrl] = useState('')

  const [formData, setFormData] = useState({
    vehicle_id: '',
    category: '',
    severity: '',
    description: '',
    odometer: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setIsDataLoading(true)
    try {
      const [vehiclesRes, categoriesRes] = await Promise.all([
        vehiclesApi.getAll(),
        settingsApi.getCategories()
      ])

      const vehicleOptions = vehiclesRes.data.vehicles.map((v) => ({
        value: v._id,
        label: `${v.plate_number} - ${v.brand} ${v.model}`
      }))

      setVehicles(vehicleOptions)
      setCategories(categoriesRes.data.fault_categories)
      setSeverities(categoriesRes.data.severity_levels)

      // Якщо тільки одне авто - вибираємо автоматично
      if (vehicleOptions.length === 1) {
        setFormData(prev => ({ ...prev, vehicle_id: vehicleOptions[0].value }))
      }
    } catch (error) {
      toast.error('Помилка завантаження даних')
    } finally {
      setIsDataLoading(false)
    }
  }

  const handleChange = (name, value) => {
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files)
    files.forEach(file => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onload = (e) => {
          setPhotos(prev => [...prev, {
            type: 'file',
            data: file,
            preview: e.target.result
          }])
        }
        reader.readAsDataURL(file)
      }
    })
    e.target.value = '' // Скидаємо input
  }

  const handleAddUrl = () => {
    if (!photoUrl.trim()) return
    if (!photoUrl.startsWith('http://') && !photoUrl.startsWith('https://')) {
      toast.error('URL має починатися з http:// або https://')
      return
    }
    setPhotos(prev => [...prev, {
      type: 'url',
      data: photoUrl,
      preview: photoUrl
    }])
    setPhotoUrl('')
  }

  const handleRemovePhoto = (index) => {
    setPhotos(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!formData.vehicle_id || !formData.category || !formData.severity || !formData.description) {
      toast.error('Заповніть всі обов\'язкові поля')
      return
    }

    if (formData.description.length < 10) {
      toast.error('Опис має бути не менше 10 символів')
      return
    }

    setIsLoading(true)

    try {
      // Створюємо несправність
      const requestData = {
        vehicle_id: formData.vehicle_id,
        category: formData.category,
        severity: formData.severity,
        description: formData.description
      }
      if (formData.odometer) {
        requestData.odometer = parseInt(formData.odometer)
      }
      const response = await faultsApi.create(requestData)

      const faultId = response.data.fault._id

      // Завантажуємо фото
      for (const photo of photos) {
        try {
          if (photo.type === 'file') {
            await faultsApi.uploadPhoto(faultId, photo.data)
          } else {
            await faultsApi.addPhotoUrl(faultId, photo.data)
          }
        } catch (err) {
          console.error('Помилка завантаження фото:', err)
        }
      }

      toast.success(`Несправність ${response.data.fault.number} створено`)
      navigate('/driver/faults')
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
        <h1>Нова несправність</h1>
      </div>

      <div className="card">
        {isDataLoading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Завантаження...</p>
          </div>
        ) : (
        <form onSubmit={handleSubmit}>
          <FormField
            label="Транспортний засіб"
            name="vehicle_id"
            type="select"
            value={formData.vehicle_id}
            onChange={handleChange}
            options={vehicles}
            required
            disabled={vehicles.length === 1}
          />

          {vehicles.length === 0 && (
            <p className="text-warning mb-md">
              У вас немає активних путівок. Зверніться до керівника.
            </p>
          )}

          <div className="form-row">
            <FormField
              label="Категорія"
              name="category"
              type="select"
              value={formData.category}
              onChange={handleChange}
              options={categories}
              required
            />

            <FormField
              label="Критичність"
              name="severity"
              type="select"
              value={formData.severity}
              onChange={handleChange}
              options={severities}
              required
            />
          </div>

          <FormField
            label="Опис несправності"
            name="description"
            type="textarea"
            value={formData.description}
            onChange={handleChange}
            placeholder="Детально опишіть несправність..."
            rows={5}
            required
          />

          <FormField
            label="Поточний пробіг (км)"
            name="odometer"
            type="number"
            value={formData.odometer}
            onChange={handleChange}
            min={0}
          />

          {/* Секція фото */}
          <div className="form-group">
            <label className="form-label">Фото (необов'язково)</label>

            {/* Превью фото */}
            {photos.length > 0 && (
              <div className="photo-preview-grid">
                {photos.map((photo, index) => (
                  <div key={index} className="photo-preview-item">
                    <img src={photo.preview} alt={`Фото ${index + 1}`} />
                    <button
                      type="button"
                      className="photo-remove-btn"
                      onClick={() => handleRemovePhoto(index)}
                    >
                      X
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Кнопки додавання */}
            <div className="photo-upload-actions">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept="image/*"
                multiple
                style={{ display: 'none' }}
              />
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => fileInputRef.current?.click()}
              >
                Вибрати файл
              </button>

              <div className="photo-url-input">
                <input
                  type="text"
                  className="form-input"
                  placeholder="Або вставте URL фото"
                  value={photoUrl}
                  onChange={(e) => setPhotoUrl(e.target.value)}
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleAddUrl}
                  disabled={!photoUrl.trim()}
                >
                  Додати
                </button>
              </div>
            </div>
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
              disabled={isLoading || vehicles.length === 0 || categories.length === 0}
            >
              {isLoading ? 'Збереження...' : 'Створити'}
            </button>
          </div>
        </form>
        )}
      </div>
    </div>
  )
}

export default DriverFaultNew
