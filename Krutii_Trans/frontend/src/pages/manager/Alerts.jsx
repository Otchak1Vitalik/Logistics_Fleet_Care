import { useEffect, useState } from 'react'
import { alertsApi } from '../../api/alerts'
import Loader from '../../components/Loader'
import { formatDateTime } from '../../utils/formatters'

const ALERT_TYPES = {
  info: { label: 'Інформація', color: 'var(--color-info)' },
  warning: { label: 'Попередження', color: 'var(--color-warning)' },
  critical: { label: 'Критично', color: 'var(--color-danger)' }
}

const CATEGORIES = {
  fault: 'Несправності',
  maintenance: 'ТО',
  fuel: 'Пальне',
  escalation: 'Ескалація',
  general: 'Загальне'
}

function ManagerAlerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    loadAlerts()
  }, [])

  const loadAlerts = async () => {
    setLoading(true)
    try {
      const response = await alertsApi.getAll({ limit: 100 })
      setAlerts(response.data.alerts)
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAsRead = async (alertId) => {
    try {
      await alertsApi.markAsRead(alertId)
      setAlerts((prev) =>
        prev.map((a) => (a._id === alertId ? { ...a, is_read: true } : a))
      )
    } catch (error) {
      // Помилка оброблена в interceptor
    }
  }

  const handleDismiss = async (alertId) => {
    try {
      await alertsApi.dismiss(alertId)
      setAlerts((prev) => prev.filter((a) => a._id !== alertId))
    } catch (error) {
      // Помилка оброблена в interceptor
    }
  }

  const handleMarkAllAsRead = async () => {
    try {
      await alertsApi.markAllAsRead()
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })))
    } catch (error) {
      // Помилка оброблена в interceptor
    }
  }

  const filteredAlerts = alerts.filter((a) => {
    if (filter === 'all') return true
    if (filter === 'unread') return !a.is_read
    return a.alert_type === filter
  })

  const unreadCount = alerts.filter((a) => !a.is_read).length

  if (loading) {
    return <Loader text="Завантаження..." />
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>
          Сповіщення
          {unreadCount > 0 && (
            <span className="text-muted" style={{ fontSize: '1rem', marginLeft: '8px' }}>
              ({unreadCount} непрочитаних)
            </span>
          )}
        </h1>
        {unreadCount > 0 && (
          <button className="btn btn-secondary" onClick={handleMarkAllAsRead}>
            Прочитати всі
          </button>
        )}
      </div>

      {/* Фільтри */}
      <div className="filters">
        <div className="filter-group">
          <label>Фільтр</label>
          <select
            className="form-control"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">Всі</option>
            <option value="unread">Непрочитані</option>
            <option value="critical">Критичні</option>
            <option value="warning">Попередження</option>
            <option value="info">Інформація</option>
          </select>
        </div>
      </div>

      {/* Список сповіщень */}
      {filteredAlerts.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            {filter === 'unread' ? 'Немає непрочитаних сповіщень' : 'Немає сповіщень'}
          </div>
        </div>
      ) : (
        <div className="card">
          {filteredAlerts.map((alert) => (
            <div
              key={alert._id}
              className={`list-item ${!alert.is_read ? 'font-medium' : ''}`}
              style={{
                borderLeft: `4px solid ${ALERT_TYPES[alert.alert_type]?.color || 'var(--color-gray-300)'}`,
                backgroundColor: !alert.is_read ? 'var(--color-gray-50)' : 'transparent'
              }}
            >
              <div className="item-main">
                <div className="flex items-center gap-sm">
                  <span
                    className="status-badge"
                    style={{
                      background: ALERT_TYPES[alert.alert_type]?.color,
                      color: 'white'
                    }}
                  >
                    {ALERT_TYPES[alert.alert_type]?.label}
                  </span>
                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                    {CATEGORIES[alert.category] || alert.category}
                  </span>
                </div>
                <span className="item-title mt-sm">{alert.title}</span>
                <span className="item-subtitle">{alert.message}</span>
                <span className="text-muted" style={{ fontSize: '0.75rem', marginTop: '4px' }}>
                  {formatDateTime(alert.created_at)}
                </span>
              </div>
              <div className="flex gap-sm">
                {!alert.is_read && (
                  <button
                    className="btn btn-sm btn-text"
                    onClick={() => handleMarkAsRead(alert._id)}
                  >
                    Прочитано
                  </button>
                )}
                <button
                  className="btn btn-sm btn-text"
                  onClick={() => handleDismiss(alert._id)}
                >
                  Приховати
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ManagerAlerts
