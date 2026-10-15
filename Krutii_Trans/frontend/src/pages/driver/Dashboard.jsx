import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWaybillStore } from '../../store/waybillStore'
import { faultsApi } from '../../api/faults'
import { fuelApi } from '../../api/fuel'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDateTime, formatOdometer } from '../../utils/formatters'

function DriverDashboard() {
  const navigate = useNavigate()
  const { activeWaybill, fetchActiveWaybill, isLoading: waybillLoading } = useWaybillStore()
  const [recentFaults, setRecentFaults] = useState([])
  const [recentFuel, setRecentFuel] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    await fetchActiveWaybill()

    try {
      const [faultsRes, fuelRes] = await Promise.all([
        faultsApi.getAll(),
        fuelApi.getRecords()
      ])
      setRecentFaults(faultsRes.data.faults.slice(0, 5))
      setRecentFuel(fuelRes.data.records.slice(0, 5))
    } catch (error) {
      // Ігноруємо
    }

    setLoading(false)
  }

  if (loading) {
    return <Loader text="Завантаження..." />
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Головна</h1>
      </div>

      {/* Активна путівка */}
      <div className="card card-highlight">
        <h2>Активна путівка</h2>
        {activeWaybill ? (
          <div className="active-waybill">
            <div className="waybill-info">
              <div className="info-row">
                <span className="label">Номер:</span>
                <span className="value">{activeWaybill.number}</span>
                <StatusBadge status={activeWaybill.status} />
              </div>
              <div className="info-row">
                <span className="label">Транспорт:</span>
                <span className="value">
                  {activeWaybill.vehicle?.plate_number} - {activeWaybill.vehicle?.brand} {activeWaybill.vehicle?.model}
                </span>
              </div>
              <div className="info-row">
                <span className="label">Маршрут:</span>
                <span className="value">
                  {activeWaybill.route_from} - {activeWaybill.route_to}
                </span>
              </div>
              <div className="info-row">
                <span className="label">Дійсна до:</span>
                <span className="value">{formatDateTime(activeWaybill.valid_until)}</span>
              </div>
              <div className="info-row">
                <span className="label">Початковий пробіг:</span>
                <span className="value">{formatOdometer(activeWaybill.odometer_start)}</span>
              </div>
            </div>
            <button
              className="btn btn-primary"
              onClick={() => navigate(`/driver/waybills/${activeWaybill._id}`)}
            >
              Перейти до путівки
            </button>
          </div>
        ) : (
          <div className="empty-state">
            <p>Немає активної путівки</p>
          </div>
        )}
      </div>

      <div className="dashboard-grid">
        {/* Останні несправності */}
        <div className="card">
          <div className="card-header">
            <h3>Мої несправності</h3>
            <button
              className="btn btn-text"
              onClick={() => navigate('/driver/faults')}
            >
              Всі
            </button>
          </div>
          {recentFaults.length > 0 ? (
            <ul className="list">
              {recentFaults.map((fault) => (
                <li
                  key={fault._id}
                  className="list-item clickable"
                  onClick={() => navigate(`/driver/faults/${fault._id}`)}
                >
                  <div className="item-main">
                    <span className="item-title">{fault.number}</span>
                    <span className="item-subtitle">
                      {fault.vehicle?.plate_number} - {fault.category_display}
                    </span>
                  </div>
                  <StatusBadge status={fault.status} />
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state small">Немає несправностей</div>
          )}
          <div className="card-footer">
            <button
              className="btn btn-primary"
              onClick={() => navigate('/driver/faults/new')}
            >
              Повідомити про несправність
            </button>
          </div>
        </div>

        {/* Останні заправки */}
        <div className="card">
          <div className="card-header">
            <h3>Історія заправок</h3>
            <button
              className="btn btn-text"
              onClick={() => navigate('/driver/fuel')}
            >
              Всі
            </button>
          </div>
          {recentFuel.length > 0 ? (
            <ul className="list">
              {recentFuel.map((record) => (
                <li key={record._id} className="list-item">
                  <div className="item-main">
                    <span className="item-title">
                      {record.quantity} л - {record.vehicle?.plate_number}
                    </span>
                    <span className="item-subtitle">
                      {formatDateTime(record.date)}
                      {record.station && ` - ${record.station}`}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state small">Немає записів</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DriverDashboard
