import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useWaybillStore } from '../../store/waybillStore'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import ConfirmModal from '../../components/ConfirmModal'
import { formatDate, formatDateTime, formatOdometer } from '../../utils/formatters'
import { formatFuel } from '../../utils/fuelCalc'
import toast from 'react-hot-toast'
import { tr } from '../../i18n'

function DriverWaybillDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { currentWaybill, fetchWaybill, updateWaybill, isLoading } = useWaybillStore()

  const [showCompleteModal, setShowCompleteModal] = useState(false)
  const [odometerEnd, setOdometerEnd] = useState('')
  const [fuelUsed, setFuelUsed] = useState('')
  const [completionNotes, setCompletionNotes] = useState('')

  useEffect(() => {
    fetchWaybill(id)
  }, [id])

  const handleActivate = async () => {
    const result = await updateWaybill(id, { status: 'active' })
    if (result.success) {
      toast.success(tr("Путівку активовано"))
    }
  }

  const handleComplete = async () => {
    if (!odometerEnd) {
      toast.error(tr("Вкажіть кінцевий пробіг"))
      return
    }

    const result = await updateWaybill(id, {
      status: 'completed',
      odometer_end: parseInt(odometerEnd),
      fuel_used: fuelUsed ? parseFloat(fuelUsed) : null,
      completion_notes: completionNotes || null
    })

    if (result.success) {
      toast.success(tr("Путівку завершено"))
      setShowCompleteModal(false)
    }
  }

  if (isLoading || !currentWaybill) {
    return <Loader text={tr("Завантаження...")} />
  }

  const waybill = currentWaybill

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="header-left">
          <button className="btn btn-text" onClick={() => navigate(-1)}>
            {tr("Назад")}
          </button>
          <h1>{tr("Путівка")}{' '}{waybill.number}</h1>
          <StatusBadge status={waybill.status} />
        </div>

        <div className="header-actions">
          {waybill.status === 'issued' && (
            <button className="btn btn-primary" onClick={handleActivate}>
              {tr("Активувати")}
            </button>
          )}
          {waybill.status === 'active' && (
            <button
              className="btn btn-success"
              onClick={() => setShowCompleteModal(true)}
            >
              {tr("Завершити")}
            </button>
          )}
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3>{tr("Основна інформація")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Дата видачі")}</dt>
              <dd>{formatDate(waybill.issue_date)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Дійсна з")}</dt>
              <dd>{formatDateTime(waybill.valid_from)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Дійсна до")}</dt>
              <dd>{formatDateTime(waybill.valid_until)}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>{tr("Транспорт")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Номер")}</dt>
              <dd>{waybill.vehicle?.plate_number}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Марка/Модель")}</dt>
              <dd>{waybill.vehicle?.brand} {waybill.vehicle?.model}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Норма витрат")}</dt>
              <dd>{waybill.vehicle?.fuel_norm}{' '}{tr("л/100км")}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>{tr("Маршрут")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Звідки")}</dt>
              <dd>{waybill.route_from || '-'}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Куди")}</dt>
              <dd>{waybill.route_to || '-'}</dd>
            </div>
            {waybill.route_description && (
              <div className="info-item full">
                <dt>{tr("Опис маршруту")}</dt>
                <dd>{waybill.route_description}</dd>
              </div>
            )}
          </dl>
        </div>

        <div className="card">
          <h3>{tr("Пробіг та пальне")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Пробіг на початку")}</dt>
              <dd>{formatOdometer(waybill.odometer_start)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Пробіг в кінці")}</dt>
              <dd>{waybill.odometer_end ? formatOdometer(waybill.odometer_end) : '-'}</dd>
            </div>
            {waybill.odometer_end && (
              <div className="info-item">
                <dt>{tr("Пройдено")}</dt>
                <dd>{formatOdometer(waybill.odometer_end - waybill.odometer_start)}</dd>
              </div>
            )}
            <div className="info-item">
              <dt>{tr("Видано пального")}</dt>
              <dd>{formatFuel(waybill.fuel_issued)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Витрачено пального")}</dt>
              <dd>{waybill.fuel_used ? formatFuel(waybill.fuel_used) : '-'}</dd>
            </div>
          </dl>
        </div>

        {waybill.notes && (
          <div className="card full-width">
            <h3>{tr("Примітки")}</h3>
            <p>{waybill.notes}</p>
          </div>
        )}

        {waybill.completion_notes && (
          <div className="card full-width">
            <h3>{tr("Примітки при завершенні")}</h3>
            <p>{waybill.completion_notes}</p>
          </div>
        )}
      </div>

      {/* Модал завершення */}
      {showCompleteModal && (
        <div className="modal-overlay" onClick={() => setShowCompleteModal(false)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{tr("Завершення путівки")}</h3>
            </div>

            <div className="modal-body">
              <div className="form-field">
                <label htmlFor="odometerEnd">
                  {tr("Кінцевий пробіг (км)")}{' '}<span className="required">*</span>
                </label>
                <input
                  type="number"
                  id="odometerEnd"
                  className="form-control"
                  value={odometerEnd}
                  onChange={(e) => setOdometerEnd(e.target.value)}
                  min={waybill.odometer_start}
                  required
                />
                <span className="field-hint">
                  {tr("Початковий пробіг:")}{' '}{formatOdometer(waybill.odometer_start)}
                </span>
              </div>

              <div className="form-field">
                <label htmlFor="fuelUsed">{tr("Витрачено пального (л)")}</label>
                <input
                  type="number"
                  id="fuelUsed"
                  className="form-control"
                  value={fuelUsed}
                  onChange={(e) => setFuelUsed(e.target.value)}
                  min="0"
                  step="0.1"
                />
              </div>

              <div className="form-field">
                <label htmlFor="completionNotes">{tr("Примітки")}</label>
                <textarea
                  id="completionNotes"
                  className="form-control"
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
                  rows={3}
                />
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowCompleteModal(false)}
              >
                {tr("Скасувати")}
              </button>
              <button className="btn btn-success" onClick={handleComplete}>
                {tr("Завершити путівку")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DriverWaybillDetail
