import { useEffect, useState } from 'react'
import { useAlertStore } from '../store/alertStore'

function AlertBell() {
  const { unreadCount, fetchUnreadCount, alerts, fetchAlerts, markAsRead } = useAlertStore()
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    fetchUnreadCount()
    const interval = setInterval(fetchUnreadCount, 60000) // Кожну хвилину
    return () => clearInterval(interval)
  }, [])

  const handleToggle = () => {
    if (!isOpen) {
      fetchAlerts(true) // Тільки непрочитані
    }
    setIsOpen(!isOpen)
  }

  const handleAlertClick = (alert) => {
    if (!alert.is_read) {
      markAsRead(alert._id)
    }
  }

  return (
    <div className="alert-bell">
      <button className="bell-button" onClick={handleToggle}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>

      {isOpen && (
        <div className="alert-dropdown">
          <div className="dropdown-header">
            <span>Сповіщення</span>
            {alerts.length > 0 && (
              <button
                className="btn btn-text btn-sm"
                onClick={() => useAlertStore.getState().markAllAsRead()}
              >
                Прочитати всі
              </button>
            )}
          </div>

          <div className="dropdown-content">
            {alerts.length === 0 ? (
              <div className="empty-state">Немає нових сповіщень</div>
            ) : (
              alerts.slice(0, 10).map((alert) => (
                <div
                  key={alert._id}
                  className={`alert-item alert-${alert.alert_type} ${
                    !alert.is_read ? 'unread' : ''
                  }`}
                  onClick={() => handleAlertClick(alert)}
                >
                  <div className="alert-title">{alert.title}</div>
                  <div className="alert-message">{alert.message}</div>
                  <div className="alert-time">
                    {new Date(alert.created_at).toLocaleString('uk-UA')}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default AlertBell
