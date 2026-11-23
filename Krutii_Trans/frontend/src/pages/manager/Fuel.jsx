import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fuelApi } from '../../api/fuel'
import DataTable from '../../components/DataTable'
import { formatDate, formatNumber } from '../../utils/formatters'

function ManagerFuel() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('invoices')
  const [invoices, setInvoices] = useState([])
  const [records, setRecords] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [invoicesRes, recordsRes, summaryRes] = await Promise.all([
        fuelApi.getInvoices(),
        fuelApi.getRecords(),
        fuelApi.getSummary()
      ])
      setInvoices(invoicesRes.data.invoices)
      setRecords(recordsRes.data.records)
      setSummary(summaryRes.data)
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const invoiceColumns = [
    {
      key: 'number',
      label: 'Номер',
      render: (_, row) => (
        <div>
          <div className="font-medium">{row.number}</div>
          <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
            {formatDate(row.date)}
          </div>
        </div>
      )
    },
    {
      key: 'supplier',
      label: 'Постачальник',
      render: (val) => val || '-'
    },
    {
      key: 'fuel_type',
      label: 'Тип',
      render: (type) => ({
        diesel: 'Дизель',
        petrol: 'Бензин',
        gas: 'Газ'
      }[type] || type)
    },
    {
      key: 'quantity',
      label: 'Кількість',
      render: (val) => `${formatNumber(val)} л`
    },
    {
      key: 'distributed',
      label: 'Розподілено',
      render: (val, row) => (
        <div>
          <span>{formatNumber(val || 0)} л</span>
          <span className="text-muted" style={{ marginLeft: '8px' }}>
            ({formatNumber(row.quantity - (val || 0))} залишок)
          </span>
        </div>
      )
    },
    {
      key: 'total_amount',
      label: 'Сума',
      render: (val) => val ? `${formatNumber(val)} грн` : '-'
    }
  ]

  const recordColumns = [
    {
      key: 'date',
      label: 'Дата',
      render: (val) => formatDate(val)
    },
    {
      key: 'vehicle',
      label: 'Транспорт',
      render: (_, row) => row.vehicle?.plate_number || '-'
    },
    {
      key: 'driver',
      label: 'Водій',
      render: (_, row) => row.driver?.full_name || '-'
    },
    {
      key: 'quantity',
      label: 'Кількість',
      render: (val) => `${formatNumber(val)} л`
    },
    {
      key: 'record_type',
      label: 'Тип',
      render: (type) => ({
        issue: 'Видача',
        external: 'Зовнішня заправка',
        return: 'Повернення'
      }[type] || type)
    },
    {
      key: 'station',
      label: 'АЗС',
      render: (val) => val || '-'
    }
  ]

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Пальне</h1>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/manager/fuel/new')}
        >
          Нова накладна
        </button>
      </div>

      {/* Зведення */}
      {summary && (
        <div className="dashboard-stats mb-lg">
          {summary.by_fuel_type?.map((item) => (
            <div key={item._id} className="stat-card">
              <div className="stat-value">{formatNumber(item.total_received)} л</div>
              <div className="stat-label">
                {{
                  diesel: 'Дизель',
                  petrol: 'Бензин',
                  gas: 'Газ'
                }[item._id] || item._id} (отримано)
              </div>
              <div className="text-muted mt-sm" style={{ fontSize: '0.875rem' }}>
                Розподілено: {formatNumber(item.total_distributed || 0)} л
              </div>
            </div>
          ))}
          <div className="stat-card">
            <div className="stat-value">
              {formatNumber(summary.monthly?.total_issued || 0)} л
            </div>
            <div className="stat-label">Видано за місяць</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              {formatNumber(summary.monthly?.total_external || 0)} л
            </div>
            <div className="stat-label">Зовнішні заправки за місяць</div>
          </div>
        </div>
      )}

      {/* Таби */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'invoices' ? 'active' : ''}`}
          onClick={() => setActiveTab('invoices')}
        >
          Накладні
        </button>
        <button
          className={`tab ${activeTab === 'records' ? 'active' : ''}`}
          onClick={() => setActiveTab('records')}
        >
          Записи видачі
        </button>
      </div>

      {/* Контент */}
      <div className="card">
        {activeTab === 'invoices' ? (
          <DataTable
            columns={invoiceColumns}
            data={invoices}
            isLoading={loading}
            emptyMessage="Накладних не знайдено"
          />
        ) : (
          <DataTable
            columns={recordColumns}
            data={records}
            isLoading={loading}
            emptyMessage="Записів не знайдено"
          />
        )}
      </div>
    </div>
  )
}

export default ManagerFuel
