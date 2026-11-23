import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { reportsApi } from '../../api/reports'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDate, formatNumber, formatOdometer } from '../../utils/formatters'
import { downloadCsv, fileDate } from '../../utils/exportReport'
import { tr } from '../../i18n'

const TAB_TITLES = {
  fleet: tr("Стан автопарку"),
  fuel: tr("Витрати пального"),
  drivers: tr("Продуктивність водіїв"),
  maintenance: tr("Графік ТО"),
  costs: tr("Витрати за 30 днів"),
}
const TAB_FILES = {
  fleet: 'stan-avtoparku',
  fuel: 'vytraty-palnoho',
  drivers: 'vodii',
  maintenance: 'hrafik-to',
  costs: 'vytraty',
}
const MAINTENANCE_STATUS = {
  ok: { badge: 'active', label: tr("В нормі") },
  warning: { badge: 'warning', label: tr("Попередження") },
  overdue: { badge: 'critical', label: tr("Прострочено") },
}
const FUEL_LABELS = { diesel: tr("Дизель"), petrol: tr("Бензин"), gas: tr("Газ") }
const REPAIR_LABELS = { maintenance: tr("ТО"), repair: tr("Ремонт"), inspection: tr("Огляд") }
const VEHICLE_STATUS = { active: tr("Активна"), repair: tr("В ремонті"), inspection: tr("На огляді"), decommissioned: tr("Списано") }

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

  // Підготовка даних поточної вкладки для експорту (лише значення, без оформлення)
  const getExportData = () => {
    if (!data) return null
    switch (activeTab) {
      case 'fleet':
        return {
          headers: [tr("Номер"), tr("Марка"), tr("Модель"), tr("Статус"), tr("Пробіг, км"), tr("Водій"), tr("Відкриті несправності"), tr("До ТО, км")],
          rows: (data.vehicles || []).map((v) => [
            v.plate_number, v.brand, v.model, VEHICLE_STATUS[v.status] || v.status, v.odometer,
            v.has_active_waybill ? v.current_driver || '' : '', v.open_faults || 0,
            v.next_maintenance_km ? v.next_maintenance_km - (v.odometer || 0) : '',
          ]),
        }
      case 'fuel':
        return {
          headers: [tr("Номер"), tr("Марка"), tr("Модель"), tr("Норма, л/100 км"), tr("Пробіг, км"), tr("Витрачено, л"), tr("Факт. витрати, л/100 км"), tr("Відхилення, %")],
          rows: (data.by_vehicle || []).map((v) => [
            v.plate_number, v.brand, v.model, v.fuel_norm, v.total_distance, v.total_fuel,
            v.consumption_per_100km, v.deviation_percent,
          ]),
        }
      case 'drivers':
        return {
          headers: [tr("Водій"), tr("Путівок"), tr("Пробіг, км"), tr("Пальне, л"), tr("Несправностей")],
          rows: (data.drivers || []).map((d) => [
            d.full_name, d.total_waybills, d.total_distance, d.total_fuel, d.faults_reported,
          ]),
        }
      case 'maintenance':
        return {
          headers: [tr("Номер"), tr("Марка"), tr("Модель"), tr("Пробіг, км"), tr("Залишок, км"), tr("Залишок, днів"), tr("Дата ТО"), tr("Прогноз ТО"), tr("Основа прогнозу"), tr("Статус")],
          rows: (data.schedule || []).map((v) => [
            v.plate_number, v.brand, v.model, v.current_odometer, v.km_remaining ?? '', v.days_remaining ?? '',
            v.next_maintenance_date ? formatDate(v.next_maintenance_date) : '',
            v.forecast?.expected_date ? formatDate(v.forecast.expected_date) : '',
            v.forecast?.basis === 'mileage' ? tr("за пробігом, ≈{0} км/добу", v.forecast.avg_daily_km) : v.forecast?.basis ? tr("за датою") : '',
            (MAINTENANCE_STATUS[v.status] || MAINTENANCE_STATUS.ok).label,
          ]),
        }
      case 'costs': {
        const rows = []
        const ext = data.fuel?.external || {}
        rows.push([tr("Пальне: зовнішні заправки"), '', ext.quantity || 0, ext.total || 0, '', ''])
        ;(data.fuel?.invoices || []).forEach((i) =>
          rows.push([tr("Пальне: накладні ({0})", FUEL_LABELS[i._id] || i._id), '', i.quantity, i.total, '', '']))
        ;(data.repairs || []).forEach((r) =>
          rows.push([tr("Роботи: {0}", REPAIR_LABELS[r._id] || r._id), r.count, '', (r.labor_cost || 0) + (r.parts_cost || 0), r.labor_cost, r.parts_cost]))
        return {
          headers: [tr("Стаття витрат"), tr("Кількість робіт"), tr("Пальне, л"), tr("Сума, грн"), tr("Робота, грн"), tr("Запчастини, грн")],
          rows,
        }
      }
      default:
        return null
    }
  }

  const handleExport = () => {
    const exp = getExportData()
    if (!exp) return
    downloadCsv(`zvit-${TAB_FILES[activeTab]}-${fileDate()}.csv`, exp.headers, exp.rows)
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
        label: tr("Номер"),
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
        label: tr("Статус"),
        render: (status) => <StatusBadge status={status} />
      },
      {
        key: 'odometer',
        label: tr("Пробіг"),
        render: (val) => formatOdometer(val)
      },
      {
        key: 'current_driver',
        label: tr("Водій"),
        render: (val, row) => row.has_active_waybill ? val || '-' : '-'
      },
      {
        key: 'open_faults',
        label: tr("Несправності"),
        render: (val) => val > 0 ? (
          <span className="text-danger font-medium">{val}</span>
        ) : '-'
      },
      {
        key: 'next_maintenance_km',
        label: tr("До ТО (км)"),
        render: (val, row) => {
          if (!val) return '-'
          const remaining = val - (row.odometer || 0)
          return (
            <span className={remaining <= 0 ? 'text-danger font-bold' : remaining <= 1000 ? 'text-warning' : ''}>
              {remaining <= 0 ? tr("перевищено на {0}", formatNumber(Math.abs(remaining))) : formatNumber(remaining)}
            </span>
          )
        }
      }
    ]

    return (
      <DataTable
        columns={columns}
        data={data.vehicles}
        emptyMessage={tr("Немає даних")}
      />
    )
  }

  const renderFuelConsumption = () => {
    if (!data?.by_vehicle) return null

    const columns = [
      {
        key: 'plate_number',
        label: tr("Транспорт"),
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
        label: tr("Норма"),
        render: (val) => tr("{0} л/100км", val)
      },
      {
        key: 'total_distance',
        label: tr("Пробіг"),
        render: (val) => tr("{0} км", formatNumber(val))
      },
      {
        key: 'total_fuel',
        label: tr("Витрачено"),
        render: (val) => tr("{0} л", formatNumber(val))
      },
      {
        key: 'consumption_per_100km',
        label: tr("Факт. витрати"),
        render: (val) => tr("{0} л/100км", val)
      },
      {
        key: 'deviation_percent',
        label: tr("Відхилення"),
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
              <div className="stat-value">{formatNumber(data.summary.total_fuel)}{' '}{tr("л")}</div>
              <div className="stat-label">{tr("Загальні витрати")}</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{formatNumber(data.summary.total_distance)}{' '}{tr("км")}</div>
              <div className="stat-label">{tr("Загальний пробіг")}</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{data.summary.avg_consumption}{' '}{tr("л/100км")}</div>
              <div className="stat-label">{tr("Середні витрати")}</div>
            </div>
          </div>
        )}
        <DataTable
          columns={columns}
          data={data.by_vehicle}
          emptyMessage={tr("Немає даних")}
        />
      </>
    )
  }

  const renderDriverPerformance = () => {
    if (!data?.drivers) return null

    const columns = [
      {
        key: 'full_name',
        label: tr("Водій")
      },
      {
        key: 'total_waybills',
        label: tr("Путівок")
      },
      {
        key: 'total_distance',
        label: tr("Пробіг"),
        render: (val) => tr("{0} км", formatNumber(val))
      },
      {
        key: 'total_fuel',
        label: tr("Пальне"),
        render: (val) => tr("{0} л", formatNumber(val))
      },
      {
        key: 'faults_reported',
        label: tr("Несправностей")
      }
    ]

    return (
      <DataTable
        columns={columns}
        data={data.drivers}
        emptyMessage={tr("Немає даних")}
      />
    )
  }

  const renderMaintenanceSchedule = () => {
    if (!data?.schedule) return null

    const columns = [
      {
        key: 'plate_number',
        label: tr("Транспорт"),
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
        label: tr("Пробіг"),
        render: (val) => formatOdometer(val)
      },
      {
        key: 'km_remaining',
        label: tr("Залишок км"),
        render: (val, row) => {
          if (val === null) return '-'
          return (
            <span className={row.status === 'overdue' ? 'text-danger font-bold' : row.status === 'warning' ? 'text-warning' : ''}>
              {val <= 0 ? tr("перевищено на {0}", Math.abs(val)) : formatNumber(val)}
            </span>
          )
        }
      },
      {
        key: 'days_remaining',
        label: tr("Залишок днів"),
        render: (val, row) => {
          if (val === null) return '-'
          return (
            <span className={row.status === 'overdue' ? 'text-danger font-bold' : row.status === 'warning' ? 'text-warning' : ''}>
              {val <= 0 ? tr("прострочено на {0}", Math.abs(val)) : val}
            </span>
          )
        }
      },
      {
        key: 'next_maintenance_date',
        label: tr("Дата ТО"),
        render: (val) => formatDate(val)
      },
      {
        key: 'forecast',
        label: tr("Прогноз ТО"),
        sortValue: (row) => row.forecast?.expected_date,
        render: (f) => {
          if (!f?.expected_date) return '-'
          const cls = f.days_left <= 0 ? 'text-danger font-bold' : f.days_left <= 14 ? 'text-warning' : ''
          return (
            <div>
              <div className={cls}>≈ {formatDate(f.expected_date)}</div>
              <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                {f.basis === 'mileage' ? tr("за пробігом, ≈{0} км/добу", f.avg_daily_km) : tr("за датою")}
              </div>
            </div>
          )
        }
      },
      {
        key: 'status',
        label: tr("Статус"),
        render: (status) => {
          const s = MAINTENANCE_STATUS[status] || MAINTENANCE_STATUS.ok
          return <StatusBadge status={s.badge} customLabel={s.label} />
        }
      }
    ]

    return (
      <DataTable
        columns={columns}
        data={data.schedule}
        emptyMessage={tr("Немає даних")}
      />
    )
  }

  const renderCostsSummary = () => {
    if (!data) return null

    return (
      <div className="dashboard-grid">
        <div className="card">
          <h3>{tr("Витрати на пальне (зовнішні заправки)")}</h3>
          <p className="text-muted chart-subtitle">{tr("За останні 30 днів")}</p>
          <div className="info-grid mt-md">
            <div className="info-row">
              <span className="label">{tr("Кількість")}</span>
              <span className="value">{formatNumber(data.fuel?.external?.quantity || 0)}{' '}{tr("л")}</span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Сума")}</span>
              <span className="value font-bold">{formatNumber(data.fuel?.external?.total || 0)}{' '}{tr("грн")}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3>{tr("Закупівлі пального (накладні)")}</h3>
          {data.fuel?.invoices?.map((item) => (
            <div key={item._id} className="info-grid mt-md">
              <div className="info-row">
                <span className="label">{{diesel: tr("Дизель"), petrol: tr("Бензин"), gas: tr("Газ")}[item._id]}</span>
                <span className="value">{formatNumber(item.quantity)}{' '}{tr("л /")}{' '}{formatNumber(item.total)}{' '}{tr("грн")}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <h3>{tr("Витрати на ремонти")}</h3>
          {data.repairs?.map((item) => (
            <div key={item._id} className="info-grid mt-md">
              <div className="info-row">
                <span className="label">{{maintenance: tr("ТО"), repair: tr("Ремонт"), inspection: tr("Огляд")}[item._id]}</span>
                <span className="value">
                  {item.count}{' '}{tr("шт | Робота:")}{' '}{formatNumber(item.labor_cost)}{' '}{tr("грн | Запчастини:")}{' '}{formatNumber(item.parts_cost)}{' '}{tr("грн")}
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
        <h1>{tr("Звіти")}</h1>
        <div className="report-actions no-print">
          <button className="btn btn-secondary" onClick={handleExport} disabled={loading || !data}
            title={tr("Завантажити поточну таблицю у файл для Excel")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Excel
          </button>
          <button className="btn btn-secondary" onClick={() => window.print()} disabled={loading || !data}
            title={tr("Надрукувати або зберегти як PDF")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 6 2 18 2 18 9" />
              <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
              <rect x="6" y="14" width="12" height="8" />
            </svg>
            {tr("Друк / PDF")}
          </button>
        </div>
      </div>

      {/* Шапка, яка видна лише під час друку / збереження в PDF */}
      <div className="print-only report-print-header">
        <h2>KRUTII TRANS – {TAB_TITLES[activeTab]}</h2>
        <p>{tr("Сформовано:")}{' '}{formatDate(new Date(), 'dd.MM.yyyy HH:mm')}</p>
      </div>

      {/* Таби */}
      <div className="tabs no-print">
        <button
          className={`tab ${activeTab === 'fleet' ? 'active' : ''}`}
          onClick={() => handleTabChange('fleet')}
        >
          {tr("Стан автопарку")}
        </button>
        <button
          className={`tab ${activeTab === 'fuel' ? 'active' : ''}`}
          onClick={() => handleTabChange('fuel')}
        >
          {tr("Витрати пального")}
        </button>
        <button
          className={`tab ${activeTab === 'drivers' ? 'active' : ''}`}
          onClick={() => handleTabChange('drivers')}
        >
          {tr("Водії")}
        </button>
        <button
          className={`tab ${activeTab === 'maintenance' ? 'active' : ''}`}
          onClick={() => handleTabChange('maintenance')}
        >
          {tr("Графік ТО")}
        </button>
        <button
          className={`tab ${activeTab === 'costs' ? 'active' : ''}`}
          onClick={() => handleTabChange('costs')}
        >
          {tr("Витрати")}
        </button>
      </div>

      {/* Контент */}
      {loading ? (
        <Loader text={tr("Завантаження...")} />
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
