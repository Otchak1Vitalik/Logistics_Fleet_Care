import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { reportsApi } from '../../api/reports'
import { alertsApi } from '../../api/alerts'
import Loader from '../../components/Loader'

function ManagerDashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [dashboardRes, alertsRes] = await Promise.all([
        reportsApi.getDashboard(),
        alertsApi.getAll({ limit: 5 })
      ])
      setData(dashboardRes.data.dashboard)
      setAlerts(alertsRes.data.alerts)
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <Loader text="Завантаження..." />
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Панель керівника</h1>
      </div>

      {/* Статистика */}
      <div className="dashboard-stats">
        <div
          className="stat-card highlight"
          onClick={() => navigate('/manager/vehicles')}
          style={{ cursor: 'pointer' }}
        >
          <div className="stat-value">{data?.vehicles?.active || 0}</div>
          <div className="stat-label">Активних авто</div>
          {data?.vehicles?.maintenance_due > 0 && (
            <div className="text-warning mt-sm" style={{ fontSize: '0.875rem' }}>
              {data.vehicles.maintenance_due} потребують ТО
            </div>
          )}
        </div>

        <div
          className="stat-card"
          onClick={() => navigate('/manager/users?role=driver')}
          style={{ cursor: 'pointer' }}
        >
          <div className="stat-value">{data?.drivers?.active || 0}</div>
          <div className="stat-label">Активних водіїв</div>
        </div>

        <div
          className="stat-card"
          onClick={() => navigate('/manager/waybills?status=active')}
          style={{ cursor: 'pointer' }}
        >
          <div className="stat-value">{data?.waybills?.active || 0}</div>
          <div className="stat-label">Активних путівок</div>
        </div>

        <div
          className={`stat-card ${data?.faults?.critical > 0 ? 'danger' : data?.faults?.new > 0 ? 'warning' : ''}`}
          onClick={() => navigate('/manager/alerts')}
          style={{ cursor: 'pointer' }}
        >
          <div className="stat-value">{data?.faults?.new || 0}</div>
          <div className="stat-label">Нових несправностей</div>
          {data?.faults?.critical > 0 && (
            <div className="text-danger mt-sm" style={{ fontSize: '0.875rem' }}>
              {data.faults.critical} критичних
            </div>
          )}
        </div>

        <div
          className="stat-card"
          onClick={() => navigate('/manager/alerts')}
          style={{ cursor: 'pointer' }}
        >
          <div className="stat-value">{data?.repairs?.in_progress || 0}</div>
          <div className="stat-label">Ремонтів в роботі</div>
          {data?.repairs?.planned > 0 && (
            <div className="text-muted mt-sm" style={{ fontSize: '0.875rem' }}>
              {data.repairs.planned} заплановано
            </div>
          )}
        </div>

        <div
          className={`stat-card ${data?.alerts?.unread > 0 ? 'warning' : ''}`}
          onClick={() => navigate('/manager/alerts')}
          style={{ cursor: 'pointer' }}
        >
          <div className="stat-value">{data?.alerts?.unread || 0}</div>
          <div className="stat-label">Непрочитаних сповіщень</div>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Швидкі дії */}
        <div className="card">
          <h3>Швидкі дії</h3>
          <div className="flex flex-col gap-sm mt-md">
            <button
              className="btn btn-primary btn-block"
              onClick={() => navigate('/manager/waybills/new')}
            >
              Видати путівку
            </button>
            <button
              className="btn btn-secondary btn-block"
              onClick={() => navigate('/manager/vehicles/new')}
            >
              Додати транспорт
            </button>
            <button
              className="btn btn-secondary btn-block"
              onClick={() => navigate('/manager/users/new')}
            >
              Додати користувача
            </button>
            <button
              className="btn btn-secondary btn-block"
              onClick={() => navigate('/manager/fuel/new')}
            >
              Оформити накладну на пальне
            </button>
          </div>
        </div>

        {/* Останні сповіщення */}
        <div className="card">
          <div className="card-header">
            <h3>Останні сповіщення</h3>
            <button
              className="btn btn-text"
              onClick={() => navigate('/manager/alerts')}
            >
              Всі
            </button>
          </div>
          {alerts.length > 0 ? (
            <ul className="list">
              {alerts.map((alert) => (
                <li
                  key={alert._id}
                  className={`list-item ${!alert.is_read ? 'font-medium' : ''}`}
                >
                  <div className="item-main">
                    <span className={`item-title ${alert.alert_type === 'critical' ? 'text-danger' : alert.alert_type === 'warning' ? 'text-warning' : ''}`}>
                      {alert.title}
                    </span>
                    <span className="item-subtitle">{alert.message}</span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state small">Немає сповіщень</div>
          )}
        </div>

        {/* Звіти */}
        <div className="card">
          <h3>Звіти</h3>
          <div className="flex flex-col gap-sm mt-md">
            <button
              className="btn btn-secondary btn-block"
              onClick={() => navigate('/manager/reports?tab=fleet')}
            >
              Стан автопарку
            </button>
            <button
              className="btn btn-secondary btn-block"
              onClick={() => navigate('/manager/reports?tab=fuel')}
            >
              Витрати пального
            </button>
            <button
              className="btn btn-secondary btn-block"
              onClick={() => navigate('/manager/reports?tab=drivers')}
            >
              Продуктивність водіїв
            </button>
            <button
              className="btn btn-secondary btn-block"
              onClick={() => navigate('/manager/reports?tab=maintenance')}
            >
              Графік ТО
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ManagerDashboard
