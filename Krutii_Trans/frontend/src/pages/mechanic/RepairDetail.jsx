import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { repairsApi } from '../../api/repairs'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDate, formatDateTime, formatOdometer, formatCurrency } from '../../utils/formatters'
import toast from 'react-hot-toast'

function MechanicRepairDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [repair, setRepair] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showCompleteModal, setShowCompleteModal] = useState(false)
  const [workPerformed, setWorkPerformed] = useState('')
  const [laborHours, setLaborHours] = useState('')
  const [laborCost, setLaborCost] = useState('')
  const [partsCost, setPartsCost] = useState('')

  useEffect(() => {
    loadRepair()
  }, [id])

  const loadRepair = async () => {
    setIsLoading(true)
    try {
      const response = await repairsApi.getById(id)
      setRepair(response.data.repair)
    } catch (error) {
      // Ігноруємо
    }
    setIsLoading(false)
  }

  const handleStart = async () => {
    try {
      await repairsApi.update(id, { status: 'in_progress' })
      toast.success('Ремонт розпочато')
      loadRepair()
    } catch (error) {
      // Ігноруємо
    }
  }

  const handleComplete = async () => {
    if (!workPerformed.trim()) {
      toast.error('Вкажіть виконані роботи')
      return
    }
    try {
      await repairsApi.update(id, {
        status: 'completed',
        work_performed: workPerformed,
        labor_hours: laborHours ? parseFloat(laborHours) : null,
        labor_cost: laborCost ? parseFloat(laborCost) : null,
        parts_cost: partsCost ? parseFloat(partsCost) : null
      })
      toast.success('Ремонт завершено')
      setShowCompleteModal(false)
      loadRepair()
    } catch (error) {
      // Ігноруємо
    }
  }

  const handleCancel = async () => {
    const reason = prompt('Причина скасування:')
    if (!reason) return

    try {
      await repairsApi.update(id, { status: 'cancelled', cancellation_reason: reason })
      toast.success('Ремонт скасовано')
      loadRepair()
    } catch (error) {
      // Ігноруємо
    }
  }

  if (isLoading || !repair) {
    return <Loader text="Завантаження..." />
  }

  const canStart = repair.status === 'planned'
  const canComplete = repair.status === 'in_progress'
  const canCancel = ['planned', 'in_progress'].includes(repair.status)

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="header-left">
          <button className="btn btn-text" onClick={() => navigate(-1)}>
            Назад
          </button>
          <h1>Ремонт {repair.number}</h1>
          <StatusBadge status={repair.status} />
        </div>

        <div className="header-actions">
          {canStart && (
            <button className="btn btn-primary" onClick={handleStart}>
              Розпочати
            </button>
          )}
          {canComplete && (
            <button
              className="btn btn-success"
              onClick={() => setShowCompleteModal(true)}
            >
              Завершити
            </button>
          )}
          {canCancel && (
            <button className="btn btn-danger" onClick={handleCancel}>
              Скасувати
            </button>
          )}
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3>Транспорт</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>Номер</dt>
              <dd>{repair.vehicle?.plate_number}</dd>
            </div>
            <div className="info-item">
              <dt>Марка/Модель</dt>
              <dd>
                {repair.vehicle?.brand} {repair.vehicle?.model}
              </dd>
            </div>
            <div className="info-item">
              <dt>Пробіг</dt>
              <dd>{formatOdometer(repair.odometer)}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>Деталі ремонту</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>Тип</dt>
              <dd>{repair.repair_type_display || repair.repair_type}</dd>
            </div>
            <div className="info-item">
              <dt>Запланована дата</dt>
              <dd>{formatDate(repair.scheduled_date)}</dd>
            </div>
            {repair.started_at && (
              <div className="info-item">
                <dt>Розпочато</dt>
                <dd>{formatDateTime(repair.started_at)}</dd>
              </div>
            )}
            {repair.completed_at && (
              <div className="info-item">
                <dt>Завершено</dt>
                <dd>{formatDateTime(repair.completed_at)}</dd>
              </div>
            )}
            <div className="info-item">
              <dt>Механік</dt>
              <dd>{repair.mechanic?.full_name || '-'}</dd>
            </div>
          </dl>
        </div>

        <div className="card full-width">
          <h3>Опис</h3>
          <p className="description-text">{repair.description}</p>
        </div>

        {repair.work_performed && (
          <div className="card full-width">
            <h3>Виконані роботи</h3>
            <p className="description-text">{repair.work_performed}</p>
          </div>
        )}

        {repair.status === 'completed' && (
          <div className="card">
            <h3>Витрати</h3>
            <dl className="info-list">
              <div className="info-item">
                <dt>Години роботи</dt>
                <dd>{repair.labor_hours ? `${repair.labor_hours} год` : '-'}</dd>
              </div>
              <div className="info-item">
                <dt>Вартість роботи</dt>
                <dd>{formatCurrency(repair.labor_cost)}</dd>
              </div>
              <div className="info-item">
                <dt>Вартість запчастин</dt>
                <dd>{formatCurrency(repair.parts_cost)}</dd>
              </div>
              <div className="info-item">
                <dt>Загалом</dt>
                <dd className="text-bold">
                  {formatCurrency((repair.labor_cost || 0) + (repair.parts_cost || 0))}
                </dd>
              </div>
            </dl>
          </div>
        )}

        {repair.notes && (
          <div className="card">
            <h3>Примітки</h3>
            <p>{repair.notes}</p>
          </div>
        )}

        {repair.cancellation_reason && (
          <div className="card">
            <h3>Причина скасування</h3>
            <p>{repair.cancellation_reason}</p>
          </div>
        )}
      </div>

      {/* Модал завершення */}
      {showCompleteModal && (
        <div className="modal-overlay" onClick={() => setShowCompleteModal(false)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Завершення ремонту</h3>
            </div>
            <div className="modal-body">
              <div className="form-field">
                <label>Виконані роботи *</label>
                <textarea
                  className="form-control"
                  value={workPerformed}
                  onChange={(e) => setWorkPerformed(e.target.value)}
                  rows={4}
                  placeholder="Опишіть виконані роботи..."
                />
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label>Години роботи</label>
                  <input
                    type="number"
                    className="form-control"
                    value={laborHours}
                    onChange={(e) => setLaborHours(e.target.value)}
                    min="0"
                    step="0.5"
                  />
                </div>
                <div className="form-field">
                  <label>Вартість роботи (грн)</label>
                  <input
                    type="number"
                    className="form-control"
                    value={laborCost}
                    onChange={(e) => setLaborCost(e.target.value)}
                    min="0"
                  />
                </div>
                <div className="form-field">
                  <label>Вартість запчастин (грн)</label>
                  <input
                    type="number"
                    className="form-control"
                    value={partsCost}
                    onChange={(e) => setPartsCost(e.target.value)}
                    min="0"
                  />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowCompleteModal(false)}
              >
                Скасувати
              </button>
              <button className="btn btn-success" onClick={handleComplete}>
                Завершити
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MechanicRepairDetail
