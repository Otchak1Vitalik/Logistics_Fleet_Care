import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { faultsApi } from '../../api/faults'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatDateTime } from '../../utils/formatters'

function MechanicFaults() {
  const navigate = useNavigate()
  const [faults, setFaults] = useState([])
  const [filter, setFilter] = useState('pending') // pending, all
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadFaults()
  }, [filter])

  const loadFaults = async () => {
    setIsLoading(true)
    try {
      const response =
        filter === 'pending'
          ? await faultsApi.getPending()
          : await faultsApi.getAll()
      setFaults(response.data.faults)
    } catch (error) {
      // Ігноруємо
    }
    setIsLoading(false)
  }

  const columns = [
    {
      key: 'number',
      label: 'Номер',
      width: '100px'
    },
    {
      key: 'vehicle',
      label: 'Транспорт',
      render: (_, row) => row.vehicle?.plate_number || '-'
    },
    {
      key: 'category',
      label: 'Категорія',
      render: (_, row) => row.category_display || row.category
    },
    {
      key: 'severity',
      label: 'Критичність',
      width: '100px',
      render: (_, row) => (
        <span
          className={
            row.severity === 'critical'
              ? 'text-danger'
              : row.severity === 'high'
              ? 'text-warning'
              : ''
          }
        >
          {row.severity_display || row.severity}
        </span>
      )
    },
    {
      key: 'reporter',
      label: 'Від',
      render: (_, row) => row.reporter?.full_name || '-'
    },
    {
      key: 'report_date',
      label: 'Дата',
      width: '140px',
      render: (val) => formatDateTime(val)
    },
    {
      key: 'status',
      label: 'Статус',
      width: '120px',
      render: (val) => <StatusBadge status={val} />
    }
  ]

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Несправності</h1>

        <div className="filter-tabs">
          <button
            className={`tab ${filter === 'pending' ? 'active' : ''}`}
            onClick={() => setFilter('pending')}
          >
            В очікуванні
          </button>
          <button
            className={`tab ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            Всі
          </button>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={faults}
        isLoading={isLoading}
        emptyMessage={
          filter === 'pending'
            ? 'Немає несправностей в очікуванні'
            : 'Немає несправностей'
        }
        onRowClick={(row) => navigate(`/mechanic/faults/${row._id}`)}
      />
    </div>
  )
}

export default MechanicFaults
