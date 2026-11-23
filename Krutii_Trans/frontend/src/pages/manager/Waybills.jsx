import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { waybillsApi } from '../../api/waybills'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatDate, formatDateTime } from '../../utils/formatters'

const STATUSES = {
  issued: 'Видано',
  active: 'Активна',
  completed: 'Завершена',
  cancelled: 'Скасована'
}

function ManagerWaybills() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [waybills, setWaybills] = useState([])
  const [loading, setLoading] = useState(true)

  const statusFilter = searchParams.get('status') || ''

  useEffect(() => {
    loadWaybills()
  }, [statusFilter])

  const loadWaybills = async () => {
    setLoading(true)
    try {
      const params = {}
      if (statusFilter) params.status = statusFilter

      const response = await waybillsApi.getAll(params)
      setWaybills(response.data.waybills)
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      key: 'number',
      label: 'Номер',
      render: (_, row) => (
        <div>
          <div className="font-medium">{row.number}</div>
          <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
            {formatDate(row.issue_date)}
          </div>
        </div>
      )
    },
    {
      key: 'vehicle',
      label: 'Транспорт',
      render: (_, row) => row.vehicle?.plate_number || '-'
    },
    {
      key: 'driver',
      label: 'Водій',
      render: (_, row) => row.driver?.full_name || '-'
    },
    {
      key: 'route',
      label: 'Маршрут',
      render: (_, row) => (
        <div style={{ maxWidth: '200px' }}>
          {row.route_from && row.route_to
            ? `${row.route_from} - ${row.route_to}`
            : row.route_description || '-'}
        </div>
      )
    },
    {
      key: 'valid_until',
      label: 'Дійсна до',
      render: (val) => formatDateTime(val)
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
        <h1>Путівки</h1>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/manager/waybills/new')}
        >
          Видати путівку
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
      </div>

      {/* Таблиця */}
      <div className="card">
        <DataTable
          columns={columns}
          data={waybills}
          isLoading={loading}
          onRowClick={(row) => navigate(`/manager/waybills/${row._id}`)}
          emptyMessage="Путівок не знайдено"
        />
      </div>
    </div>
  )
}

export default ManagerWaybills
