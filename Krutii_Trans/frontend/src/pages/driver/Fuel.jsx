import { useEffect, useState } from 'react'
import { fuelApi } from '../../api/fuel'
import DataTable from '../../components/DataTable'
import { formatDateTime, formatCurrency } from '../../utils/formatters'
import { formatFuel } from '../../utils/fuelCalc'

function DriverFuel() {
  const [records, setRecords] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadRecords()
  }, [])

  const loadRecords = async () => {
    setIsLoading(true)
    try {
      const response = await fuelApi.getRecords()
      setRecords(response.data.records)
    } catch (error) {
      // Ігноруємо
    }
    setIsLoading(false)
  }

  const columns = [
    {
      key: 'date',
      label: 'Дата',
      width: '140px',
      render: (val) => formatDateTime(val)
    },
    {
      key: 'vehicle',
      label: 'Транспорт',
      render: (_, row) => row.vehicle?.plate_number || '-'
    },
    {
      key: 'quantity',
      label: 'Кількість',
      width: '100px',
      render: (val) => formatFuel(val)
    },
    {
      key: 'record_type',
      label: 'Тип',
      width: '120px',
      render: (val) => val === 'issue' ? 'Видача' : 'Зовнішня'
    },
    {
      key: 'station',
      label: 'АЗС',
      render: (val) => val || '-'
    },
    {
      key: 'total_amount',
      label: 'Сума',
      width: '100px',
      render: (val) => val ? formatCurrency(val) : '-'
    }
  ]

  // Підрахунок статистики
  const totalIssued = records
    .filter((r) => r.record_type === 'issue')
    .reduce((sum, r) => sum + r.quantity, 0)

  const totalExternal = records
    .filter((r) => r.record_type === 'external')
    .reduce((sum, r) => sum + r.quantity, 0)

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Історія заправок</h1>
      </div>

      <div className="stats-row">
        <div className="stat-card">
          <span className="stat-value">{formatFuel(totalIssued)}</span>
          <span className="stat-label">Видано з бази</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{formatFuel(totalExternal)}</span>
          <span className="stat-label">Зовнішні заправки</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{formatFuel(totalIssued + totalExternal)}</span>
          <span className="stat-label">Загалом</span>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={records}
        isLoading={isLoading}
        emptyMessage="Немає записів про заправки"
      />
    </div>
  )
}

export default DriverFuel
