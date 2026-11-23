import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { faultsApi } from '../../api/faults'
import StatusBadge from '../../components/StatusBadge'
import Loader from '../../components/Loader'
import { formatDateTime, formatOdometer } from '../../utils/formatters'
import { tr } from '../../i18n'

function DriverFaultDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [fault, setFault] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

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

  if (isLoading || !fault) {
    return <Loader text={tr("Завантаження...")} />
  }

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
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3>{tr("Основна інформація")}</h3>
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
              <dd>{fault.severity_display || fault.severity}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Пробіг")}</dt>
              <dd>{formatOdometer(fault.odometer)}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>{tr("Транспорт")}</h3>
          <dl className="info-list">
            <div className="info-item">
              <dt>{tr("Номер")}</dt>
              <dd>{fault.vehicle?.plate_number}</dd>
            </div>
            <div className="info-item">
              <dt>{tr("Марка/Модель")}</dt>
              <dd>{fault.vehicle?.brand} {fault.vehicle?.model}</dd>
            </div>
          </dl>
        </div>

        <div className="card full-width">
          <h3>{tr("Опис несправності")}</h3>
          <p className="description-text">{fault.description}</p>
        </div>

        {fault.status !== 'new' && (
          <div className="card">
            <h3>{tr("Обробка")}</h3>
            <dl className="info-list">
              {fault.acknowledged_at && (
                <div className="info-item">
                  <dt>{tr("Прийнято")}</dt>
                  <dd>{formatDateTime(fault.acknowledged_at)}</dd>
                </div>
              )}
              {fault.mechanic && (
                <div className="info-item">
                  <dt>{tr("Механік")}</dt>
                  <dd>{fault.mechanic.full_name}</dd>
                </div>
              )}
              {fault.resolved_at && (
                <div className="info-item">
                  <dt>{tr("Вирішено")}</dt>
                  <dd>{formatDateTime(fault.resolved_at)}</dd>
                </div>
              )}
            </dl>
          </div>
        )}

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
    </div>
  )
}

export default DriverFaultDetail
