import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { repairsApi } from '../../api/repairs'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatDate } from '../../utils/formatters'

function MechanicRepairs() {
  const navigate = useNavigate()
  const [repairs, setRepairs] = useState([])
  const [filter, setFilter] = useState('active') // active, all
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadRepairs()
  }, [filter])

  const loadRepairs = async () => {
    setIsLoading(true)
    try {
      const response =
        filter === 'active'
          ? await repairsApi.getScheduled()
          : await repairsApi.getAll()
      setRepairs(response.data.repairs)
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
      key: 'repair_type',
      label: 'Тип',
      width: '140px',
      render: (_, row) => row.repair_type_display || row.repair_type
    },
    {
      key: 'description',
      label: 'Опис',
      render: (val) => (val?.length > 50 ? val.slice(0, 50) + '...' : val)
    },
    {
      key: 'scheduled_date',
      label: 'Дата',
      width: '100px',
      render: (val) => formatDate(val)
    },
    {
      key: 'mechanic',
      label: 'Механік',
      render: (_, row) => row.mechanic?.full_name || '-'
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
        <h1>Ремонти</h1>

        <div className="header-actions">
          <div className="filter-tabs">
            <button
              className={`tab ${filter === 'active' ? 'active' : ''}`}
              onClick={() => setFilter('active')}
            >
              Активні
            </button>
            <button
              className={`tab ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              Всі
            </button>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => navigate('/mechanic/repairs/new')}
          >
            Новий ремонт
          </button>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={repairs}
        isLoading={isLoading}
        emptyMessage={filter === 'active' ? 'Немає активних ремонтів' : 'Немає ремонтів'}
        onRowClick={(row) => navigate(`/mechanic/repairs/${row._id}`)}
      />
    </div>
  )
}

export default MechanicRepairs
