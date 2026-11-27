import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Cell,
} from 'recharts'
import { predictiveApi } from '../../api/predictive'
import Loader from '../../components/Loader'
import { useThemeStore } from '../../store/themeStore'
import { formatDate, formatNumber } from '../../utils/formatters'
import { tr } from '../../i18n'

const LEVELS = {
  high: { label: tr("Високий"), cls: 'status-danger' },
  medium: { label: tr("Середній"), cls: 'status-warning' },
  low: { label: tr("Низький"), cls: 'status-success' },
}
const COLORS = { rule: '#94a3b8', logreg: '#6366f1', gboost: '#f59e0b' }
const pct = (v, d = 0) => `${(v * 100).toFixed(d)} %`

// Значення ознаки в зрозумілому вигляді
export function featureValue(key, v) {
  if (v === null || v === undefined) return '—'
  if (key === 'maint_ratio') return `${Math.round(v * 100)} %`
  if (key === 'fuel_dev') return `${v > 0 ? '+' : ''}${formatNumber(v, 1)} %`
  if (key === 'odometer_k') return tr("{0} тис. км", formatNumber(v))
  if (key === 'age_years') return tr("{0} р.", formatNumber(v, 1))
  if (key === 'daily_km') return tr("{0} км", formatNumber(v))
  if (key === 'days_since_maint') return tr("{0} дн.", v)
  if (key === 'heavy') return v ? tr("так") : tr("ні")
  return String(v)
}

function useChartColors() {
  const theme = useThemeStore((s) => s.theme)
  return { axis: theme === 'dark' ? '#9aa4b2' : '#6b7280', grid: theme === 'dark' ? '#263044' : '#e5e7eb' }
}
const tooltipStyle = { background: 'var(--color-surface)', border: '1px solid var(--color-gray-200)', borderRadius: 8, fontSize: 12 }

export function RiskFactors({ item }) {
  if (!item.factors?.length) return <span className="text-muted">{tr("Помітних чинників немає")}</span>
  return (
    <div className="pm-factors">
      {item.factors.map((f) => (
        <span key={f.feature} className="pm-factor" title={tr("Звичне значення: {0}", featureValue(f.feature, f.typical))}>
          {tr(f.label)}: <b>{featureValue(f.feature, f.value)}</b>
        </span>
      ))}
    </div>
  )
}

function RiskBar({ p, level }) {
  return (
    <div className="pm-prob">
      <div className="pm-prob-bar"><span className={level} style={{ width: `${Math.max(3, p * 100)}%` }} /></div>
      <b>{p < 0.01 ? '< 1 %' : pct(p)}</b>
    </div>
  )
}

