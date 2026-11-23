import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { vehiclesApi } from '../../api/vehicles'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatOdometer } from '../../utils/formatters'

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

function ManagerVehicles() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(true)

  const statusFilter = searchParams.get('status') || ''
  const fuelFilter = searchParams.get('fuel_type') || ''

  useEffect(() => {
    loadVehicles()
  }, [statusFilter, fuelFilter])

  const loadVehicles = async () => {
    setLoading(true)
    try {
      const params = {}
      if (statusFilter) params.status = statusFilter
      if (fuelFilter) params.fuel_type = fuelFilter

      const response = await vehiclesApi.getAll(params)
      setVehicles(response.data.vehicles)
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      key: 'plate_number',
      label: 'Номер',
      render: (_, row) => (
        <div>
          <div className="font-medium">{row.plate_number}</div>
          <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
            {row.brand} {row.model}
          </div>
        </div>
      )
    },
    {
      key: 'year',
      label: 'Рік'
    },
    {
      key: 'fuel_type',
      label: 'Пальне',
      render: (type) => FUEL_TYPES[type] || type
    },
    {
      key: 'fuel_norm',
      label: 'Норма',
      render: (norm) => norm ? `${norm} л/100км` : '-'
    },
    {
      key: 'odometer',
      label: 'Пробіг',
      render: (km) => formatOdometer(km)
    },
    {
      key: 'status',
      label: 'Статус',
      render: (status) => <StatusBadge status={status} />
    }
  ]

  const handleFilterChange = (key, value) => {
    const params = new URLSearchParams(searchParams)
    if (value) {
      params.set(key, value)
    } else {
      params.delete(key)
    }
    setSearchParams(params)
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Автопарк</h1>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/manager/vehicles/new')}
        >
          Додати транспорт
        </button>
      </div>

      {/* Фільтри */}
      <div className="filters">
        <div className="filter-group">
          <label>Статус</label>
          <select
            className="form-control"
            value={statusFilter}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="">Всі</option>
            {Object.entries(STATUSES).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Тип пального</label>
          <select
            className="form-control"
            value={fuelFilter}
            onChange={(e) => handleFilterChange('fuel_type', e.target.value)}
          >
            <option value="">Всі</option>
            {Object.entries(FUEL_TYPES).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Таблиця */}
      <div className="card">
        <DataTable
          columns={columns}
          data={vehicles}
          isLoading={loading}
          onRowClick={(row) => navigate(`/manager/vehicles/${row._id}`)}
          emptyMessage="Транспорт не знайдено"
        />
      </div>
    </div>
  )
}

export default ManagerVehicles
