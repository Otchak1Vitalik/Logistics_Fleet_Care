import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { faultsApi } from '../../api/faults'
import { repairsApi } from '../../api/repairs'
import { reportsApi } from '../../api/reports'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDateTime } from '../../utils/formatters'
import { tr } from '../../i18n'

function MechanicDashboard() {
  const navigate = useNavigate()
  const [pendingFaults, setPendingFaults] = useState([])
  const [scheduledRepairs, setScheduledRepairs] = useState([])
  const [maintenanceSchedule, setMaintenanceSchedule] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [faultsRes, repairsRes, maintenanceRes] = await Promise.all([
        faultsApi.getPending(),
        repairsApi.getScheduled(),
        reportsApi.getMaintenanceSchedule()
      ])
      setPendingFaults(faultsRes.data.faults.slice(0, 5))
      setScheduledRepairs(repairsRes.data.repairs.slice(0, 5))
      setMaintenanceSchedule(
        maintenanceRes.data.schedule.filter((v) => v.status !== 'ok').slice(0, 5)
      )
    } catch (error) {
      // Ігноруємо
    }
    setLoading(false)
  }

  if (loading) {
    return <Loader text={tr("Завантаження...")} />
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{tr("Головна")}</h1>
      </div>

      <div className="stats-row">
        <div className="stat-card stat-warning">
          <span className="stat-value">{pendingFaults.length}</span>
          <span className="stat-label">{tr("Несправності в очікуванні")}</span>
        </div>
        <div className="stat-card stat-info">
          <span className="stat-value">{scheduledRepairs.length}</span>
          <span className="stat-label">{tr("Активні ремонти")}</span>
        </div>
        <div className="stat-card stat-danger">
          <span className="stat-value">
            {maintenanceSchedule.filter((v) => v.status === 'overdue').length}
          </span>
          <span className="stat-label">{tr("Прострочене ТО")}</span>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Несправності */}
        <div className="card">
          <div className="card-header">
            <h3>{tr("Несправності")}</h3>
            <button
              className="btn btn-text"
              onClick={() => navigate('/mechanic/faults')}
            >
              {tr("Всі")}
            </button>
          </div>
          {pendingFaults.length > 0 ? (
            <ul className="list">
              {pendingFaults.map((fault) => (
                <li
                  key={fault._id}
                  className="list-item clickable"
                  onClick={() => navigate(`/mechanic/faults/${fault._id}`)}
                >
                  <div className="item-main">
                    <span className="item-title">
                      {fault.vehicle?.plate_number} - {fault.category_display}
                    </span>
                    <span className="item-subtitle">
                      {fault.severity_display} | {formatDateTime(fault.report_date)}
                    </span>
                  </div>
                  <StatusBadge status={fault.status} />
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state small">{tr("Немає несправностей")}</div>
          )}
        </div>

        {/* Ремонти */}
        <div className="card">
          <div className="card-header">
            <h3>{tr("Активні ремонти")}</h3>
            <button
              className="btn btn-text"
              onClick={() => navigate('/mechanic/repairs')}
            >
              {tr("Всі")}
            </button>
          </div>
          {scheduledRepairs.length > 0 ? (
            <ul className="list">
              {scheduledRepairs.map((repair) => (
                <li
                  key={repair._id}
                  className="list-item clickable"
                  onClick={() => navigate(`/mechanic/repairs/${repair._id}`)}
                >
                  <div className="item-main">
                    <span className="item-title">
                      {repair.vehicle?.plate_number} - {repair.repair_type_display}
                    </span>
                    <span className="item-subtitle">{repair.description}</span>
                  </div>
                  <StatusBadge status={repair.status} />
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state small">{tr("Немає активних ремонтів")}</div>
          )}
          <div className="card-footer">
            <button
              className="btn btn-primary"
              onClick={() => navigate('/mechanic/repairs/new')}
            >
              {tr("Створити ремонт")}
            </button>
          </div>
        </div>

        {/* Графік ТО */}
        <div className="card full-width">
          <div className="card-header">
            <h3>{tr("Потребують ТО")}</h3>
            <button
              className="btn btn-text"
              onClick={() => navigate('/mechanic/fleet')}
            >
              {tr("Всі")}
            </button>
          </div>
          {maintenanceSchedule.length > 0 ? (
            <ul className="list">
              {maintenanceSchedule.map((vehicle) => (
                <li
                  key={vehicle._id}
                  className="list-item clickable"
                  onClick={() => navigate(`/mechanic/fleet/${vehicle._id}`)}
                >
                  <div className="item-main">
                    <span className="item-title">
                      {vehicle.plate_number} - {vehicle.brand} {vehicle.model}
                    </span>
                    <span className="item-subtitle">
                      {vehicle.km_remaining !== null && tr("Залишилось {0} км", vehicle.km_remaining)}
                      {vehicle.km_remaining !== null && vehicle.days_remaining !== null && ' | '}
                      {vehicle.days_remaining !== null && tr("{0} днів", vehicle.days_remaining)}
                    </span>
                  </div>
                  <StatusBadge
                    status={vehicle.status}
                    customLabel={vehicle.status === 'overdue' ? tr("Прострочено") : tr("Скоро")}
                  />
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state small">{tr("Всі авто в порядку")}</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default MechanicDashboard
