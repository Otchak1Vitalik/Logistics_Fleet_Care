import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { waybillsApi } from '../../api/waybills'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatDate, formatDateTime } from '../../utils/formatters'
import { tr } from '../../i18n'

const STATUSES = {
  issued: tr("Видано"),
  active: tr("Активна"),
  completed: tr("Завершена"),
  cancelled: tr("Скасована")
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
      label: tr("Номер"),
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
      label: tr("Транспорт"),
      render: (_, row) => row.vehicle?.plate_number || '-'
    },
    {
      key: 'driver',
      label: tr("Водій"),
      render: (_, row) => row.driver?.full_name || '-'
    },
    {
      key: 'route',
      label: tr("Маршрут"),
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
      label: tr("Дійсна до"),
      render: (val) => formatDateTime(val)
    },
    {
      key: 'status',
      label: tr("Статус"),
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
        <h1>{tr("Путівки")}</h1>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/manager/waybills/new')}
        >
          {tr("Видати путівку")}
        </button>
      </div>

      {/* Фільтри */}
      <div className="filters">
        <div className="filter-group">
          <label>{tr("Статус")}</label>
          <select
            className="form-control"
            value={statusFilter}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="">{tr("Всі")}</option>
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
          emptyMessage={tr("Путівок не знайдено")}
        />
      </div>
    </div>
  )
}

export default ManagerWaybills
