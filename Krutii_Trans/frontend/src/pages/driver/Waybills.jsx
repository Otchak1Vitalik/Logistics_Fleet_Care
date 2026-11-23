import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWaybillStore } from '../../store/waybillStore'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatDate, formatDateTime } from '../../utils/formatters'
import { tr } from '../../i18n'

function DriverWaybills() {
  const navigate = useNavigate()
  const { waybills, fetchWaybills, isLoading } = useWaybillStore()

  useEffect(() => {
    fetchWaybills()
  }, [])

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
      key: 'route',
      label: tr("Маршрут"),
      render: (_, row) => `${row.route_from || ''} - ${row.route_to || ''}`
    },
    {
      key: 'issue_date',
      label: tr("Дата"),
      width: '100px',
      render: (val) => formatDate(val)
    },
    {
      key: 'valid_until',
      label: tr("Дійсна до"),
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
        <h1>{tr("Мої путівки")}</h1>
      </div>

      <DataTable
        columns={columns}
        data={waybills}
        isLoading={isLoading}
        emptyMessage={tr("Немає путівок")}
        onRowClick={(row) => navigate(`/driver/waybills/${row._id}`)}
      />
    </div>
  )
}

export default DriverWaybills
