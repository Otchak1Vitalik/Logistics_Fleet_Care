import { Fragment, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  ResponsiveContainer, ComposedChart, Line, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ReferenceArea,
} from 'recharts'
import { fuelAnomaliesApi } from '../../api/fuelAnomalies'
import Loader from '../../components/Loader'
import { useThemeStore } from '../../store/themeStore'
import { formatDate, formatCurrency, formatNumber } from '../../utils/formatters'
import { tr, lang } from '../../i18n'

const KINDS = {
  trip_overspend: { label: tr("Перевитрата в рейсі") },
  over_tank: { label: tr("Заправка понад бак") },
  double_refuel: { label: tr("Повторна заправка") },
  price: { label: tr("Нетипова ціна") },
}
const METHODS = {
  rule: { label: tr("Норма"), title: tr("Правило норми: перевищення норми з урахуванням сезону більше за поріг") },
  stat: { label: 'z-score', title: tr("Робастний z-score: нетипово висока витрата відносно звичної для цього авто") },
  ml: { label: 'ML', title: tr("Isolation Forest: нетиповий рейс за сукупністю ознак") },
  check: { label: tr("Перевірка"), title: tr("Формальна перевірка заправки") },
}
const STATUSES = {
  new: { label: tr("Нова"), cls: 'status-warning' },
  confirmed: { label: tr("Підтверджено"), cls: 'status-danger' },
  dismissed: { label: tr("Хибна тривога"), cls: 'status-secondary' },
}
const LEVELS = { high: tr("Високий"), medium: tr("Середній"), low: tr("Низький") }
const pct = (v) => `${Math.round(v * 100)} %`

function VehicleChart({ vehicleId, current }) {
  const theme = useThemeStore((s) => s.theme)
  const [hist, setHist] = useState(null)
  useEffect(() => {
    fuelAnomaliesApi.vehicleHistory(vehicleId).then((r) => setHist(r.data.history)).catch(() => setHist(null))
  }, [vehicleId])
  if (!hist) return <div className="fa-chart fa-chart-empty"><Loader /></div>
  if (hist.points.length < 2) return null
  const axis = theme === 'dark' ? '#9aa4b2' : '#6b7280'
  const grid = theme === 'dark' ? '#263044' : '#e5e7eb'
  const data = hist.points.map((p) => ({ ...p, t: new Date(p.date).getTime(), flag: p.flagged ? p.pct : null,
    cur: p.waybill_id === current ? p.pct : null }))
  const max = Math.max(130, ...data.map((d) => d.pct)) + 5
  return (
    <div className="fa-chart">
      <div className="fa-chart-title">{tr("Витрата цього авто по рейсах, % від норми")}</div>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid stroke={grid} vertical={false} />
          <XAxis dataKey="t" type="number" domain={['dataMin', 'dataMax']} scale="time" stroke={axis} fontSize={11}
            tickFormatter={(t) => formatDate(new Date(t), 'dd.MM')} />
          <YAxis domain={[70, Math.ceil(max / 10) * 10]} stroke={axis} fontSize={11} unit="%" />
          <ReferenceArea y1={hist.typical_pct - 5} y2={hist.typical_pct + 5} fill="#10b981" fillOpacity={0.1} />
          <ReferenceLine y={100} stroke={axis} strokeDasharray="4 4" label={{ value: tr("норма"), position: 'insideTopLeft', fill: axis, fontSize: 11 }} />
          <Tooltip contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-gray-200)', borderRadius: 8, fontSize: 12 }}
            labelFormatter={(t) => formatDate(new Date(t))}
            formatter={(v, name, item) => (name === 'pct' ? [`${v} % (${item.payload.actual_l100} ${tr("л/100 км")})`, item.payload.number] : [null, null])} />
          <Line dataKey="pct" stroke="#6366f1" strokeWidth={1.5} dot={{ r: 2 }} isAnimationActive={false} />
          <Scatter dataKey="flag" fill="#f59e0b" shape="circle" isAnimationActive={false} />
          <Scatter dataKey="cur" fill="#dc2626" shape="diamond" isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="fa-legend">
        <span><i style={{ background: '#6366f1' }} />{tr("рейси")}</span>
        <span><i className="band" />{tr("звична витрата авто ({0} %)", hist.typical_pct)}</span>
        <span><i style={{ background: '#f59e0b' }} />{tr("позначені системою")}</span>
        <span><i style={{ background: '#dc2626' }} />{tr("цей рейс")}</span>
      </div>
    </div>
  )
}

