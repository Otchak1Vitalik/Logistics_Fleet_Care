import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { reportsApi } from '../../api/reports'
import Loader from '../../components/Loader'
import { tr } from '../../i18n'

const MONTHS = [tr("Січень"), tr("Лютий"), tr("Березень"), tr("Квітень"), tr("Травень"), tr("Червень"),
  tr("Липень"), tr("Серпень"), tr("Вересень"), tr("Жовтень"), tr("Листопад"), tr("Грудень")]
const WEEKDAYS = [tr("Пн"), tr("Вт"), tr("Ср"), tr("Чт"), tr("Пт"), tr("Сб"), tr("Нд")]

const STATUS_LABELS = {
  planned: tr("заплановано"), overdue: tr("прострочено"), in_progress: tr("в роботі"), completed: tr("виконано"),
}

// Клас кольору події: планове ТО / прострочене ТО / ремонт за статусом
function eventClass(e) {
  if (e.type === 'planned_maintenance') return e.status === 'overdue' ? 'ev-overdue' : 'ev-planned-to'
  if (e.status === 'completed') return 'ev-done'
  if (e.status === 'in_progress') return 'ev-progress'
  return 'ev-repair'
}

const pad = (n) => String(n).padStart(2, '0')
const isoDate = (y, m, d) => `${y}-${pad(m)}-${pad(d)}`

function MaintenanceCalendar({ role }) {
  const navigate = useNavigate()
  const now = new Date()
  const todayIso = isoDate(now.getFullYear(), now.getMonth() + 1, now.getDate())
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1) // 1..12
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(todayIso)

  useEffect(() => {
    setLoading(true)
    reportsApi.getMaintenanceCalendar(year, month)
      .then((res) => setEvents(res.data.events))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false))
  }, [year, month])

  const byDate = useMemo(() => {
    const map = {}
    events.forEach((e) => { (map[e.date] = map[e.date] || []).push(e) })
    return map
  }, [events])

  // Сітка місяця: тиждень починається з понеділка
  const cells = useMemo(() => {
    const first = new Date(year, month - 1, 1)
    const offset = (first.getDay() + 6) % 7
    const daysInMonth = new Date(year, month, 0).getDate()
    const list = Array.from({ length: offset }, () => null)
    for (let d = 1; d <= daysInMonth; d++) list.push(d)
    while (list.length % 7 !== 0) list.push(null)
    return list
  }, [year, month])

  const shiftMonth = (delta) => {
    let m = month + delta
    let y = year
    if (m < 1) { m = 12; y -= 1 }
    if (m > 12) { m = 1; y += 1 }
    setMonth(m)
    setYear(y)
  }

  const goToday = () => {
    setYear(now.getFullYear())
    setMonth(now.getMonth() + 1)
    setSelected(todayIso)
  }

  const openEvent = (e) => {
    if (e.type === 'repair' && role === 'mechanic') navigate(`/mechanic/repairs/${e.repair_id}`)
    else if (role === 'mechanic') navigate(`/mechanic/fleet/${e.vehicle_id}`)
    else navigate(`/manager/vehicles/${e.vehicle_id}`)
  }

  const counts = {
    to: events.filter((e) => e.type === 'planned_maintenance').length,
    overdue: events.filter((e) => e.status === 'overdue').length,
    repairs: events.filter((e) => e.type === 'repair').length,
  }
  const dayEvents = byDate[selected] || []

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{tr("Календар ТО")}</h1>
        <div className="calendar-nav">
          <button className="btn btn-secondary btn-sm" onClick={() => shiftMonth(-1)} aria-label={tr("Попередній місяць")}>‹</button>
          <span className="calendar-title">{MONTHS[month - 1]} {year}</span>
          <button className="btn btn-secondary btn-sm" onClick={() => shiftMonth(1)} aria-label={tr("Наступний місяць")}>›</button>
          <button className="btn btn-text btn-sm" onClick={goToday}>{tr("Сьогодні")}</button>
          {role === 'manager' && (
            <button className="btn btn-primary btn-sm" onClick={() => navigate('/manager/maintenance-plan')}>{tr("Оптимізувати графік")}</button>
          )}
        </div>
      </div>

      <div className="calendar-summary">
        <span><b>{counts.to}</b>{' '}{tr("планових ТО")}</span>
        <span className={counts.overdue ? 'text-danger' : ''}><b>{counts.overdue}</b>{' '}{tr("прострочено")}</span>
        <span><b>{counts.repairs}</b>{' '}{tr("ремонтів / робіт")}</span>
        <span className="calendar-legend">
          <i className="ev-dot ev-planned-to" />{' '}{tr("ТО за планом")}
          <i className="ev-dot ev-overdue" />{' '}{tr("прострочене")}
          <i className="ev-dot ev-repair" />{' '}{tr("заплановані роботи")}
          <i className="ev-dot ev-progress" />{' '}{tr("в роботі")}
          <i className="ev-dot ev-done" />{' '}{tr("виконано")}
        </span>
      </div>

      {loading ? <Loader text={tr("Завантаження календаря...")} /> : (
        <div className="calendar-layout">
          <div className="card calendar-card">
            <div className="calendar-grid">
              {WEEKDAYS.map((w) => <div key={w} className="calendar-weekday">{w}</div>)}
              {cells.map((day, i) => {
                if (!day) return <div key={`e${i}`} className="calendar-cell empty" />
                const iso = isoDate(year, month, day)
                const list = byDate[iso] || []
                return (
                  <button
                    key={iso}
                    type="button"
                    className={`calendar-cell ${iso === todayIso ? 'today' : ''} ${iso === selected ? 'selected' : ''}`}
                    onClick={() => setSelected(iso)}
                  >
                    <span className="calendar-day">{day}</span>
                    {list.slice(0, 3).map((e, k) => (
                      <span key={k} className={`calendar-event ${eventClass(e)}`} title={e.details}>{e.title}</span>
                    ))}
                    {list.length > 3 && <span className="calendar-more">{tr("ще")}{' '}{list.length - 3}</span>}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="card calendar-day-card">
            <h3>{selected.split('-').reverse().join('.')}</h3>
            {dayEvents.length === 0 ? (
              <div className="empty-state small">{tr("Подій немає")}</div>
            ) : (
              <ul className="list">
                {dayEvents.map((e, k) => (
                  <li key={k} className="list-item clickable" onClick={() => openEvent(e)}>
                    <i className={`ev-dot ${eventClass(e)}`} />
                    <div className="item-main">
                      <span className="item-title">{e.title}</span>
                      <span className="item-subtitle">{e.details}</span>
                      <span className="item-subtitle">{STATUS_LABELS[e.status] || e.status}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default MaintenanceCalendar
