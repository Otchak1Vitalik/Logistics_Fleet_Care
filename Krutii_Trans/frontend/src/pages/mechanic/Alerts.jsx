import { useEffect, useState } from 'react'
import { useAlertStore } from '../../store/alertStore'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDateTime, timeAgo } from '../../utils/formatters'

function MechanicAlerts() {
  const { alerts, fetchAlerts, markAsRead, markAllAsRead, dismiss, isLoading } = useAlertStore()
  const [filter, setFilter] = useState('unread') // unread, all

  useEffect(() => {
    fetchAlerts(filter === 'unread')
  }, [filter])

  if (isLoading) {
    return <Loader text="Завантаження..." />
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Сповіщення</h1>

        <div className="header-actions">
          <div className="filter-tabs">
            <button
              className={`tab ${filter === 'unread' ? 'active' : ''}`}
              onClick={() => setFilter('unread')}
            >
              Непрочитані
            </button>
            <button
              className={`tab ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              Всі
            </button>
          </div>

          {alerts.length > 0 && filter === 'unread' && (
            <button className="btn btn-secondary" onClick={markAllAsRead}>
              Прочитати всі
            </button>
          )}
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="empty-state">
          {filter === 'unread'
            ? 'Немає непрочитаних сповіщень'
            : 'Немає сповіщень'}
        </div>
      ) : (
        <div className="alerts-list">
          {alerts.map((alert) => (
            <div
              key={alert._id}
              className={`alert-card alert-${alert.alert_type} ${
                !alert.is_read ? 'unread' : ''
              }`}
            >
              <div className="alert-header">
                <div className="alert-title">
                  <StatusBadge status={alert.alert_type} />
                  <span>{alert.title}</span>
                </div>
                <span className="alert-time">{timeAgo(alert.created_at)}</span>
              </div>

              <p className="alert-message">{alert.message}</p>

              <div className="alert-footer">
                <span className="alert-date">
                  {formatDateTime(alert.created_at)}
                </span>
                <div className="alert-actions">
                  {!alert.is_read && (
                    <button
                      className="btn btn-text btn-sm"
                      onClick={() => markAsRead(alert._id)}
                    >
                      Прочитано
                    </button>
                  )}
                  <button
                    className="btn btn-text btn-sm"
                    onClick={() => dismiss(alert._id)}
                  >
                    Приховати
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default MechanicAlerts
