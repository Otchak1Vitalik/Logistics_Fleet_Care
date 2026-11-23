import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useVehicleStore } from '../../store/vehicleStore'
import { vehiclesApi } from '../../api/vehicles'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDate, formatOdometer } from '../../utils/formatters'
import toast from 'react-hot-toast'

function MechanicVehicleDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { currentVehicle, fetchVehicle, updateVehicle, isLoading } = useVehicleStore()
  const [history, setHistory] = useState(null)

  useEffect(() => {
    fetchVehicle(id)
    loadHistory()
  }, [id])

  const loadHistory = async () => {
    try {
      const response = await vehiclesApi.getHistory(id)
      setHistory(response.data)
    } catch (error) {
      // Ігноруємо
    }
  }

  const handleStatusChange = async (newStatus) => {
    const result = await updateVehicle(id, { status: newStatus })
    if (result.success) {
      toast.success('Статус оновлено')
    }
  }

  if (isLoading || !currentVehicle) {
    return <Loader text="Завантаження..." />
  }

  const vehicle = currentVehicle

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="header-left">
          <button className="btn btn-text" onClick={() => navigate(-1)}>
            Назад
          </button>
          <h1>{vehicle.plate_number}</h1>
          <StatusBadge status={vehicle.status} />
        </div>

        <div className="header-actions">
          {vehicle.status === 'active' && (
            <button
              className="btn btn-warning"
              onClick={() => handleStatusChange('repair')}
            >
              Взяти в ремонт
            </button>
          )}
          {vehicle.status === 'repair' && (
            <button
              className="btn btn-success"
              onClick={() => handleStatusChange('active')}
            >
              Повернути в роботу
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={() => navigate('/mechanic/repairs/new', { state: { vehicleId: id } })}
          >
            Створити ремонт
          </button>
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3>Основна інформація</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>Марка</dt>
              <dd>{vehicle.brand}</dd>
            </div>
            <div className="info-item">
              <dt>Модель</dt>
              <dd>{vehicle.model}</dd>
            </div>
            <div className="info-item">
              <dt>Рік випуску</dt>
              <dd>{vehicle.year || '-'}</dd>
            </div>
            <div className="info-item">
              <dt>VIN</dt>
              <dd>{vehicle.vin || '-'}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>Пробіг та ТО</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>Поточний пробіг</dt>
              <dd>{formatOdometer(vehicle.odometer)}</dd>
            </div>
            <div className="info-item">
              <dt>Останнє ТО (км)</dt>
              <dd>{formatOdometer(vehicle.last_maintenance_km)}</dd>
            </div>
            <div className="info-item">
              <dt>Останнє ТО (дата)</dt>
              <dd>{formatDate(vehicle.last_maintenance_date)}</dd>
            </div>
            <div className="info-item">
              <dt>Наступне ТО (км)</dt>
              <dd>{formatOdometer(vehicle.next_maintenance_km)}</dd>
            </div>
            <div className="info-item">
              <dt>Наступне ТО (дата)</dt>
              <dd>{formatDate(vehicle.next_maintenance_date)}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>Паливо</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>Тип пального</dt>
              <dd>
                {vehicle.fuel_type === 'diesel'
                  ? 'Дизель'
                  : vehicle.fuel_type === 'petrol'
                  ? 'Бензин'
                  : 'Газ'}
              </dd>
            </div>
            <div className="info-item">
              <dt>Норма витрат</dt>
              <dd>{vehicle.fuel_norm} л/100км</dd>
            </div>
            <div className="info-item">
              <dt>Об\'єм баку</dt>
              <dd>{vehicle.tank_capacity ? `${vehicle.tank_capacity} л` : '-'}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>Документи</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>Техогляд до</dt>
              <dd>{formatDate(vehicle.inspection_expiry)}</dd>
            </div>
            <div className="info-item">
              <dt>Страховка</dt>
              <dd>{vehicle.insurance_policy || '-'}</dd>
            </div>
            <div className="info-item">
              <dt>Страховка до</dt>
              <dd>{formatDate(vehicle.insurance_expiry)}</dd>
            </div>
          </dl>
        </div>

        {/* Історія ремонтів */}
        {history?.repairs && history.repairs.length > 0 && (
          <div className="card full-width">
            <h3>Останні ремонти</h3>
            <ul className="list">
              {history.repairs.map((repair) => (
                <li
                  key={repair._id}
                  className="list-item clickable"
                  onClick={() => navigate(`/mechanic/repairs/${repair._id}`)}
                >
                  <div className="item-main">
                    <span className="item-title">{repair.number}</span>
                    <span className="item-subtitle">{repair.description}</span>
                  </div>
                  <StatusBadge status={repair.status} />
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Історія несправностей */}
        {history?.faults && history.faults.length > 0 && (
          <div className="card full-width">
            <h3>Останні несправності</h3>
            <ul className="list">
              {history.faults.map((fault) => (
                <li
                  key={fault._id}
                  className="list-item clickable"
                  onClick={() => navigate(`/mechanic/faults/${fault._id}`)}
                >
                  <div className="item-main">
                    <span className="item-title">{fault.number}</span>
                    <span className="item-subtitle">{fault.description}</span>
                  </div>
                  <StatusBadge status={fault.status} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

export default MechanicVehicleDetail
