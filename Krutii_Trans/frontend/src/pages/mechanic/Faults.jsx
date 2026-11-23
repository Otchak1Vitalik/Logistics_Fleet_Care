import { useEffect, useState } from 'react'
import { useRoleBase } from '../../utils/useRoleBase'
import { useNavigate } from 'react-router-dom'
import { faultsApi } from '../../api/faults'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatDateTime } from '../../utils/formatters'
import { tr } from '../../i18n'

function MechanicFaults() {
  const navigate = useNavigate()
  const base = useRoleBase()
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
      label: tr("Номер"),
      width: '100px'
    },
    {
      key: 'vehicle',
      label: tr("Транспорт"),
      render: (_, row) => row.vehicle?.plate_number || '-'
    },
    {
      key: 'category',
      label: tr("Категорія"),
      render: (_, row) => row.category_display || row.category
    },
    {
      key: 'severity',
      label: tr("Критичність"),
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
      label: tr("Від"),
      render: (_, row) => row.reporter?.full_name || '-'
    },
    {
      key: 'report_date',
      label: tr("Дата"),
      width: '140px',
      render: (val) => formatDateTime(val)
    },
    {
      key: 'status',
      label: tr("Статус"),
      width: '120px',
      render: (val) => <StatusBadge status={val} />
    }
  ]

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{tr("Несправності")}</h1>

        <div className="filter-tabs">
          <button
            className={`tab ${filter === 'pending' ? 'active' : ''}`}
            onClick={() => setFilter('pending')}
          >
            {tr("В очікуванні")}
          </button>
          <button
            className={`tab ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            {tr("Всі")}
          </button>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={faults}
        isLoading={isLoading}
        emptyMessage={
          filter === 'pending'
            ? tr("Немає несправностей в очікуванні")
            : tr("Немає несправностей")
        }
        onRowClick={(row) => navigate(`${base}/faults/${row._id}`)}
      />
    </div>
  )
}

export default MechanicFaults