function Metrics({ a }) {
  const m = a.metrics || {}
  const rows = a.kind === 'trip_overspend' ? [
    [tr("Пробіг"), tr("{0} км", formatNumber(m.distance))],
    [tr("Витрачено"), tr("{0} л", formatNumber(m.fuel_used, 1))],
    [tr("Фактично / норма"), `${m.actual_l100} / ${m.norm_l100} ${tr("л/100 км")}`],
    [tr("Відхилення від норми"), `${m.deviation_pct > 0 ? '+' : ''}${m.deviation_pct} %`],
    [tr("Звична витрата авто"), tr("{0} % від норми", m.typical_pct)],
    ['z-score', `${m.z} (${m.z_basis === 'vehicle' ? tr("за історією авто") : tr("за автопарком")})`],
    [tr("Оцінка Isolation Forest"), m.ml_score?.toFixed(2)],
  ] : a.kind === 'price' ? [
    [tr("Ціна"), tr("{0} грн/л", m.price)], [tr("Звична ціна"), tr("{0} грн/л", m.median_price)],
    [tr("Відхилення"), `${m.deviation_pct > 0 ? '+' : ''}${m.deviation_pct} %`],
  ] : a.kind === 'over_tank' ? [
    [tr("Заправлено"), tr("{0} л", formatNumber(m.quantity))], [tr("Об'єм бака"), tr("{0} л", formatNumber(m.tank))],
  ] : [
    [tr("Заправлено"), tr("{0} л", formatNumber(m.quantity))], [tr("Після попередньої"), tr("{0} год, {1} км", m.hours, m.km)],
  ]
  return (
    <dl className="fa-metrics">
      {rows.map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{v}</dd></Fragment>)}
      {m.excess_l > 0 && <><dt>{tr("Можливі втрати")}</dt><dd className="fa-loss">{tr("{0} л", formatNumber(m.excess_l, 1))} · {formatCurrency(m.cost)}</dd></>}
      {a.kind === 'price' && m.cost > 0 && <><dt>{tr("Переплата")}</dt><dd className="fa-loss">{formatCurrency(m.cost)}</dd></>}
    </dl>
  )
}

function Detail({ a, onReviewed }) {
  const [comment, setComment] = useState(a.review?.comment || '')
  const [saving, setSaving] = useState(false)
  const save = async (status) => {
    setSaving(true)
    try {
      const r = await fuelAnomaliesApi.review(a._id, status, comment)
      toast.success(tr(r.data.message))
      onReviewed(r.data.anomaly, r.data.summary)
    } catch { /* interceptor */ }
    setSaving(false)
  }
  return (
    <div className="fa-detail">
      <div className="fa-detail-main">
        <div className="fa-reasons">
          <h4>{tr("Чому випадок позначено")}</h4>
          <ul>{a.reasons.map((r) => <li key={r}>{tr(r)}</li>)}</ul>
          {a.source_type === 'waybill' && <Link to={`/manager/waybills/${a.source_id}`} className="fa-link">{tr("Відкрити путівку")} {a.number} →</Link>}
        </div>
        <Metrics a={a} />
      </div>
      {a.kind === 'trip_overspend' && <VehicleChart vehicleId={a.vehicle_id} current={a.source_id} />}
      <div className="fa-review">
        {a.review && (
          <div className="fa-review-info">
            {tr("Рішення")}: <b>{STATUSES[a.status].label}</b> · {a.review.by_name} · {formatDate(a.review.at, 'dd.MM.yyyy HH:mm')}
          </div>
        )}
        <textarea className="form-control" rows={2} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)}
          placeholder={tr("Коментар: результат перевірки, пояснення водія...")} />
        <div className="fa-review-actions">
          {a.status !== 'confirmed' && <button className="btn btn-danger btn-sm" disabled={saving} onClick={() => save('confirmed')}>{tr("Підтвердити порушення")}</button>}
          {a.status !== 'dismissed' && <button className="btn btn-secondary btn-sm" disabled={saving} onClick={() => save('dismissed')}>{tr("Хибна тривога")}</button>}
          {a.status !== 'new' && <button className="btn btn-text btn-sm" disabled={saving} onClick={() => save('new')}>{tr("Повернути в нові")}</button>}
        </div>
      </div>
    </div>
  )
}

