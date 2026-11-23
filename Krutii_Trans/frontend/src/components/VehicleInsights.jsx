import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { vehiclesApi } from '../api/vehicles'
import StatusBadge from './StatusBadge'
import { formatCurrency, formatDate, formatNumber } from '../utils/formatters'
import { useRoleBase } from '../utils/useRoleBase'
import { tr } from '../i18n'

const TYPES = {
  waybill: { label: tr("Путівки"), icon: tr("ПЛ"), cls: 'tl-waybill' },
  fault: { label: tr("Несправності"), icon: tr("НС"), cls: 'tl-fault' },
  repair: { label: tr("Ремонти"), icon: tr("РМ"), cls: 'tl-repair' },
  fuel: { label: tr("Заправки"), icon: '⛽', cls: 'tl-fuel' },
}
const REPAIR_TYPES = { maintenance: tr("ТО"), repair: tr("Ремонт"), inspection: tr("Огляд") }
const PAGE = 15

// Прогноз ТО, підсумки та повна хронологія автомобіля («медична карта»)
function VehicleInsights({ vehicleId }) {
  const navigate = useNavigate()
  const base = useRoleBase()
  const [data, setData] = useState(null)
  const [filter, setFilter] = useState('all')
  const [limit, setLimit] = useState(PAGE)

  useEffect(() => {
    vehiclesApi.getHistory(vehicleId).then((res) => setData(res.data)).catch(() => setData(null))
  }, [vehicleId])

  if (!data) return null
  const f = data.maintenance_forecast || {}
  const t = data.totals || {}
  const events = (data.timeline || []).filter((e) => filter === 'all' || e.type === filter)

  const open = (e) => {
    if (e.type === 'fault') navigate(`${base}/faults/${e.id}`)
    else if (e.type === 'repair') navigate(`${base}/repairs/${e.id}`)
    else if (e.type === 'waybill' && base === '/manager') navigate(`/manager/waybills/${e.id}`)
  }

  const title = (e) => {
    if (e.type === 'waybill') return `${e.number} · ${e.title || tr("Путівка")}`
    if (e.type === 'fault') return `${e.number} · ${e.title}`
    if (e.type === 'repair') return `${e.number} · ${REPAIR_TYPES[e.repair_type] || ''}: ${e.title}`
    return e.record_type === 'external' ? tr("Заправка на АЗС {0}", e.title || '') : tr("Видача пального")
  }
  const value = (e) => {
    const out = []
    if (e.distance) out.push(tr("{0} км", formatNumber(e.distance)))
    if (e.fuel) out.push(tr("{0} л", formatNumber(e.fuel)))
    if (e.cost) out.push(formatCurrency(e.cost))
    return out.join(' · ')
  }

  const daysCls = f.days_left !== null && f.days_left !== undefined
    ? (f.days_left <= 0 ? 'forecast-overdue' : f.days_left <= 14 ? 'forecast-soon' : '') : ''

  return (
    <>
      <div className="card full-width">
        <h3>{tr("Прогноз технічного обслуговування")}</h3>
        {f.expected_date ? (
          <div className="forecast-card mt-md">
            <div>
              <div className={`forecast-date ${daysCls}`}>≈ {formatDate(f.expected_date)}</div>
              <div className="text-muted">
                {f.days_left <= 0 ? tr("ТО вже потрібне") : tr("через {0} дн.", f.days_left)}
              </div>
            </div>
            <div className="text-muted" style={{ flex: 1, minWidth: 220 }}>
              {f.basis === 'mileage'
                ? tr("Розраховано за середнім пробігом ≈ {0} км/добу: до ТО залишилось {1} км.", f.avg_daily_km, formatNumber(f.km_left))
                : tr("Визначено плановою датою ТО.")}
              {f.avg_daily_km && f.basis === 'date' ? ' ' + tr("Середній пробіг ≈ {0} км/добу.", f.avg_daily_km) : ''}
            </div>
          </div>
        ) : (
          <div className="empty-state small">{tr("Недостатньо даних для прогнозу")}</div>
        )}
      </div>

      <div className="card full-width">
        <h3>{tr("Підсумки за весь час")}</h3>
        <div className="info-grid mt-md">
          <div className="info-row"><span className="label">{tr("Путівок")}</span><span className="value">{t.waybills}</span></div>
          <div className="info-row"><span className="label">{tr("Пробіг за путівками")}</span><span className="value">{tr("{0} км", formatNumber(t.distance))}</span></div>
          <div className="info-row"><span className="label">{tr("Витрачено пального")}</span><span className="value">{tr("{0} л", formatNumber(t.fuel_used))}</span></div>
          <div className="info-row"><span className="label">{tr("Несправностей (відкритих)")}</span><span className="value">{t.faults} ({t.open_faults})</span></div>
          <div className="info-row"><span className="label">{tr("Завершених ремонтів")}</span><span className="value">{t.repairs}</span></div>
          <div className="info-row"><span className="label">{tr("Витрати на ремонти")}</span><span className="value">{formatCurrency(t.repairs_cost)}</span></div>
          <div className="info-row"><span className="label">{tr("Витрати на заправки")}</span><span className="value">{formatCurrency(t.fuel_cost)}</span></div>
        </div>
      </div>

      <div className="card full-width">
        <h3>{tr("Історія автомобіля")}</h3>
        <div className="timeline-filters mt-md">
          {[['all', tr("Усе")], ...Object.entries(TYPES).map(([k, v]) => [k, v.label])].map(([k, label]) => (
            <button key={k} className={`btn btn-sm ${filter === k ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => { setFilter(k); setLimit(PAGE) }}>
              {label} ({k === 'all' ? data.timeline.length : data.timeline.filter((e) => e.type === k).length})
            </button>
          ))}
        </div>
        {events.length === 0 ? <div className="empty-state small">{tr("Немає записів")}</div> : (
          <ul className="timeline">
            {events.slice(0, limit).map((e) => (
              <li key={`${e.type}-${e.id}`} className="timeline-item" onClick={() => open(e)}>
                <span className={`timeline-icon ${TYPES[e.type].cls}`}>{TYPES[e.type].icon}</span>
                <div>
                  <div className="timeline-title">{title(e)}</div>
                  <div className="timeline-meta">
                    {formatDate(e.date)}{e.person ? ` · ${e.person}` : ''}
                    {e.parts?.length ? ` · ${tr("запчастини")}: ${e.parts.join(', ')}` : ''}
                  </div>
                </div>
                <div className="timeline-value">
                  {value(e)}
                  {e.status && <div className="mt-sm"><StatusBadge status={e.status} /></div>}
                </div>
              </li>
            ))}
          </ul>
        )}
        {events.length > limit && (
          <button className="btn btn-text mt-md" onClick={() => setLimit(limit + PAGE)}>
            {tr("Показати ще ({0})", events.length - limit)}
          </button>
        )}
      </div>
    </>
  )
}

export default VehicleInsights
