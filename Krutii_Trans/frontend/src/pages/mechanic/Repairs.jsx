import { useEffect, useState } from 'react'
import { useRoleBase } from '../../utils/useRoleBase'
import { useNavigate } from 'react-router-dom'
import { repairsApi } from '../../api/repairs'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatDate } from '../../utils/formatters'
import { tr } from '../../i18n'

function MechanicRepairs() {
  const navigate = useNavigate()
  const base = useRoleBase()
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
      label: tr("Номер"),
      width: '100px'
    },
    {
      key: 'vehicle',
      label: tr("Транспорт"),
      render: (_, row) => row.vehicle?.plate_number || '-'
    },
    {
      key: 'repair_type',
      label: tr("Тип"),
      width: '140px',
      render: (_, row) => row.repair_type_display || row.repair_type
    },
    {
      key: 'description',
      label: tr("Опис"),
      render: (val) => (val?.length > 50 ? val.slice(0, 50) + '...' : val)
    },
    {
      key: 'scheduled_date',
      label: tr("Дата"),
      width: '100px',
      render: (val) => formatDate(val)
    },
    {
      key: 'mechanic',
      label: tr("Механік"),
      render: (_, row) => row.mechanic?.full_name || '-'
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
        <h1>{tr("Ремонти")}</h1>

        <div className="header-actions">
          <div className="filter-tabs">
            <button
              className={`tab ${filter === 'active' ? 'active' : ''}`}
              onClick={() => setFilter('active')}
            >
              {tr("Активні")}
            </button>
            <button
              className={`tab ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              {tr("Всі")}
            </button>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => navigate(`${base}/repairs/new`)}
          >
            {tr("Новий ремонт")}
          </button>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={repairs}
        isLoading={isLoading}
        emptyMessage={filter === 'active' ? tr("Немає активних ремонтів") : tr("Немає ремонтів")}
        onRowClick={(row) => navigate(`${base}/repairs/${row._id}`)}
      />
    </div>
  )
}

export default MechanicRepairs
