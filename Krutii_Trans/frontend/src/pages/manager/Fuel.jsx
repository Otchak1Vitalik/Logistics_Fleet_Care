import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fuelApi } from '../../api/fuel'
import DataTable from '../../components/DataTable'
import { formatDate, formatNumber } from '../../utils/formatters'
import { tr } from '../../i18n'

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
      label: tr("Номер"),
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
      label: tr("Постачальник"),
      render: (val) => val || '-'
    },
    {
      key: 'fuel_type',
      label: tr("Тип"),
      render: (type) => ({
        diesel: tr("Дизель"),
        petrol: tr("Бензин"),
        gas: tr("Газ")
      }[type] || type)
    },
    {
      key: 'quantity',
      label: tr("Кількість"),
      render: (val) => tr("{0} л", formatNumber(val))
    },
    {
      key: 'distributed',
      label: tr("Розподілено"),
      render: (val, row) => (
        <div>
          <span>{formatNumber(val || 0)}{' '}{tr("л")}</span>
          <span className="text-muted" style={{ marginLeft: '8px' }}>
            ({formatNumber(row.quantity - (val || 0))}{' '}{tr("залишок)")}
          </span>
        </div>
      )
    },
    {
      key: 'total_amount',
      label: tr("Сума"),
      render: (val) => val ? tr("{0} грн", formatNumber(val)) : '-'
    }
  ]

  const recordColumns = [
    {
      key: 'date',
      label: tr("Дата"),
      render: (val) => formatDate(val)
    },
    {
      key: 'vehicle',
      label: tr("Транспорт"),
      render: (_, row) => row.vehicle?.plate_number || '-'
    },
    {
      key: 'driver',
      label: tr("Водій"),
      render: (_, row) => row.driver?.full_name || '-'
    },
    {
      key: 'quantity',
      label: tr("Кількість"),
      render: (val) => tr("{0} л", formatNumber(val))
    },
    {
      key: 'record_type',
      label: tr("Тип"),
      render: (type) => ({
        issue: tr("Видача"),
        external: tr("Зовнішня заправка"),
        return: tr("Повернення")
      }[type] || type)
    },
    {
      key: 'station',
      label: tr("АЗС"),
      render: (val) => val || '-'
    }
  ]

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{tr("Пальне")}</h1>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/manager/fuel/new')}
        >
          {tr("Нова накладна")}
        </button>
      </div>

      {/* Зведення */}
      {summary && (
        <div className="dashboard-stats mb-lg">
          {summary.by_fuel_type?.map((item) => (
            <div key={item._id} className="stat-card">
              <div className="stat-value">{formatNumber(item.total_received)}{' '}{tr("л")}</div>
              <div className="stat-label">
                {{
                  diesel: tr("Дизель"),
                  petrol: tr("Бензин"),
                  gas: tr("Газ")
                }[item._id] || item._id}{' '}{tr("(отримано)")}
              </div>
              <div className="text-muted mt-sm" style={{ fontSize: '0.875rem' }}>
                {tr("Розподілено:")}{' '}{formatNumber(item.total_distributed || 0)}{' '}{tr("л")}
              </div>
            </div>
          ))}
          <div className="stat-card">
            <div className="stat-value">
              {formatNumber(summary.monthly?.total_issued || 0)}{' '}{tr("л")}
            </div>
            <div className="stat-label">{tr("Видано за місяць")}</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              {formatNumber(summary.monthly?.total_external || 0)}{' '}{tr("л")}
            </div>
            <div className="stat-label">{tr("Зовнішні заправки за місяць")}</div>
          </div>
        </div>
      )}

      {/* Таби */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'invoices' ? 'active' : ''}`}
          onClick={() => setActiveTab('invoices')}
        >
          {tr("Накладні")}
        </button>
        <button
          className={`tab ${activeTab === 'records' ? 'active' : ''}`}
          onClick={() => setActiveTab('records')}
        >
          {tr("Записи видачі")}
        </button>
      </div>

      {/* Контент */}
      <div className="card">
        {activeTab === 'invoices' ? (
          <DataTable
            columns={invoiceColumns}
            data={invoices}
            isLoading={loading}
            emptyMessage={tr("Накладних не знайдено")}
          />
        ) : (
          <DataTable
            columns={recordColumns}
            data={records}
            isLoading={loading}
            emptyMessage={tr("Записів не знайдено")}
          />
        )}
      </div>
    </div>
  )
}

export default ManagerFuel