function RiskTab() {
  const [data, setData] = useState(null)
  const [level, setLevel] = useState('')
  useEffect(() => { predictiveApi.risk().then((r) => setData(r.data)).catch(() => setData({ ready: false, items: [] })) }, [])
  if (!data) return <Loader />
  if (!data.ready) return <div className="card"><div className="table-empty">{tr("Недостатньо історії для навчання моделі. Знімки стану автопарку збираються щомісяця автоматично.")}</div></div>
  const s = data.summary
  const items = data.items.filter((i) => !level || i.level === level)
  return (
    <>
      <div className="dashboard-stats mb-lg">
        <div className={`stat-card ${s.high ? 'danger' : ''}`} onClick={() => setLevel(level === 'high' ? '' : 'high')} style={{ cursor: 'pointer' }}>
          <div className="stat-value">{s.high}</div><div className="stat-label">{tr("Високий ризик")}</div>
        </div>
        <div className={`stat-card ${s.medium ? 'warning' : ''}`} onClick={() => setLevel(level === 'medium' ? '' : 'medium')} style={{ cursor: 'pointer' }}>
          <div className="stat-value">{s.medium}</div><div className="stat-label">{tr("Середній ризик")}</div>
        </div>
        <div className="stat-card" onClick={() => setLevel(level === 'low' ? '' : 'low')} style={{ cursor: 'pointer' }}>
          <div className="stat-value">{s.low}</div><div className="stat-label">{tr("Низький ризик")}</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">≈ {formatNumber(s.expected_failures, 1)}</div>
          <div className="stat-label">{tr("Очікувана кількість несправностей за {0} днів", data.horizon_days)}</div>
        </div>
      </div>
      <div className="card">
        <p className="text-muted pm-model-note">
          {tr("Ймовірність несправності кожного автомобіля протягом {0} днів. Модель: {1}, навчена {2}.", data.horizon_days, tr(data.model), formatDate(data.trained_at, 'dd.MM.yyyy HH:mm'))}
          {level && <> · <button className="btn btn-text btn-sm" onClick={() => setLevel('')}>{tr("Показати всі")}</button></>}
        </p>
        <div className="table-wrapper">
          <table className="data-table pm-table">
            <thead><tr>
              <th>{tr("Автомобіль")}</th><th>{tr("Ймовірність")}</th><th>{tr("Ризик")}</th>
              <th>{tr("Основні чинники")}</th><th>{tr("Рекомендація")}</th>
            </tr></thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.vehicle_id}>
                  <td className="pm-vehicle"><Link to={`/manager/vehicles/${i.vehicle_id}`} className="font-medium pm-link">{i.vehicle_label}</Link>
                    <div className="text-muted">{tr("Використано інтервалу ТО")}: {featureValue('maint_ratio', i.features.maint_ratio)}</div></td>
                  <td><RiskBar p={i.probability} level={i.level} /></td>
                  <td><span className={`status-badge ${LEVELS[i.level].cls}`}>{LEVELS[i.level].label}</span></td>
                  <td><RiskFactors item={i} /></td>
                  <td className="pm-rec">{i.recommendation ? tr(i.recommendation) : <span className="text-muted">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}

function MethodsTable({ methods, best, cost }) {
  return (
    <div className="table-wrapper">
      <table className="data-table pm-metrics">
        <thead><tr>
          <th>{tr("Метод")}</th>
          <th title={tr("Здатність ранжувати: 0.5 - як випадкове вгадування, 1 - ідеально")}>ROC-AUC</th>
          <th title={tr("Площа під кривою точність-повнота; важлива, коли відмов мало")}>PR-AUC</th>
          <th>{tr("Точність")}</th><th>{tr("Повнота")}</th>
          <th title={tr("Частка всіх відмов, що припала на 20 % найризикованіших")}>{tr("Відмов у топ-20 %")}</th>
          {cost ? <><th>{tr("Хибні тривоги")}</th><th>{tr("Пропущено")}</th><th>{tr("Вартість помилок")}</th></>
            : <th title={tr("Середня квадратична похибка ймовірності (менше - краще)")}>Brier</th>}
        </tr></thead>
        <tbody>
          {methods.map((m) => (
            <tr key={m.key} className={m.key === best ? 'pm-best-row' : ''}>
              <td><span className="pm-dot" style={{ background: COLORS[m.key] }} /><span className="font-medium">{tr(m.title)}</span>
                {m.key === best && <span className="pm-best">{tr("найкращий")}</span>}
                {m.detail && <div className="text-muted">{tr(m.detail)}</div>}</td>
              <td>{m.roc_auc.toFixed(3)}</td><td>{m.pr_auc.toFixed(3)}</td>
              <td>{pct(m.at_threshold.precision)}</td><td>{pct(m.at_threshold.recall)}</td>
              <td>{pct(m.top20_capture)}</td>
              {cost ? <><td>{formatNumber(m.at_threshold.fp)}</td><td>{m.at_threshold.fn}</td><td className="font-medium">{formatNumber(m.cost)}</td></>
                : <td>{m.brier.toFixed(3)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Curves({ methods, kind }) {
  const { axis, grid } = useChartColors()
  const roc = kind === 'roc'
  return (
    <div className="pm-chart">
      <div className="pm-chart-title">{roc ? tr("ROC-крива") : tr("Крива точність - повнота")}</div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart margin={{ top: 6, right: 12, bottom: 14, left: -8 }}>
          <CartesianGrid stroke={grid} />
          <XAxis type="number" dataKey="x" domain={[0, 1]} stroke={axis} fontSize={11} tickCount={6}
            label={{ value: roc ? tr("Частка хибних тривог") : tr("Повнота"), position: 'insideBottom', offset: -8, fill: axis, fontSize: 11 }} />
          <YAxis type="number" domain={[0, 1]} stroke={axis} fontSize={11} tickCount={6} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => v.toFixed(3)} labelFormatter={(v) => (roc ? 'FPR ' : 'Recall ') + Number(v).toFixed(3)} />
          {roc && <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke={axis} strokeDasharray="4 4" />}
          {methods.map((m) => (
            <Line key={m.key} data={m[kind]} dataKey="y" name={tr(m.title)} stroke={COLORS[m.key]} strokeWidth={2}
              dot={false} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function Importance({ items }) {
  const { axis, grid } = useChartColors()
  const data = items.filter((i) => i.value > 0).slice(0, 8).map((i) => ({ ...i, name: i.label ? tr(i.label) : i.feature }))
  return (
    <div className="pm-chart">
      <div className="pm-chart-title">{tr("Найважливіші ознаки (на скільки погіршується PR-AUC без ознаки)")}</div>
      <ResponsiveContainer width="100%" height={Math.max(160, data.length * 30 + 30)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={grid} horizontal={false} />
          <XAxis type="number" stroke={axis} fontSize={11} />
          <YAxis type="category" dataKey="name" width={Math.min(240, Math.max(60, ...data.map((d) => d.name.length * 6.2)))} stroke={axis} fontSize={11} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => v.toFixed(3)} />
          <Bar dataKey="value" name={tr("Важливість")} isAnimationActive={false}>
            {data.map((d, i) => <Cell key={d.name} fill={i < 3 ? '#6366f1' : '#a5b4fc'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Calibration({ points }) {
  const { axis, grid } = useChartColors()
  if (!points?.length) return null
  const max = Math.min(1, Math.ceil(Math.max(...points.map((p) => Math.max(p.predicted, p.actual))) * 10 + 0.5) / 10)
  return (
    <div className="pm-chart">
      <div className="pm-chart-title">{tr("Надійність ймовірностей: прогноз vs фактична частка відмов")}</div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={points} margin={{ top: 6, right: 12, bottom: 14, left: -8 }}>
          <CartesianGrid stroke={grid} />
          <XAxis type="number" dataKey="predicted" domain={[0, max]} stroke={axis} fontSize={11} tickFormatter={(v) => pct(v)}
            label={{ value: tr("Прогнозована ймовірність"), position: 'insideBottom', offset: -8, fill: axis, fontSize: 11 }} />
          <YAxis type="number" domain={[0, max]} stroke={axis} fontSize={11} tickFormatter={(v) => pct(v)} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => pct(v, 1)} labelFormatter={(v) => tr("Прогноз {0}", pct(v, 1))} />
          <ReferenceLine segment={[{ x: 0, y: 0 }, { x: max, y: max }]} stroke={axis} strokeDasharray="4 4" />
          <Line dataKey="actual" name={tr("Фактично")} stroke="#10b981" strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function Confusion({ c, title }) {
  return (
    <div>
      <div className="pm-chart-title">{tr("Матриця помилок: {0}", title)}</div>
      <table className="pm-confusion">
        <thead><tr><th /><th>{tr("Прогноз: відмова")}</th><th>{tr("Прогноз: норма")}</th></tr></thead>
        <tbody>
          <tr><th>{tr("Насправді відмова")}</th><td className="ok">{formatNumber(c.tp)}<span>{tr("виявлено")}</span></td>
            <td className="bad">{formatNumber(c.fn)}<span>{tr("пропущено")}</span></td></tr>
          <tr><th>{tr("Насправді норма")}</th><td className="warn">{formatNumber(c.fp)}<span>{tr("зайвий огляд")}</span></td>
            <td className="ok">{formatNumber(c.tn)}<span>{tr("правильно")}</span></td></tr>
        </tbody>
      </table>
      <p className="pm-note">{tr("Модель пропускає лише {0} з {1} відмов ціною {2} зайвих оглядів - для вантажівок це вигідно, бо пропущена відмова в 50 разів дорожча за огляд.",
        c.fn, c.tp + c.fn, formatNumber(c.fp))}</p>
    </div>
  )
}

function Legend({ methods }) {
  return (
    <div className="pm-legend">
      {methods.map((m) => <span key={m.key}><i style={{ background: COLORS[m.key] }} />{tr(m.title)}</span>)}
    </div>
  )
}

function ModelTab() {
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const load = () => predictiveApi.model().then((r) => setData(r.data)).catch(() => setData({ ready: false }))
  useEffect(() => { load() }, [])
  const retrain = async () => {
    setBusy(true)
    try { const r = await predictiveApi.retrain(); toast.success(tr(r.data.message)); await load() } catch { /* interceptor */ }
    setBusy(false)
  }
  if (!data) return <Loader />
  if (!data.ready) return <div className="card"><div className="table-empty">{tr("Недостатньо історії для навчання моделі. Знімки стану автопарку збираються щомісяця автоматично.")}</div></div>
  const ev = data.evaluation
  const best = ev.methods.find((m) => m.key === ev.best)
  const rule = ev.methods.find((m) => m.key === 'rule')
  return (
    <div className="pm-grid">
      <div className="card pm-span">
        <div className="pm-head">
          <div>
            <h3>{tr("Як перевірялася модель")}</h3>
            <p className="text-muted">
              {tr("{0} знімків стану {1} автомобілів (кожні 2 тижні), у {2} випадках протягом {3} днів сталася несправність ({4}).",
                formatNumber(ev.rows), ev.vehicles, ev.positives, ev.horizon_days, pct(ev.base_rate, 1))}{' '}
              {tr("Навчання - на знімках {0} - {1}, перевірка - на останніх 12 місяцях ({2} - {3}), яких модель «не бачила».",
                formatDate(ev.train.from), formatDate(ev.train.to), formatDate(ev.test.from), formatDate(ev.test.to))}
            </p>
            {ev.synthetic > 0 && (
              <p className="pm-warn">
                {ev.live
                  ? tr("Історія містить {0} демонстраційних знімків і {1} реальних. Із накопиченням реальних даних модель перенавчається на них.", ev.synthetic, ev.live)
                  : tr("Історія демонстраційна: її згенеровано імітаційною моделлю зношування для авто цього автопарку. Реальні знімки додаються щомісяця, і модель перенавчається на них. Перевірку на реальних даних див. на вкладці «Перевірка на даних Scania».")}
              </p>
            )}
          </div>
          <button className="btn btn-secondary" onClick={retrain} disabled={busy}>{busy ? tr("Навчаємо...") : tr("Перенавчити модель")}</button>
        </div>
        <MethodsTable methods={ev.methods} best={ev.best} />
        <p className="pm-note">
          {tr("Найкращий метод - {0}: серед 20 % автомобілів з найвищим прогнозованим ризиком опинилося {1} усіх несправностей (правило ТО - {2}). Точність і повнота наведені для порогу, обраного на навчальних даних.",
            tr(best.title), pct(best.top20_capture), pct(rule.top20_capture))}
        </p>
      </div>
      <div className="card"><Curves methods={ev.methods} kind="roc" /><Legend methods={ev.methods} /></div>
      <div className="card"><Curves methods={ev.methods} kind="pr" /><Legend methods={ev.methods} /></div>
      <div className="card"><Importance items={ev.importance} /></div>
      <div className="card"><Calibration points={best.calibration} />
        <p className="pm-note">{tr("Чим ближче зелена лінія до діагоналі, тим точніше ймовірність відповідає реальній частоті несправностей.")}</p></div>
    </div>
  )
}

function ScaniaTab() {
  const [data, setData] = useState(null)
  useEffect(() => { predictiveApi.scania().then((r) => setData(r.data)).catch(() => setData({ ready: false })) }, [])
  if (!data) return <Loader />
  if (!data.ready) {
    return (
      <div className="card"><div className="table-empty">
        {tr("Звіт ще не сформовано. Запустіть у папці backend:")}<pre className="pm-code">venv\Scripts\python.exe -m ml.scania_validate</pre>
      </div></div>
    )
  }
  const r = data.report
  const best = r.methods.find((m) => m.key === r.best)
  const saved = 1 - best.cost / r.cost.no_model
  return (
    <div className="pm-grid">
      <div className="card pm-span">
        <h3>{tr("Перевірка методів на реальних даних Scania")}</h3>
        <p className="text-muted">
          {tr("Набір «APS Failure at Scania Trucks» (Scania CV AB, UCI Machine Learning Repository): показники пневматичної системи реальних вантажівок і відомі відмови. {0} записів для навчання і {1} для перевірки, {2} знеособлених показників, {3} значень пропущено.",
            formatNumber(r.train.n), formatNumber(r.test.n), r.features, pct(r.missing_share))}
        </p>
        <div className="dashboard-stats pm-scania-stats">
          <div className="stat-card"><div className="stat-value">{r.test.positives}</div><div className="stat-label">{tr("Відмов у перевірній вибірці ({0})", pct(r.test.positives / r.test.n, 1))}</div></div>
          <div className="stat-card success"><div className="stat-value">{best.at_threshold.tp}</div><div className="stat-label">{tr("Виявлено моделлю «{0}»", tr(best.title))}</div></div>
          <div className="stat-card"><div className="stat-value">{formatNumber(best.cost)}</div><div className="stat-label">{tr("Вартість помилок (без моделі - {0})", formatNumber(r.cost.no_model))}</div></div>
          <div className="stat-card success"><div className="stat-value">{pct(saved)}</div><div className="stat-label">{tr("Економія порівняно з роботою без прогнозу")}</div></div>
        </div>
        <MethodsTable methods={r.methods} best={r.best} cost />
        <p className="pm-note">
          {tr("Вартість помилок за умовою Scania: зайвий огляд (хибна тривога) - {0} умовних одиниць, пропущена відмова - {1}. Поріг кожного методу обрано за навчальними даними (5-кратна перехресна перевірка), а результат виміряно на окремій перевірній вибірці.", r.cost.fp, r.cost.fn)}
        </p>
      </div>
      <div className="card"><Curves methods={r.methods} kind="roc" /><Legend methods={r.methods} /></div>
      <div className="card"><Curves methods={r.methods} kind="pr" /><Legend methods={r.methods} /></div>
      {best.importance && <div className="card"><Importance items={best.importance} />
        <p className="pm-note">{tr("Назви показників знеособлені виробником (наприклад, ag_002 - один з інтервалів гістограми). Реальна користь моделі - у ранжуванні вантажівок за ризиком.")}</p></div>}
      <div className="card"><Confusion c={best.at_threshold} title={tr(best.title)} /></div>
      <div className="card pm-span pm-source">
        {tr("Джерело: Scania CV AB, «APS Failure at Scania Trucks», UCI Machine Learning Repository, 2016 (ліцензія GPL-3). Дані в систему не входять; звіт сформовано скриптом backend/ml/scania_validate.py {0}.", formatDate(r.generated_at, 'dd.MM.yyyy'))}
      </div>
    </div>
  )
}

function Predictive() {
  const [tab, setTab] = useState('risk')
  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>{tr("Прогноз несправностей")}</h1>
          <p className="text-muted">{tr("Машинне навчання на історії автопарку: які автомобілі найімовірніше потребуватимуть ремонту найближчим часом.")}</p>
        </div>
      </div>
      <div className="tabs">
        <button className={`tab ${tab === 'risk' ? 'active' : ''}`} onClick={() => setTab('risk')}>{tr("Ризик по автопарку")}</button>
        <button className={`tab ${tab === 'model' ? 'active' : ''}`} onClick={() => setTab('model')}>{tr("Якість моделі")}</button>
        <button className={`tab ${tab === 'scania' ? 'active' : ''}`} onClick={() => setTab('scania')}>{tr("Перевірка на даних Scania")}</button>
      </div>
      {tab === 'risk' ? <RiskTab /> : tab === 'model' ? <ModelTab /> : <ScaniaTab />}
    </div>
  )
}

export default Predictive
