import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { faultsApi } from '../../api/faults'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatDateTime } from '../../utils/formatters'
import { tr } from '../../i18n'

function DriverFaults() {
  const navigate = useNavigate()
  const [faults, setFaults] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadFaults()
  }, [])

  const loadFaults = async () => {
    setIsLoading(true)
    try {
      const response = await faultsApi.getAll()
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
      width: '120px'
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
      render: (_, row) => row.severity_display || row.severity
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
        <h1>{tr("Мої несправності")}</h1>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/driver/faults/new')}
        >
          {tr("Повідомити про несправність")}
        </button>
      </div>

      <DataTable
        columns={columns}
        data={faults}
        isLoading={isLoading}
        emptyMessage={tr("Немає повідомлень про несправності")}
        onRowClick={(row) => navigate(`/driver/faults/${row._id}`)}
      />
    </div>
  )
}

export default DriverFaults
