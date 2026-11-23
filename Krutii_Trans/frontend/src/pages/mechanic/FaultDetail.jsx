import { useEffect, useState } from 'react'
import { useRoleBase } from '../../utils/useRoleBase'
import { useParams, useNavigate } from 'react-router-dom'
import { faultsApi } from '../../api/faults'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDateTime, formatOdometer } from '../../utils/formatters'
import toast from 'react-hot-toast'
import { tr } from '../../i18n'

function MechanicFaultDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const base = useRoleBase()
  const [fault, setFault] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showResolveModal, setShowResolveModal] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [resolution, setResolution] = useState('')
  const [rejectionReason, setRejectionReason] = useState('')

  useEffect(() => {
    loadFault()
  }, [id])

  const loadFault = async () => {
    setIsLoading(true)
    try {
      const response = await faultsApi.getById(id)
      setFault(response.data.fault)
    } catch (error) {
      // Ігноруємо
    }
    setIsLoading(false)
  }

  const handleAcknowledge = async () => {
    try {
      await faultsApi.update(id, { status: 'acknowledged' })
      toast.success(tr("Несправність прийнято в роботу"))
      loadFault()
    } catch (error) {
      // Ігноруємо
    }
  }

  const handleResolve = async () => {
    if (!resolution.trim()) {
      toast.error(tr("Вкажіть опис рішення"))
      return
    }
    try {
      await faultsApi.update(id, { status: 'resolved', resolution })
      toast.success(tr("Несправність вирішено"))
      setShowResolveModal(false)
      loadFault()
    } catch (error) {
      // Ігноруємо
    }
  }

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      toast.error(tr("Вкажіть причину відхилення"))
      return
    }
    try {
      await faultsApi.update(id, { status: 'rejected', rejection_reason: rejectionReason })
      toast.success(tr("Несправність відхилено"))
      setShowRejectModal(false)
      loadFault()
    } catch (error) {
      // Ігноруємо
    }
  }

  const handleCreateRepair = () => {
    navigate(`${base}/repairs/new`, { state: { faultId: id, vehicleId: fault.vehicle_id } })
  }

  if (isLoading || !fault) {
    return <Loader text={tr("Завантаження...")} />
  }

  const canAcknowledge = fault.status === 'new'
  const canResolve = ['acknowledged', 'in_repair'].includes(fault.status)
  const canReject = fault.status === 'new'
  const canCreateRepair = ['new', 'acknowledged'].includes(fault.status)

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="header-left">
          <button className="btn btn-text" onClick={() => navigate(-1)}>
            {tr("Назад")}
          </button>
          <h1>{tr("Несправність")}{' '}{fault.number}</h1>
          <StatusBadge status={fault.status} />
        </div>

        <div className="header-actions">
          {canAcknowledge && (
            <button className="btn btn-primary" onClick={handleAcknowledge}>
              {tr("Прийняти")}
            </button>
          )}
          {canCreateRepair && (
            <button className="btn btn-info" onClick={handleCreateRepair}>
              {tr("Створити ремонт")}
            </button>
          )}
          {canResolve && (
            <button
              className="btn btn-success"
              onClick={() => setShowResolveModal(true)}
            >
              {tr("Вирішено")}
            </button>
          )}
          {canReject && (
            <button
              className="btn btn-danger"
              onClick={() => setShowRejectModal(true)}
            >
              {tr("Відхилити")}
            </button>
          )}
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3>{tr("Транспорт")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Номер")}</dt>
              <dd>{fault.vehicle?.plate_number}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Марка/Модель")}</dt>
              <dd>
                {fault.vehicle?.brand} {fault.vehicle?.model}
              </dd>
            </div>
            <div className="info-item">
              <dt>{tr("Пробіг")}</dt>
              <dd>{formatOdometer(fault.odometer)}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>{tr("Деталі несправності")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Дата повідомлення")}</dt>
              <dd>{formatDateTime(fault.report_date)}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Категорія")}</dt>
              <dd>{fault.category_display || fault.category}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Критичність")}</dt>
              <dd
                className={
                  fault.severity === 'critical'
                    ? 'text-danger'
                    : fault.severity === 'high'
                    ? 'text-warning'
                    : ''
                }
              >
                {fault.severity_display || fault.severity}
              </dd>
            </div>
            <div className="info-item">
              <dt>{tr("Від водія")}</dt>
              <dd>{fault.reporter?.full_name}</dd>
            </div>
          </dl>
        </div>

        <div className="card full-width">
          <h3>{tr("Опис")}</h3>
          <p className="description-text">{fault.description}</p>
        </div>

        {fault.resolution && (
          <div className="card full-width">
            <h3>{tr("Рішення")}</h3>
            <p className="description-text">{fault.resolution}</p>
          </div>
        )}

        {fault.rejection_reason && (
          <div className="card full-width">
            <h3>{tr("Причина відхилення")}</h3>
            <p className="description-text">{fault.rejection_reason}</p>
          </div>
        )}
      </div>

      {/* Модал рішення */}
      {showResolveModal && (
        <div className="modal-overlay" onClick={() => setShowResolveModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{tr("Рішення несправності")}</h3>
            </div>
            <div className="modal-body">
              <div className="form-field">
                <label>{tr("Опис виконаних робіт")}</label>
                <textarea
                  className="form-control"
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                  rows={4}
                  placeholder={tr("Опишіть, що було зроблено...")}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowResolveModal(false)}
              >
                {tr("Скасувати")}
              </button>
              <button className="btn btn-success" onClick={handleResolve}>
                {tr("Підтвердити")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Модал відхилення */}
      {showRejectModal && (
        <div className="modal-overlay" onClick={() => setShowRejectModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{tr("Відхилення несправності")}</h3>
            </div>
            <div className="modal-body">
              <div className="form-field">
                <label>{tr("Причина відхилення")}</label>
                <textarea
                  className="form-control"
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  rows={4}
                  placeholder={tr("Вкажіть причину...")}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowRejectModal(false)}
              >
                {tr("Скасувати")}
              </button>
              <button className="btn btn-danger" onClick={handleReject}>
                {tr("Відхилити")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MechanicFaultDetail