function Evaluation() {
  const [ev, setEv] = useState(null)
  useEffect(() => { fuelAnomaliesApi.evaluation().then((r) => setEv(r.data.evaluation)).catch(() => setEv(false)) }, [])
  if (ev === null) return <Loader />
  if (!ev || !ev.labeled) {
    return <div className="card"><div className="table-empty">{tr("Поки немає рейсів з відомою відповіддю. Позначайте випадки як «підтверджено» або «хибна тривога» - і тут з'явиться порівняння методів.")}</div></div>
  }
  const best = Math.max(...ev.methods.map((m) => m.f1))
  return (
    <div className="fa-eval">
      <div className="card">
        <h3>{tr("Порівняння методів виявлення")}</h3>
        <p className="text-muted">
          {ev.source === 'demo'
            ? tr("Перевірено на {0} демонстраційних рейсах, серед яких {1} з навмисно внесеною перевитратою (відома правильна відповідь).", ev.labeled, ev.positives)
            : tr("Перевірено на {0} рейсах, щодо яких керівник ухвалив рішення (з них {1} підтверджених порушень).", ev.labeled, ev.positives)}
        </p>
        <div className="table-wrapper">
          <table className="data-table fa-eval-table">
            <thead><tr>
              <th>{tr("Метод")}</th><th title={tr("Частка справжніх порушень серед позначених")}>{tr("Точність")}{lang === 'en' ? '' : ' (precision)'}</th>
              <th title={tr("Частка знайдених порушень серед усіх справжніх")}>{tr("Повнота")}{lang === 'en' ? '' : ' (recall)'}</th><th>F1</th>
              <th>{tr("Знайдено")}</th><th>{tr("Хибні тривоги")}</th><th>{tr("Пропущено")}</th>
            </tr></thead>
            <tbody>
              {ev.methods.map((m) => (
                <tr key={m.key} className={m.key === 'any' ? 'fa-eval-system' : ''}>
                  <td className="font-medium">{tr(m.title)}</td>
                  <td><div className="fa-bar"><span style={{ width: `${m.precision * 100}%` }} /></div>{pct(m.precision)}</td>
                  <td><div className="fa-bar"><span style={{ width: `${m.recall * 100}%` }} /></div>{pct(m.recall)}</td>
                  <td className={m.f1 === best ? 'fa-best' : ''}>{m.f1.toFixed(2)}</td>
                  <td>{m.tp}</td><td>{m.fp}</td><td>{m.fn}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fa-note">{tr("Правило норми не враховує, що кожне авто має свою звичну витрату: економне авто може перевитрачати відносно себе, залишаючись у межах норми. Статистичний метод це помічає, а Isolation Forest враховує кілька ознак разом. Поєднання методів дає найкращий баланс точності й повноти.")}</p>
      </div>
      <div className="card">
        <h3>{tr("Як поріг правила норми впливає на результат")}</h3>
        <p className="text-muted">{tr("Поточний поріг задається в налаштуваннях системи («Поріг перевитрати»).")}</p>
        <div className="table-wrapper">
          <table className="data-table fa-eval-table">
            <thead><tr><th>{tr("Поріг")}</th><th>{tr("Точність")}</th><th>{tr("Повнота")}</th><th>F1</th><th>{tr("Хибні тривоги")}</th><th>{tr("Пропущено")}</th></tr></thead>
            <tbody>
              {ev.rule_thresholds.map((r) => (
                <tr key={r.threshold}><td className="font-medium">{r.threshold} %</td><td>{pct(r.precision)}</td><td>{pct(r.recall)}</td>
                  <td>{r.f1.toFixed(2)}</td><td>{r.fp}</td><td>{r.fn}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function FuelAnomalies() {
  const [tab, setTab] = useState('cases')
  const [status, setStatus] = useState('new')
  const [kind, setKind] = useState('')
  const [items, setItems] = useState(null)
  const [summary, setSummary] = useState(null)
  const [open, setOpen] = useState(null)
  const [running, setRunning] = useState(false)

  const load = () => {
    fuelAnomaliesApi.getAll({ ...(status ? { status } : {}), ...(kind ? { kind } : {}) })
      .then((r) => { setItems(r.data.items); setSummary(r.data.summary) })
      .catch(() => setItems([]))
  }
  useEffect(load, [status, kind])

  const run = async () => {
    setRunning(true)
    try {
      const r = await fuelAnomaliesApi.run()
      toast.success(tr("Перевірено рейсів: {0}, підозрілих випадків: {1}", r.data.result.trips_checked, r.data.result.found))
      load()
    } catch { /* interceptor */ }
    setRunning(false)
  }

  const onReviewed = (a, s) => {
    setSummary(s)
    setItems((list) => (status && a.status !== status ? list.filter((x) => x._id !== a._id) : list.map((x) => (x._id === a._id ? a : x))))
    if (status && a.status !== status) setOpen(null)
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <div className="fa-crumbs"><Link to="/manager/fuel">{tr("Пальне")}</Link> /</div>
          <h1>{tr("Аномалії витрати пального")}</h1>
          <p className="text-muted">{tr("Рейси і заправки, які система вважає підозрілими. Перевірте кожен випадок і ухваліть рішення.")}</p>
        </div>
        <button className="btn btn-secondary" onClick={run} disabled={running}>
          {running ? tr("Перевіряємо...") : tr("Перевірити зараз")}
        </button>
      </div>

      {summary && (
        <div className="dashboard-stats mb-lg">
          <div className={`stat-card ${summary.high_new ? 'danger' : 'warning'}`} onClick={() => { setTab('cases'); setStatus('new') }} style={{ cursor: 'pointer' }}>
            <div className="stat-value">{summary.new}</div>
            <div className="stat-label">{tr("Нових випадків")}{summary.high_new ? ` · ${tr("{0} з високим ризиком", summary.high_new)}` : ''}</div>
          </div>
          <div className="stat-card" onClick={() => { setTab('cases'); setStatus('confirmed') }} style={{ cursor: 'pointer' }}>
            <div className="stat-value">{summary.confirmed}</div><div className="stat-label">{tr("Підтверджених порушень")}</div>
          </div>
          <div className="stat-card" onClick={() => { setTab('cases'); setStatus('dismissed') }} style={{ cursor: 'pointer' }}>
            <div className="stat-value">{summary.dismissed}</div><div className="stat-label">{tr("Хибних тривог")}</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{formatCurrency(summary.loss_cost)}</div>
            <div className="stat-label">{tr("Можливі втрати: {0} л (нові й підтверджені)", formatNumber(summary.loss_liters))}</div>
          </div>
        </div>
      )}

      <div className="tabs">
        <button className={`tab ${tab === 'cases' ? 'active' : ''}`} onClick={() => setTab('cases')}>{tr("Підозрілі випадки")}</button>
        <button className={`tab ${tab === 'eval' ? 'active' : ''}`} onClick={() => setTab('eval')}>{tr("Порівняння методів")}</button>
      </div>

      {tab === 'eval' ? <Evaluation /> : (
        <div className="card">
          <div className="fa-filters">
            <div className="filter-tabs">
              {[['new', tr("Нові")], ['confirmed', tr("Підтверджені")], ['dismissed', tr("Хибні тривоги")], ['', tr("Усі")]].map(([k, l]) => (
                <button key={k} className={`tab ${status === k ? 'active' : ''}`} onClick={() => { setStatus(k); setOpen(null) }}>{l}</button>
              ))}
            </div>
            <select className="form-control" value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="">{tr("Усі типи")}</option>
              {Object.entries(KINDS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </div>
          {items === null ? <Loader /> : !items.length ? <div className="table-empty">{tr("Випадків не знайдено")}</div> : (
            <div className="table-wrapper">
              <table className="data-table fa-table">
                <thead><tr>
                  <th>{tr("Ризик")}</th><th>{tr("Дата")}</th><th>{tr("Автомобіль / водій")}</th><th>{tr("Тип")}</th>
                  <th>{tr("Показник")}</th><th>{tr("Методи")}</th><th>{tr("Статус")}</th>
                </tr></thead>
                <tbody>
                  {items.map((a) => (
                    <Fragment key={a._id}>
                      <tr className={`fa-row ${open === a._id ? 'open' : ''}`} onClick={() => setOpen(open === a._id ? null : a._id)}>
                        <td><span className={`fa-score ${a.level}`} title={LEVELS[a.level]}>{a.score}</span></td>
                        <td><div>{formatDate(a.date)}</div><div className="text-muted">{a.number}</div></td>
                        <td><div className="font-medium">{a.vehicle_label}</div><div className="text-muted">{a.driver_name || '—'}</div></td>
                        <td className="fa-kind">{KINDS[a.kind]?.label}</td>
                        <td className="fa-key">
                          {a.kind === 'trip_overspend' ? <>{a.metrics.actual_l100} <span className="text-muted">/ {a.metrics.norm_l100} {tr("л/100 км")}</span></>
                            : a.kind === 'price' ? <>{tr("{0} грн/л", a.metrics.price)} <span className="text-muted">({a.metrics.deviation_pct > 0 ? '+' : ''}{a.metrics.deviation_pct} %)</span></>
                              : a.kind === 'over_tank' ? <>{tr("{0} л", a.metrics.quantity)} <span className="text-muted">/ {tr("бак {0} л", a.metrics.tank)}</span></>
                                : <>{tr("{0} л", a.metrics.quantity)} <span className="text-muted">{tr("через {0} год", a.metrics.hours)}</span></>}
                        </td>
                        <td><div className="fa-methods">{a.methods.map((m) => <span key={m} className={`fa-method ${m}`} title={METHODS[m]?.title}>{METHODS[m]?.label}</span>)}</div></td>
                        <td><span className={`status-badge ${STATUSES[a.status].cls}`}>{STATUSES[a.status].label}</span></td>
                      </tr>
                      {open === a._id && <tr className="fa-detail-row"><td colSpan={7}><Detail a={a} onReviewed={onReviewed} /></td></tr>}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default FuelAnomalies
