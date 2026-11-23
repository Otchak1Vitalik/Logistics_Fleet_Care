import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { repairsApi } from '../../api/repairs'
import { partsApi } from '../../api/parts'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDate, formatDateTime, formatOdometer, formatCurrency } from '../../utils/formatters'
import toast from 'react-hot-toast'
import { tr } from '../../i18n'

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
  const [stock, setStock] = useState([])          // запчастини складу
  const [usedParts, setUsedParts] = useState([])  // [{ part_id, quantity }]

  const openCompleteModal = async () => {
    setShowCompleteModal(true)
    try {
      const res = await partsApi.getAll()
      setStock(res.data.parts)
    } catch (e) { /* склад недоступний - можна завершити без запчастин */ }
  }

  const stockById = Object.fromEntries(stock.map((p) => [p._id, p]))
  const usedTotal = usedParts.reduce((sum, u) => sum + (stockById[u.part_id]?.price || 0) * (Number(u.quantity) || 0), 0)
  const updateUsed = (idx, patch) => setUsedParts(usedParts.map((u, i) => (i === idx ? { ...u, ...patch } : u)))

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
      toast.success(tr("Ремонт розпочато"))
      loadRepair()
    } catch (error) {
      // Ігноруємо
    }
  }

  const handleComplete = async () => {
    if (!workPerformed.trim()) {
      toast.error(tr("Вкажіть виконані роботи"))
      return
    }
    try {
      await repairsApi.update(id, {
        status: 'completed',
        work_performed: workPerformed,
        labor_hours: laborHours ? parseFloat(laborHours) : null,
        labor_cost: laborCost ? parseFloat(laborCost) : null,
        parts_cost: partsCost ? parseFloat(partsCost) : null,
        // Використані запчастини списуються зі складу; якщо вартість не вказана, вона рахується автоматично
        parts_used: usedParts
          .filter((u) => u.part_id && Number(u.quantity) > 0)
          .map((u) => ({ part_id: u.part_id, quantity: Number(u.quantity) }))
      })
      toast.success(tr("Ремонт завершено"))
      setShowCompleteModal(false)
      loadRepair()
    } catch (error) {
      // Ігноруємо
    }
  }

  const handleCancel = async () => {
    const reason = prompt(tr("Причина скасування:"))
    if (!reason) return

    try {
      await repairsApi.update(id, { status: 'cancelled', cancellation_reason: reason })
      toast.success(tr("Ремонт скасовано"))
      loadRepair()
    } catch (error) {
      // Ігноруємо
    }
  }

  if (isLoading || !repair) {
    return <Loader text={tr("Завантаження...")} />
  }

  const canStart = repair.status === 'planned'
  const canComplete = repair.status === 'in_progress'
  const canCancel = ['planned', 'in_progress'].includes(repair.status)

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="header-left">
          <button className="btn btn-text" onClick={() => navigate(-1)}>
            {tr("Назад")}
          </button>
          <h1>{tr("Ремонт")}{' '}{repair.number}</h1>
          <StatusBadge status={repair.status} />
        </div>

        <div className="header-actions">
          {canStart && (
            <button className="btn btn-primary" onClick={handleStart}>
              {tr("Розпочати")}
            </button>
          )}
          {canComplete && (
            <button
              className="btn btn-success"
              onClick={openCompleteModal}
            >
              {tr("Завершити")}
            </button>
          )}
          {canCancel && (
            <button className="btn btn-danger" onClick={handleCancel}>
              {tr("Скасувати")}
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
              <dd>{repair.vehicle?.plate_number}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Марка/Модель")}</dt>
              <dd>
                {repair.vehicle?.brand} {repair.vehicle?.model}
              </dd>
            </div>
            <div className="info-item">
              <dt>{tr("Пробіг")}</dt>
              <dd>{formatOdometer(repair.odometer)}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>{tr("Деталі ремонту")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Тип")}</dt>
              <dd>{repair.repair_type_display || repair.repair_type}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Запланована дата")}</dt>
              <dd>{formatDate(repair.scheduled_date)}</dd>
            </div>
            {repair.started_at && (
              <div className="info-item">
                <dt>{tr("Розпочато")}</dt>
                <dd>{formatDateTime(repair.started_at)}</dd>
              </div>
            )}
            {repair.completed_at && (
              <div className="info-item">
                <dt>{tr("Завершено")}</dt>
                <dd>{formatDateTime(repair.completed_at)}</dd>
              </div>
            )}
            <div className="info-item">
              <dt>{tr("Механік")}</dt>
              <dd>{repair.mechanic?.full_name || '-'}</dd>
            </div>
          </dl>
        </div>

        <div className="card full-width">
          <h3>{tr("Опис")}</h3>
          <p className="description-text">{repair.description}</p>
        </div>

        {repair.work_performed && (
          <div className="card full-width">
            <h3>{tr("Виконані роботи")}</h3>
            <p className="description-text">{repair.work_performed}</p>
          </div>
        )}

        {repair.status === 'completed' && (
          <div className="card">
            <h3>{tr("Витрати")}</h3>
            <dl className="info-list">
              <div className="info-item">
                <dt>{tr("Години роботи")}</dt>
                <dd>{repair.labor_hours ? tr("{0} год", repair.labor_hours) : '-'}</dd>
              </div>
              <div className="info-item">
                <dt>{tr("Вартість роботи")}</dt>
                <dd>{formatCurrency(repair.labor_cost)}</dd>
              </div>
              <div className="info-item">
                <dt>{tr("Вартість запчастин")}</dt>
                <dd>{formatCurrency(repair.parts_cost)}</dd>
              </div>
              <div className="info-item">
                <dt>{tr("Загалом")}</dt>
                <dd className="text-bold">
                  {formatCurrency((repair.labor_cost || 0) + (repair.parts_cost || 0))}
                </dd>
              </div>
            </dl>
            {repair.parts_used?.length > 0 && (
              <>
                <h4 className="mt-md">{tr("Використані запчастини")}</h4>
                <ul className="list">
                  {repair.parts_used.map((p, i) => (
                    <li key={i} className="list-item">
                      <div className="item-main">
                        <span className="item-title">{p.name}</span>
                        <span className="item-subtitle">{p.quantity} {tr(p.unit)} × {formatCurrency(p.price)} = {formatCurrency(p.cost)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        {repair.notes && (
          <div className="card">
            <h3>{tr("Примітки")}</h3>
            <p>{repair.notes}</p>
          </div>
        )}

        {repair.cancellation_reason && (
          <div className="card">
            <h3>{tr("Причина скасування")}</h3>
            <p>{repair.cancellation_reason}</p>
          </div>
        )}
      </div>

      {/* Модал завершення */}
      {showCompleteModal && (
        <div className="modal-overlay" onClick={() => setShowCompleteModal(false)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{tr("Завершення ремонту")}</h3>
            </div>
            <div className="modal-body">
              <div className="form-field">
                <label>{tr("Виконані роботи *")}</label>
                <textarea
                  className="form-control"
                  value={workPerformed}
                  onChange={(e) => setWorkPerformed(e.target.value)}
                  rows={4}
                  placeholder={tr("Опишіть виконані роботи...")}
                />
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label>{tr("Години роботи")}</label>
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
                  <label>{tr("Вартість роботи (грн)")}</label>
                  <input
                    type="number"
                    className="form-control"
                    value={laborCost}
                    onChange={(e) => setLaborCost(e.target.value)}
                    min="0"
                  />
                </div>
                <div className="form-field">
                  <label>{tr("Вартість запчастин (грн)")}</label>
                  <input
                    type="number"
                    className="form-control"
                    value={partsCost}
                    onChange={(e) => setPartsCost(e.target.value)}
                    min="0"
                    placeholder={usedTotal > 0 ? String(usedTotal) : ''}
                  />
                  {usedTotal > 0 && !partsCost && (
                    <div className="form-hint">{tr("Буде розраховано за складом: {0}", formatCurrency(usedTotal))}</div>
                  )}
                </div>
              </div>

              <div className="form-field">
                <label>{tr("Використані запчастини (списуються зі складу)")}</label>
                {usedParts.map((u, idx) => {
                  const part = stockById[u.part_id]
                  const tooMuch = part && Number(u.quantity) > part.quantity
                  return (
                    <div key={idx} className="parts-row">
                      <select className="form-control" value={u.part_id} onChange={(e) => updateUsed(idx, { part_id: e.target.value })}>
                        <option value="">{tr("Оберіть запчастину...")}</option>
                        {stock.map((p) => (
                          <option key={p._id} value={p._id} disabled={p.quantity <= 0}>
                            {tr("{0} (залишок {1} {2})", p.name, p.quantity, tr(p.unit))}
                          </option>
                        ))}
                      </select>
                      <input type="number" min="0" step="1" className={`form-control parts-qty ${tooMuch ? 'is-invalid' : ''}`}
                        value={u.quantity} onChange={(e) => updateUsed(idx, { quantity: e.target.value })} />
                      <button type="button" className="btn btn-text" onClick={() => setUsedParts(usedParts.filter((_, i) => i !== idx))}
                        aria-label={tr("Прибрати")}>✕</button>
                      {tooMuch && <div className="form-error parts-error">{tr("Недостатньо на складі")}</div>}
                    </div>
                  )
                })}
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setUsedParts([...usedParts, { part_id: '', quantity: 1 }])}>
                  {tr("+ Додати запчастину")}
                </button>
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
                {tr("Завершити")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MechanicRepairDetail
