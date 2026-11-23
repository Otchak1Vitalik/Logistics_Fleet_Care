import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { faultsApi } from '../../api/faults'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatDateTime } from '../../utils/formatters'

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
      label: 'Номер',
      width: '120px'
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
      render: (_, row) => row.severity_display || row.severity
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
        <h1>Мої несправності</h1>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/driver/faults/new')}
        >
          Повідомити про несправність
        </button>
      </div>

      <DataTable
        columns={columns}
        data={faults}
        isLoading={isLoading}
        emptyMessage="Немає повідомлень про несправності"
        onRowClick={(row) => navigate(`/driver/faults/${row._id}`)}
      />
    </div>
  )
}

export default DriverFaults
