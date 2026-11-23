import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useVehicleStore } from '../../store/vehicleStore'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatOdometer, formatDate } from '../../utils/formatters'
import { tr } from '../../i18n'

function MechanicFleet() {
  const navigate = useNavigate()
  const { vehicles, fetchVehicles, isLoading } = useVehicleStore()

  useEffect(() => {
    fetchVehicles()
  }, [])

  const columns = [
    {
      key: 'plate_number',
      label: tr("Номер"),
      width: '100px'
    },
    {
      key: 'brand',
      label: tr("Марка/Модель"),
      render: (_, row) => `${row.brand} ${row.model}`
    },
    {
      key: 'odometer',
      label: tr("Пробіг"),
      width: '120px',
      render: (val) => formatOdometer(val)
    },
    {
      key: 'next_maintenance_km',
      label: tr("Наступне ТО (км)"),
      width: '140px',
      render: (val, row) => {
        if (!val) return '-'
        const remaining = val - (row.odometer || 0)
        return (
          <span className={remaining <= 1000 ? 'text-warning' : ''}>
            {formatOdometer(val)} ({remaining > 0 ? `+${remaining}` : remaining})
          </span>
        )
      }
    },
    {
      key: 'next_maintenance_date',
      label: tr("Наступне ТО (дата)"),
      width: '120px',
      render: (val) => formatDate(val)
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
        <h1>{tr("Автопарк")}</h1>
      </div>

      <DataTable
        columns={columns}
        data={vehicles}
        isLoading={isLoading}
        emptyMessage={tr("Немає транспортних засобів")}
        onRowClick={(row) => navigate(`/mechanic/fleet/${row._id}`)}
      />
    </div>
  )
}

export default MechanicFleet
