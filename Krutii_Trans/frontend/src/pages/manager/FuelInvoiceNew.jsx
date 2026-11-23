import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { fuelApi } from '../../api/fuel'
import toast from 'react-hot-toast'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'

function FuelInvoiceNew() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    date: new Date(),
    supplier: '',
    fuel_type: 'diesel',
    quantity: '',
    price_per_liter: ''
  })

  const handleChange = (e) => {
    const { name, value, type } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'number' ? (value === '' ? '' : Number(value)) : value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!form.quantity || form.quantity <= 0) {
      toast.error('Вкажіть кількість пального')
      return
    }

    setLoading(true)
    try {
      const data = {
        ...form,
        date: form.date.toISOString().split('T')[0]
      }

      // Видаляємо порожні поля
      Object.keys(data).forEach((key) => {
        if (data[key] === '' || data[key] === null || data[key] === undefined) {
          delete data[key]
        }
      })

      const response = await fuelApi.createInvoice(data)
      toast.success(`Накладну ${response.data.invoice.number} створено`)
      navigate('/manager/fuel')
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const totalAmount = form.quantity && form.price_per_liter
    ? (form.quantity * form.price_per_liter).toFixed(2)
    : null

  return (
    <div className="page-container">
      <Link to="/manager/fuel" className="back-link">
        &larr; Назад
      </Link>

      <div className="page-header">
        <h1>Нова накладна на пальне</h1>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-field">
              <label>Дата</label>
              <DatePicker
                selected={form.date}
                onChange={(date) => setForm((prev) => ({ ...prev, date: date }))}
                dateFormat="dd.MM.yyyy"
                className="form-control"
              />
            </div>

            <div className="form-field">
              <label>Постачальник</label>
              <input
                type="text"
                name="supplier"
                className="form-control"
                value={form.supplier}
                onChange={handleChange}
                placeholder="Назва АЗС або постачальника"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>
                Тип пального <span className="required">*</span>
              </label>
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
              <label>
                Кількість (л) <span className="required">*</span>
              </label>
              <input
                type="number"
                name="quantity"
                className="form-control"
                value={form.quantity}
                onChange={handleChange}
                min={0}
                step="0.1"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Ціна за літр (грн)</label>
              <input
                type="number"
                name="price_per_liter"
                className="form-control"
                value={form.price_per_liter}
                onChange={handleChange}
                min={0}
                step="0.01"
              />
            </div>

            <div className="form-field">
              <label>Загальна сума</label>
              <input
                type="text"
                className="form-control"
                value={totalAmount ? `${totalAmount} грн` : '-'}
                disabled
              />
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/manager/fuel')}
            >
              Скасувати
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? 'Створення...' : 'Створити накладну'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default FuelInvoiceNew
