import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useVehicleStore } from '../../store/vehicleStore'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDate, formatOdometer } from '../../utils/formatters'
import toast from 'react-hot-toast'
import VehicleInsights from '../../components/VehicleInsights'
import { tr } from '../../i18n'

function MechanicVehicleDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { currentVehicle, fetchVehicle, updateVehicle, isLoading } = useVehicleStore()

  useEffect(() => {
    fetchVehicle(id)
  }, [id])

  const handleStatusChange = async (newStatus) => {
    const result = await updateVehicle(id, { status: newStatus })
    if (result.success) {
      toast.success(tr("Статус оновлено"))
    }
  }

  if (isLoading || !currentVehicle) {
    return <Loader text={tr("Завантаження...")} />
  }

  const vehicle = currentVehicle

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="header-left">
          <button className="btn btn-text" onClick={() => navigate(-1)}>
            {tr("Назад")}
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
              {tr("Взяти в ремонт")}
            </button>
          )}
          {vehicle.status === 'repair' && (
            <button
              className="btn btn-success"
              onClick={() => handleStatusChange('active')}
            >
              {tr("Повернути в роботу")}
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={() => navigate('/mechanic/repairs/new', { state: { vehicleId: id } })}
          >
            {tr("Створити ремонт")}
          </button>
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3>{tr("Основна інформація")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Марка")}</dt>
              <dd>{vehicle.brand}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Модель")}</dt>
              <dd>{vehicle.model}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Рік випуску")}</dt>
              <dd>{vehicle.year || '-'}</dd>
            </div>
            <div className="info-item">
              <dt>VIN</dt>
              <dd>{vehicle.vin || '-'}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>{tr("Пробіг та ТО")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Поточний пробіг")}</dt>
              <dd>{formatOdometer(vehicle.odometer)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Останнє ТО (км)")}</dt>
              <dd>{formatOdometer(vehicle.last_maintenance_km)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Останнє ТО (дата)")}</dt>
              <dd>{formatDate(vehicle.last_maintenance_date)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Наступне ТО (км)")}</dt>
              <dd>{formatOdometer(vehicle.next_maintenance_km)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Наступне ТО (дата)")}</dt>
              <dd>{formatDate(vehicle.next_maintenance_date)}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>{tr("Паливо")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Тип пального")}</dt>
              <dd>
                {vehicle.fuel_type === 'diesel'
                  ? tr("Дизель")
                  : vehicle.fuel_type === 'petrol'
                  ? tr("Бензин")
                  : tr("Газ")}
              </dd>
            </div>
            <div className="info-item">
              <dt>{tr("Норма витрат")}</dt>
              <dd>{vehicle.fuel_norm}{' '}{tr("л/100км")}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Об'єм баку")}</dt>
              <dd>{vehicle.tank_capacity ? tr("{0} л", vehicle.tank_capacity) : '-'}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>{tr("Документи")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Техогляд до")}</dt>
              <dd>{formatDate(vehicle.inspection_expiry)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Страховка")}</dt>
              <dd>{vehicle.insurance_policy || '-'}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Страховка до")}</dt>
              <dd>{formatDate(vehicle.insurance_expiry)}</dd>
            </div>
          </dl>
        </div>

        {/* Прогноз ТО, підсумки та історія автомобіля */}
        <VehicleInsights vehicleId={id} />
      </div>
    </div>
  )
}

export default MechanicVehicleDetail
