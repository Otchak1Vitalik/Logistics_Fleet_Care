import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { waybillsApi } from '../../api/waybills'
import toast from 'react-hot-toast'
import Loader from '../../components/Loader'
import StatusBadge from '../../components/StatusBadge'
import ConfirmModal from '../../components/ConfirmModal'
import { formatDate, formatDateTime, formatOdometer } from '../../utils/formatters'
import { tr } from '../../i18n'

function WaybillDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [waybill, setWaybill] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showCancelModal, setShowCancelModal] = useState(false)
  const [cancelReason, setCancelReason] = useState('')

  useEffect(() => {
    loadWaybill()
  }, [id])

  const loadWaybill = async () => {
    try {
      const response = await waybillsApi.getById(id)
      setWaybill(response.data.waybill)
    } catch (error) {
      navigate('/manager/waybills')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async () => {
    try {
      await waybillsApi.cancel(id, cancelReason)
      toast.success(tr("Путівку скасовано"))
      setShowCancelModal(false)
      loadWaybill()
    } catch (error) {
      // Помилка оброблена в interceptor
    }
  }

  if (loading) {
    return <Loader text={tr("Завантаження...")} />
  }

  if (!waybill) {
    return (
      <div className="page-container">
        <div className="empty-state">{tr("Путівку не знайдено")}</div>
      </div>
    )
  }

  const distance = waybill.odometer_end && waybill.odometer_start
    ? waybill.odometer_end - waybill.odometer_start
    : null

  return (
    <div className="page-container">
      <Link to="/manager/waybills" className="back-link">
        {tr("← Назад до списку")}
      </Link>

      <div className="detail-header">
        <div className="detail-title">
          <h1>{tr("Путівка")}{' '}{waybill.number}</h1>
          <StatusBadge status={waybill.status} />
        </div>
        <div className="detail-actions">
          {(waybill.status === 'issued' || waybill.status === 'active') && (
            <button
              className="btn btn-danger"
              onClick={() => setShowCancelModal(true)}
            >
              {tr("Скасувати")}
            </button>
          )}
        </div>
      </div>

      <div className="card">
        <div className="detail-section">
          <h3>{tr("Основна інформація")}</h3>
          <div className="info-grid">
            <div className="info-row">
              <span className="label">{tr("Дата видачі")}</span>
              <span className="value">{formatDate(waybill.issue_date)}</span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Дійсна з")}</span>
              <span className="value">{formatDateTime(waybill.valid_from)}</span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Дійсна до")}</span>
              <span className="value">{formatDateTime(waybill.valid_until)}</span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Видав")}</span>
              <span className="value">{waybill.issuer?.full_name || '-'}</span>
            </div>
          </div>
        </div>

        <div className="detail-section">
          <h3>{tr("Транспорт та водій")}</h3>
          <div className="info-grid">
            <div className="info-row">
              <span className="label">{tr("Транспорт")}</span>
              <span className="value">
                {waybill.vehicle?.plate_number} - {waybill.vehicle?.brand} {waybill.vehicle?.model}
              </span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Водій")}</span>
              <span className="value">{waybill.driver?.full_name}</span>
            </div>
          </div>
        </div>

        <div className="detail-section">
          <h3>{tr("Маршрут")}</h3>
          <div className="info-grid">
            <div className="info-row">
              <span className="label">{tr("Звідки")}</span>
              <span className="value">{waybill.route_from || '-'}</span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Куди")}</span>
              <span className="value">{waybill.route_to || '-'}</span>
            </div>
            {waybill.route_description && (
              <div className="info-row" style={{ gridColumn: '1 / -1' }}>
                <span className="label">{tr("Опис маршруту")}</span>
                <span className="value">{waybill.route_description}</span>
              </div>
            )}
          </div>
        </div>

        <div className="detail-section">
          <h3>{tr("Пробіг")}</h3>
          <div className="info-grid">
            <div className="info-row">
              <span className="label">{tr("Початковий")}</span>
              <span className="value">{formatOdometer(waybill.odometer_start)}</span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Кінцевий")}</span>
              <span className="value">{waybill.odometer_end ? formatOdometer(waybill.odometer_end) : '-'}</span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Пройдено")}</span>
              <span className="value font-bold">
                {distance !== null ? tr("{0} км", distance.toLocaleString()) : '-'}
              </span>
            </div>
          </div>
        </div>

        <div className="detail-section">
          <h3>{tr("Пальне")}</h3>
          <div className="info-grid">
            <div className="info-row">
              <span className="label">{tr("Видано")}</span>
              <span className="value">{waybill.fuel_issued ? tr("{0} л", waybill.fuel_issued) : '-'}</span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Витрачено")}</span>
              <span className="value">{waybill.fuel_used ? tr("{0} л", waybill.fuel_used) : '-'}</span>
            </div>
            <div className="info-row">
              <span className="label">{tr("Залишок")}</span>
              <span className="value">{waybill.fuel_remaining ? tr("{0} л", waybill.fuel_remaining) : '-'}</span>
            </div>
            {distance && waybill.fuel_used && (
              <div className="info-row">
                <span className="label">{tr("Фактичні витрати")}</span>
                <span className="value font-bold">
                  {((waybill.fuel_used / distance) * 100).toFixed(1)}{' '}{tr("л/100км")}
                </span>
              </div>
            )}
          </div>
        </div>

        {(waybill.notes || waybill.completion_notes) && (
          <div className="detail-section">
            <h3>{tr("Примітки")}</h3>
            {waybill.notes && (
              <div className="info-row">
                <span className="label">{tr("Примітки при видачі")}</span>
                <span className="value">{waybill.notes}</span>
              </div>
            )}
            {waybill.completion_notes && (
              <div className="info-row">
                <span className="label">{tr("Примітки при завершенні")}</span>
                <span className="value">{waybill.completion_notes}</span>
              </div>
            )}
          </div>
        )}

        {waybill.completed_at && (
          <div className="detail-section">
            <h3>{tr("Завершення")}</h3>
            <div className="info-row">
              <span className="label">{tr("Дата завершення")}</span>
              <span className="value">{formatDateTime(waybill.completed_at)}</span>
            </div>
          </div>
        )}
      </div>

      {/* Модалка скасування */}
      {showCancelModal && (
        <ConfirmModal
          title={tr("Скасування путівки")}
          onClose={() => {
            setShowCancelModal(false)
            setCancelReason('')
          }}
          onConfirm={handleCancel}
          confirmText={tr("Скасувати путівку")}
          confirmVariant="danger"
        >
          <p className="mb-md">{tr("Ви впевнені, що хочете скасувати цю путівку?")}</p>
          <div className="form-field">
            <label>{tr("Причина скасування")}</label>
            <textarea
              className="form-control"
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              rows={3}
              placeholder={tr("Вкажіть причину...")}
            />
          </div>
        </ConfirmModal>
      )}
    </div>
  )
}

export default WaybillDetail
