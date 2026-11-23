import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { reportsApi } from '../../api/reports'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDate, formatNumber, formatOdometer } from '../../utils/formatters'

function ManagerReports() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'fleet')
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)

  useEffect(() => {
    loadData()
  }, [activeTab])

  const loadData = async () => {
    setLoading(true)
    try {
      let response
      switch (activeTab) {
        case 'fleet':
          response = await reportsApi.getFleetStatus()
          break
        case 'fuel':
          response = await reportsApi.getFuelConsumption()
          break
        case 'drivers':
          response = await reportsApi.getDriverPerformance()
          break
        case 'maintenance':
          response = await reportsApi.getMaintenanceSchedule()
          break
        case 'costs':
          response = await reportsApi.getCostsSummary()
          break
        default:
          response = await reportsApi.getFleetStatus()
      }
      setData(response.data)
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setSearchParams({ tab })
  }

  const renderFleetStatus = () => {
    if (!data?.vehicles) return null

    const columns = [
      {
        key: 'plate_number',
        label: 'Номер',
        render: (_, row) => (
          <div>
            <div className="font-medium">{row.plate_number}</div>
            <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
              {row.brand} {row.model}
            </div>
          </div>
        )
      },
      {
        key: 'status',
        label: 'Статус',
        render: (status) => <StatusBadge status={status} />
      },
      {
        key: 'odometer',
        label: 'Пробіг',
        render: (val) => formatOdometer(val)
      },
      {
        key: 'current_driver',
        label: 'Водій',
        render: (val, row) => row.has_active_waybill ? val || '-' : '-'
      },
      {
        key: 'open_faults',
        label: 'Несправності',
        render: (val) => val > 0 ? (
          <span className="text-danger font-medium">{val}</span>
        ) : '-'
      },
      {
        key: 'next_maintenance_km',
        label: 'До ТО (км)',
        render: (val, row) => {
          if (!val) return '-'
          const remaining = val - (row.odometer || 0)
          return (
            <span className={remaining <= 1000 ? 'text-warning' : remaining <= 0 ? 'text-danger' : ''}>
              {formatNumber(remaining)}
            </span>
          )
        }
      }
    ]

    return (
      <DataTable
        columns={columns}
        data={data.vehicles}
        emptyMessage="Немає даних"
      />
    )
  }

  const renderFuelConsumption = () => {
    if (!data?.by_vehicle) return null

    const columns = [
      {
        key: 'plate_number',
        label: 'Транспорт',
        render: (_, row) => (
          <div>
            <div className="font-medium">{row.plate_number}</div>
            <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
              {row.brand} {row.model}
            </div>
          </div>
        )
      },
      {
        key: 'fuel_norm',
        label: 'Норма',
        render: (val) => `${val} л/100км`
      },
      {
        key: 'total_distance',
        label: 'Пробіг',
        render: (val) => `${formatNumber(val)} км`
      },
      {
        key: 'total_fuel',
        label: 'Витрачено',
        render: (val) => `${formatNumber(val)} л`
      },
      {
        key: 'consumption_per_100km',
        label: 'Факт. витрати',
        render: (val) => `${val} л/100км`
      },
      {
        key: 'deviation_percent',
        label: 'Відхилення',
        render: (val) => (
          <span className={val > 10 ? 'text-danger font-bold' : val > 0 ? 'text-warning' : 'text-success'}>
            {val > 0 ? '+' : ''}{val}%
          </span>
        )
      }
    ]

    return (
      <>
        {data.summary && (
          <div className="dashboard-stats mb-lg">
            <div className="stat-card">
              <div className="stat-value">{formatNumber(data.summary.total_fuel)} л</div>
              <div className="stat-label">Загальні витрати</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{formatNumber(data.summary.total_distance)} км</div>
              <div className="stat-label">Загальний пробіг</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{data.summary.avg_consumption} л/100км</div>
              <div className="stat-label">Середні витрати</div>
            </div>
          </div>
        )}
        <DataTable
          columns={columns}
          data={data.by_vehicle}
          emptyMessage="Немає даних"
        />
      </>
    )
  }

  const renderDriverPerformance = () => {
    if (!data?.drivers) return null

    const columns = [
      {
        key: 'full_name',
        label: 'Водій'
      },
      {
        key: 'total_waybills',
        label: 'Путівок'
      },
      {
        key: 'total_distance',
        label: 'Пробіг',
        render: (val) => `${formatNumber(val)} км`
      },
      {
        key: 'total_fuel',
        label: 'Пальне',
        render: (val) => `${formatNumber(val)} л`
      },
      {
        key: 'faults_reported',
        label: 'Несправностей'
      }
    ]

    return (
      <DataTable
        columns={columns}
        data={data.drivers}
        emptyMessage="Немає даних"
      />
    )
  }

  const renderMaintenanceSchedule = () => {
    if (!data?.schedule) return null

    const columns = [
      {
        key: 'plate_number',
        label: 'Транспорт',
        render: (_, row) => (
          <div>
            <div className="font-medium">{row.plate_number}</div>
            <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
              {row.brand} {row.model}
            </div>
          </div>
        )
      },
      {
        key: 'current_odometer',
        label: 'Пробіг',
        render: (val) => formatOdometer(val)
      },
      {
        key: 'km_remaining',
        label: 'Залишок км',
        render: (val, row) => {
          if (val === null) return '-'
          return (
            <span className={row.status === 'overdue' ? 'text-danger font-bold' : row.status === 'warning' ? 'text-warning' : ''}>
              {val <= 0 ? `перевищено на ${Math.abs(val)}` : formatNumber(val)}
            </span>
          )
        }
      },
      {
        key: 'days_remaining',
        label: 'Залишок днів',
        render: (val, row) => {
          if (val === null) return '-'
          return (
            <span className={row.status === 'overdue' ? 'text-danger font-bold' : row.status === 'warning' ? 'text-warning' : ''}>
              {val <= 0 ? `прострочено на ${Math.abs(val)}` : val}
            </span>
          )
        }
      },
      {
        key: 'next_maintenance_date',
        label: 'Дата ТО',
        render: (val) => formatDate(val)
      },
      {
        key: 'status',
        label: 'Статус',
        render: (status) => {
          const labels = {
            ok: 'В нормі',
            warning: 'Попередження',
            overdue: 'Прострочено'
          }
          return <StatusBadge status={status === 'ok' ? 'active' : status === 'warning' ? 'warning' : 'danger'} />
        }
      }
    ]

    return (
      <DataTable
        columns={columns}
        data={data.schedule}
        emptyMessage="Немає даних"
      />
    )
  }

  const renderCostsSummary = () => {
    if (!data) return null

    return (
      <div className="dashboard-grid">
        <div className="card">
          <h3>Витрати на пальне (зовнішні заправки)</h3>
          <div className="info-grid mt-md">
            <div className="info-row">
              <span className="label">Кількість</span>
              <span className="value">{formatNumber(data.fuel?.external?.quantity || 0)} л</span>
            </div>
            <div className="info-row">
              <span className="label">Сума</span>
              <span className="value font-bold">{formatNumber(data.fuel?.external?.total || 0)} грн</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Закупівлі пального (накладні)</h3>
          {data.fuel?.invoices?.map((item) => (
            <div key={item._id} className="info-grid mt-md">
              <div className="info-row">
                <span className="label">{{diesel: 'Дизель', petrol: 'Бензин', gas: 'Газ'}[item._id]}</span>
                <span className="value">{formatNumber(item.quantity)} л / {formatNumber(item.total)} грн</span>
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <h3>Витрати на ремонти</h3>
          {data.repairs?.map((item) => (
            <div key={item._id} className="info-grid mt-md">
              <div className="info-row">
                <span className="label">{{maintenance: 'ТО', repair: 'Ремонт', inspection: 'Огляд'}[item._id]}</span>
                <span className="value">
                  {item.count} шт | Робота: {formatNumber(item.labor_cost)} грн | Запчастини: {formatNumber(item.parts_cost)} грн
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Звіти</h1>
      </div>

      {/* Таби */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'fleet' ? 'active' : ''}`}
          onClick={() => handleTabChange('fleet')}
        >
          Стан автопарку
        </button>
        <button
          className={`tab ${activeTab === 'fuel' ? 'active' : ''}`}
          onClick={() => handleTabChange('fuel')}
        >
          Витрати пального
        </button>
        <button
          className={`tab ${activeTab === 'drivers' ? 'active' : ''}`}
          onClick={() => handleTabChange('drivers')}
        >
          Водії
        </button>
        <button
          className={`tab ${activeTab === 'maintenance' ? 'active' : ''}`}
          onClick={() => handleTabChange('maintenance')}
        >
          Графік ТО
        </button>
        <button
          className={`tab ${activeTab === 'costs' ? 'active' : ''}`}
          onClick={() => handleTabChange('costs')}
        >
          Витрати
        </button>
      </div>

      {/* Контент */}
      {loading ? (
        <Loader text="Завантаження..." />
      ) : (
        <div className="card">
          {activeTab === 'fleet' && renderFleetStatus()}
          {activeTab === 'fuel' && renderFuelConsumption()}
          {activeTab === 'drivers' && renderDriverPerformance()}
          {activeTab === 'maintenance' && renderMaintenanceSchedule()}
          {activeTab === 'costs' && renderCostsSummary()}
        </div>
      )}
    </div>
  )
}

export default ManagerReports
