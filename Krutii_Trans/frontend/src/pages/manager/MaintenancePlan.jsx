import { Fragment, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { maintenancePlanApi } from '../../api/maintenancePlan'
import Loader from '../../components/Loader'
import { formatCurrency, formatDate, formatNumber } from '../../utils/formatters'
import { tr } from '../../i18n'

const WEEKDAYS = [tr("Нд"), tr("Пн"), tr("Вт"), tr("Ср"), tr("Чт"), tr("Пт"), tr("Сб")]
const LEVELS = { high: 'status-danger', medium: 'status-warning', low: 'status-success' }
const LEVEL_LABELS = { high: tr("Високий"), medium: tr("Середній"), low: tr("Низький") }
const dayKey = (d) => String(d).slice(0, 10)

function Compare({ opt, naive }) {
  const rows = [
    { key: 'expected_failures', label: tr("Очікувані відмови до ТО"), fmt: (v) => formatNumber(v, 2), better: 'less' },
    { key: 'overdue_days', label: tr("Днів прострочення ТО"), fmt: (v) => v, better: 'less' },
    { key: 'high_risk_wait_days', label: tr("Днів очікування авто з високим ризиком"), fmt: (v) => v, better: 'less' },
    { key: 'scheduled', label: tr("Заплановано ТО"), fmt: (v) => v, better: 'more' },
    { key: 'cost', label: tr("Очікувані витрати"), fmt: (v) => formatCurrency(v), better: 'less' },
  ]
  const saved = naive.cost > 0 ? 1 - opt.cost / naive.cost : 0
  return (
    <div className="mp-compare card">
      <div className="mp-compare-head">
        <h3>{tr("Оптимізований план проти планування «за календарем»")}</h3>
        {saved > 0.005 && <span className="mp-saving">−{Math.round(saved * 100)} % {tr("витрат")}</span>}
      </div>
      <table className="mp-compare-table">
        <thead><tr><th /><th>{tr("За календарем")}</th><th>{tr("Оптимізований")}</th></tr></thead>
        <tbody>
          {rows.map((r) => {
            const a = naive[r.key]
            const b = opt[r.key]
            const good = r.better === 'less' ? b < a : b > a
            return (
              <tr key={r.key}>
                <th>{r.label}</th><td>{r.fmt(a)}</td>
                <td className={good ? 'mp-good' : ''}>{r.fmt(b)}{good && ' ✓'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="pm-note">{tr("«За календарем» - кожен автомобіль ставиться на ТО у свій строк (або на перший вільний день після нього) без урахування ризику відмови. Очікувані витрати - відмови до ТО, прострочення і недовикористаний ресурс при надто ранньому ТО.")}</p>
    </div>
  )
}

function Gantt({ plan, selected }) {
  const days = plan.days
  return (
    <div className="card">
      <h3>{tr("Графік на {0} днів", days.length)}</h3>
      <div className="mp-legend">
        <span><i className="mp-l-opt" />{tr("оптимізований план")}</span>
        <span><i className="mp-l-naive" />{tr("за календарем")}</span>
        <span><i className="mp-l-due" />{tr("строк ТО")}</span>
        <span><i className="mp-l-trip" />{tr("рейс (путівка)")}</span>
        <span><i className="mp-l-off" />{tr("вихідний")}</span>
      </div>
      <div className="mp-gantt-wrap">
        <table className="mp-gantt">
          <thead>
            <tr>
              <th className="mp-veh">{tr("Автомобіль")}</th>
              {days.map((d) => {
                const dt = new Date(d.date)
                return <th key={d.date} className={d.capacity ? '' : 'off'}><div>{WEEKDAYS[dt.getUTCDay()]}</div><b>{dt.getUTCDate()}</b></th>
              })}
            </tr>
          </thead>
          <tbody>
            {plan.items.map((it) => (
              <tr key={it.vehicle_id} className={selected[it.vehicle_id] === false ? 'mp-dim' : ''}>
                <td className="mp-veh">
                  <span className={`mp-risk-dot ${it.risk_level}`} title={tr("Ризик відмови {0} %", Math.round(it.risk * 100))} />
                  {it.plate}
                </td>
                {days.map((d, k) => {
                  const cls = [d.capacity ? '' : 'off', it.trip_days.includes(k) ? 'trip' : '', it.due_day === k ? 'due' : ''].join(' ')
                  return (
                    <td key={d.date} className={cls}>
                      {it.day === k && <span className="mp-opt" title={tr("ТО: {0}", formatDate(it.date))}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></svg></span>}
                      {it.naive_day === k && it.day !== k && <span className="mp-naive" title={tr("За календарем: {0}", formatDate(it.naive_date))} />}
                    </td>
                  )
                })}
              </tr>
            ))}
            {plan.fixed.length > 0 && (
              <tr className="mp-fixed-row">
                <td className="mp-veh">{tr("Уже заплановано")}</td>
                {days.map((d) => <td key={d.date} className={d.capacity ? '' : 'off'}>{d.fixed > 0 && <span className="mp-fixed">{d.fixed}</span>}</td>)}
              </tr>
            )}
          </tbody>
          <tfoot>
            <tr>
              <td className="mp-veh">{tr("Завантаження сервісу")}</td>
              {days.map((d) => (
                <td key={d.date} className={d.capacity ? '' : 'off'}>
                  {d.capacity > 0 && <span className={`mp-load ${d.load >= d.capacity ? 'full' : ''}`}>{d.load}/{d.capacity}</span>}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

function MaintenancePlan() {
  const [params, setParams] = useState({ horizon: 21, bays: '', failure_cost: 30000 })
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState({})
  const [saving, setSaving] = useState(false)

  const load = async (p = params) => {
    setLoading(true)
    try {
      const q = { horizon: p.horizon, failure_cost: p.failure_cost, ...(p.bays ? { bays: p.bays } : {}) }
      const r = await maintenancePlanApi.get(q)
      setPlan(r.data)
      if (!p.bays) setParams((x) => ({ ...x, bays: r.data.params.bays }))
      setSelected(Object.fromEntries(r.data.items.filter((i) => i.date).map((i) => [i.vehicle_id, true])))
    } catch { /* interceptor */ }
    setLoading(false)
  }
  useEffect(() => { load() }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  const apply = async () => {
    const items = plan.items.filter((i) => i.date && selected[i.vehicle_id]).map((i) => ({ vehicle_id: i.vehicle_id, date: dayKey(i.date) }))
    if (!items.length) return
    setSaving(true)
    try {
      const r = await maintenancePlanApi.apply(items)
      toast.success(tr(r.data.message))
      await load()
    } catch { /* interceptor */ }
    setSaving(false)
  }

  const chosen = plan ? plan.items.filter((i) => i.date && selected[i.vehicle_id]).length : 0
  const p = plan?.parts
  const shortage = p && (p.filters_needed > p.filters_stock || p.oil_needed > p.oil_stock)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <div className="fa-crumbs"><Link to="/manager/calendar">{tr("Календар ТО")}</Link> /</div>
          <h1>{tr("Оптимізація графіка ТО")}</h1>
          <p className="text-muted">{tr("Система розподіляє ТО по днях так, щоб ризиковані автомобілі обслуговувались раніше, сервіс не перевантажувався, а ТО не припадало на дні рейсів.")}</p>
        </div>
      </div>

      <div className="card mp-controls">
        <label>{tr("Горизонт")}
          <select className="form-control" value={params.horizon} onChange={(e) => setParams({ ...params, horizon: +e.target.value })}>
            {[14, 21, 28].map((h) => <option key={h} value={h}>{tr("{0} днів", h)}</option>)}
          </select>
        </label>
        <label>{tr("Місць у сервісі на день")}
          <input type="number" min={1} max={10} className="form-control" value={params.bays} onChange={(e) => setParams({ ...params, bays: e.target.value })} />
        </label>
        <label>{tr("Вартість однієї відмови, грн")}
          <input type="number" min={1000} step={1000} className="form-control" value={params.failure_cost} onChange={(e) => setParams({ ...params, failure_cost: e.target.value })} />
        </label>
        <button className="btn btn-secondary" onClick={() => load()} disabled={loading}>{loading ? tr("Розраховуємо...") : tr("Перерахувати")}</button>
        {plan && <span className="text-muted mp-hint">{tr("Механіків: {0}. Неділя - вихідний.", plan.params.mechanics)}</span>}
      </div>

      {!plan ? <Loader /> : (
        <>
          <Compare opt={plan.optimized} naive={plan.naive} />
          {shortage && (
            <div className="pm-warn mp-parts">
              {tr("Для запланованих ТО може не вистачити запчастин:")}{' '}
              {[
                p.filters_needed > p.filters_stock && tr("масляні фільтри - потрібно {0} шт., на складі {1}", p.filters_needed, p.filters_stock),
                p.oil_needed > p.oil_stock && tr("моторна олива - потрібно {0} л, на складі {1} л", p.oil_needed, p.oil_stock),
              ].filter(Boolean).join('; ')}. {tr("Замовте до початку робіт.")}{' '}
              <Link to="/manager/parts">{tr("Склад")} →</Link>
            </div>
          )}
          {plan.items.length === 0
            ? <div className="card"><div className="table-empty">{tr("Найближчим часом ТО не потрібне жодному автомобілю.")}</div></div>
            : (
              <>
                <Gantt plan={plan} selected={selected} />
                <div className="card">
                  <div className="mp-list-head">
                    <h3>{tr("Пропозиції")}</h3>
                    <button className="btn btn-primary" onClick={apply} disabled={!chosen || saving}>
                      {saving ? tr("Зберігаємо...") : tr("Затвердити обрані ({0})", chosen)}
                    </button>
                  </div>
                  <div className="table-wrapper">
                    <table className="data-table mp-table">
                      <thead><tr>
                        <th /><th>{tr("Автомобіль")}</th><th>{tr("Строк ТО")}</th><th>{tr("Ризик")}</th>
                        <th>{tr("Оптимізований план")}</th><th>{tr("За календарем")}</th><th>{tr("Пояснення")}</th>
                      </tr></thead>
                      <tbody>
                        {plan.items.map((it) => (
                          <tr key={it.vehicle_id}>
                            <td>{it.date && <input type="checkbox" checked={!!selected[it.vehicle_id]}
                              onChange={(e) => setSelected({ ...selected, [it.vehicle_id]: e.target.checked })} aria-label={it.plate} />}</td>
                            <td><Link to={`/manager/vehicles/${it.vehicle_id}`} className="font-medium pm-link">{it.vehicle_label}</Link></td>
                            <td className="mp-nowrap">{formatDate(it.due_date)}
                              <div className="text-muted">{it.due_basis === 'mileage' ? tr("за пробігом") : tr("за датою")}{it.due_day < 0 ? ` · ${tr("прострочено")}` : ''}</div></td>
                            <td className="mp-nowrap"><span className={`status-badge ${LEVELS[it.risk_level]}`}>{Math.round(it.risk * 100)} %</span>
                              <div className="text-muted">{LEVEL_LABELS[it.risk_level]}</div></td>
                            <td className="mp-nowrap font-medium">{it.date ? formatDate(it.date) : <span className="text-muted">{tr("пізніше")}</span>}
                              {it.shift_days !== null && it.shift_days !== 0 && (
                                <div className={`mp-shift ${it.shift_days < 0 ? 'early' : 'late'}`}>
                                  {it.shift_days < 0 ? tr("на {0} дн. раніше", -it.shift_days) : tr("на {0} дн. пізніше", it.shift_days)}
                                </div>)}</td>
                            <td className="mp-nowrap text-muted">{it.naive_date ? formatDate(it.naive_date) : tr("пізніше")}</td>
                            <td className="mp-reason">{tr(it.reason)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {plan.fixed.length > 0 && (
                    <p className="pm-note">
                      {tr("Уже заплановані ТО (враховано в завантаженні):")}{' '}
                      {plan.fixed.map((f, k) => (
                        <Fragment key={f.repair_id}>{k > 0 && ', '}<Link to={`/manager/repairs/${f.repair_id}`}>{f.plate}</Link>{f.date ? ` (${formatDate(f.date)})` : ''}</Fragment>
                      ))}
                    </p>
                  )}
                </div>
                <p className="pm-note mp-method">{tr("Метод: задача про призначення (угорський алгоритм). Вартість призначення авто на день = імовірність відмови до ТО × вартість відмови + недовикористаний ресурс при ранньому ТО + штраф за кожен день прострочення. Ризик відмови - з моделі прогнозу несправностей.")}</p>
              </>
            )}
        </>
      )}
    </div>
  )
}

export default MaintenancePlan
