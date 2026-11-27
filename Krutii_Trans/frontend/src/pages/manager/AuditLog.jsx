import { Fragment, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { auditApi } from '../../api/audit'
import Loader from '../../components/Loader'
import { formatDate, pluralize } from '../../utils/formatters'
import { downloadXlsx } from '../../utils/xlsx'
import { fileDate } from '../../utils/exportReport'
import { tr } from '../../i18n'

// Категорії подій: назва, колір і значок
const CATEGORIES = {
  login: { label: tr("Вхід"), color: '#2563eb', icon: '→' },
  logout: { label: tr("Вихід"), color: '#64748b', icon: '←' },
  security: { label: tr("Безпека"), color: '#dc2626', icon: '🔒' },
  user: { label: tr("Користувачі"), color: '#7c3aed', icon: '👤' },
  vehicle: { label: tr("Автопарк"), color: '#0891b2', icon: '🚚' },
  waybill: { label: tr("Путівки"), color: '#4f46e5', icon: '📄' },
  fuel: { label: tr("Паливо"), color: '#ca8a04', icon: '⛽' },
  fault: { label: tr("Несправності"), color: '#ea580c', icon: '⚠' },
  repair: { label: tr("Ремонти"), color: '#059669', icon: '🔧' },
  part: { label: tr("Склад"), color: '#9333ea', icon: '📦' },
  settings: { label: tr("Налаштування"), color: '#475569', icon: '⚙' },
}
const ROLES = { manager: tr("Керівник"), mechanic: tr("Механік"), driver: tr("Водій") }

// Людські назви полів у «було -> стало»
const FIELDS = {
  status: tr("Статус"), odometer: tr("Пробіг"), fuel_norm: tr("Норма пального"), fuel_type: tr("Тип пального"),
  plate_number: tr("Номерний знак"), brand: tr("Марка"), model: tr("Модель"), year: tr("Рік випуску"), vin: 'VIN',
  next_maintenance_km: tr("Наступне ТО (км)"), next_maintenance_date: tr("Наступне ТО (дата)"),
  last_maintenance_km: tr("Останнє ТО (км)"), last_maintenance_date: tr("Останнє ТО (дата)"),
  insurance_policy: tr("Страховий поліс"), insurance_expiry: tr("Страховка до"), inspection_expiry: tr("Техогляд до"),
  full_name: tr("ПІБ"), phone: tr("Телефон"), email: 'Email', role: tr("Роль"), is_active: tr("Активний"),
  license_number: tr("Номер посвідчення"), license_expiry: tr("Посвідчення до"), password: tr("Пароль"),
  severity: tr("Критичність"), category: tr("Категорія"), description: tr("Опис"), resolution: tr("Рішення"),
  rejection_reason: tr("Причина відхилення"), acknowledged_by: tr("Прийняв"), acknowledged_at: tr("Час прийняття"),
  resolved_at: tr("Час вирішення"), repair_id: tr("Ремонт"), photos: tr("Фото (кількість)"),
  mechanic_id: tr("Механік"), scheduled_date: tr("Запланована дата"), started_at: tr("Початок"), completed_at: tr("Завершення"),
  work_performed: tr("Виконані роботи"), parts_used: tr("Запчастини"), labor_hours: tr("Години роботи"),
  labor_cost: tr("Вартість роботи"), parts_cost: tr("Вартість запчастин"), cancellation_reason: tr("Причина скасування"),
  notes: tr("Примітки"), odometer_start: tr("Пробіг на виїзді"), odometer_end: tr("Пробіг на поверненні"),
  fuel_issued: tr("Видано пального"), fuel_used: tr("Витрачено пального"), fuel_remaining: tr("Залишок пального"),
  completion_notes: tr("Примітки водія"), quantity: tr("Кількість"), min_quantity: tr("Мінімальний залишок"),
  price: tr("Ціна"), name: tr("Назва"), article: tr("Артикул"),
  maintenance_warning_km: tr("Попередження про ТО (км)"), maintenance_warning_days: tr("Попередження про ТО (днів)"),
  maintenance_interval_km: tr("Інтервал ТО (км)"), maintenance_interval_days: tr("Інтервал ТО (днів)"),
  default_fuel_norm: tr("Норма пального за замовч."), overspend_threshold: tr("Поріг перевитрати"),
  winter_coefficient: tr("Зимовий коефіцієнт"), fault_mechanic_hours: tr("Ескалація механіку (год)"),
  fault_manager_hours: tr("Ескалація керівнику (год)"), company_name: tr("Назва компанії"),
}
const VALUES = {
  active: tr("Активний"), repair: tr("В ремонті"), inspection: tr("На огляді"), decommissioned: tr("Списано"),
  planned: tr("Заплановано"), in_progress: tr("В роботі"), completed: tr("Завершено"), cancelled: tr("Скасовано"),
  new: tr("Нова"), acknowledged: tr("Прийнято"), in_repair: tr("В ремонті"), resolved: tr("Вирішено"), rejected: tr("Відхилено"),
  issued: tr("Видано"), manager: tr("Керівник"), mechanic: tr("Механік"), driver: tr("Водій"),
  так: tr("так"), ні: tr("ні"), змінено: tr("змінено"),
}
const val = (v) => VALUES[v] || v
// куди веде посилання на об'єкт
const LINKS = { vehicle: '/manager/vehicles/', user: '/manager/users/', waybill: '/manager/waybills/', fault: '/manager/faults/', repair: '/manager/repairs/' }

const EMPTY_FILTERS = { q: '', username: '', category: '', status: '', date_from: '', date_to: '' }

function AuditLog() {
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(null)
  const [exporting, setExporting] = useState(false)
  const timer = useRef(null)

  const params = (p = page, limit = 50) => ({ ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)), page: p, limit })

  const load = async () => {
    setLoading(true)
    try {
      const res = await auditApi.getAll(params())
      setData(res.data)
    } catch (e) { /* обробляється в interceptor */ }
    setLoading(false)
  }
  useEffect(() => { load() }, [filters, page])

  // пошук із затримкою, щоб не надсилати запит на кожну літеру
  const onSearch = (v) => {
    setSearch(v)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => { setPage(1); setFilters((f) => ({ ...f, q: v })) }, 400)
  }
  const setFilter = (key, value) => { setPage(1); setOpen(null); setFilters((f) => ({ ...f, [key]: value })) }
  const reset = () => { setSearch(''); setPage(1); setFilters(EMPTY_FILTERS) }
  const showFailedLogins = () => { setPage(1); setFilters({ ...EMPTY_FILTERS, category: 'login', status: 'fail' }) }

  const exportExcel = async () => {
    setExporting(true)
    try {
      const rows = []
      for (let p = 1; p <= 10; p++) {
        const res = await auditApi.getAll(params(p, 100))
        res.data.items.forEach((e) => rows.push([
          formatDate(e.ts, 'dd.MM.yyyy HH:mm:ss'), e.full_name || e.username || '—', ROLES[e.role] || '',
          CATEGORIES[e.category]?.label || e.category, tr(e.action), e.entity_label || '',
          (e.changes || []).map((c) => `${FIELDS[c.field] || c.field}: ${val(c.old)} → ${val(c.new)}`).join('; '),
          e.status === 'success' ? tr("Успішно") : tr("Помилка"), e.error || '', e.ip, e.agent,
        ]))
        if (p >= res.data.pages) break
      }
      downloadXlsx(`zhurnal-dii-${fileDate()}.xlsx`, {
        sheetName: tr("Журнал дій"), title: `KRUTII TRANS – ${tr("Журнал дій")}`,
        subtitle: `${tr("Сформовано:")} ${formatDate(new Date(), 'dd.MM.yyyy HH:mm')}`,
        headers: [tr("Час"), tr("Користувач"), tr("Роль"), tr("Категорія"), tr("Дія"), tr("Об'єкт"), tr("Зміни"), tr("Результат"), tr("Помилка"), 'IP', tr("Пристрій")],
        rows,
      })
    } catch (e) { /* ignore */ }
    setExporting(false)
  }

  const s = data?.summary
  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>{tr("Журнал дій")}</h1>
          <p className="text-muted">{tr("Хто, коли і що змінив у системі. Записи не можна змінити чи видалити.")}</p>
        </div>
        <button className="btn btn-secondary" onClick={exportExcel} disabled={exporting || !data?.total}>
          {exporting ? tr("Готуємо файл...") : 'Excel'}
        </button>
      </div>

      {s && (
        <div className="dashboard-stats">
          <div className="stat-card"><div className="stat-value">{s.events_24h}</div><div className="stat-label">{tr("Подій за 24 год")}</div></div>
          <div className="stat-card"><div className="stat-value">{s.changes_7d}</div><div className="stat-label">{tr("Змін даних за 7 днів")}</div></div>
          <div className={`stat-card ${s.failed_logins_24h ? 'danger' : ''}`} onClick={showFailedLogins} style={{ cursor: 'pointer' }}
            title={tr("Показати невдалі входи")}>
            <div className="stat-value">{s.failed_logins_24h}</div><div className="stat-label">{tr("Невдалих входів за 24 год")}</div>
          </div>
          <div className="stat-card"><div className="stat-value">{s.active_users_24h}</div><div className="stat-label">{tr("Активних користувачів за 24 год")}</div></div>
        </div>
      )}

      <div className="card">
        <div className="audit-filters">
          <input type="search" className="form-control" placeholder={tr("Пошук: дія, об'єкт, користувач, IP...")}
            value={search} onChange={(e) => onSearch(e.target.value)} />
          <select className="form-control" value={filters.username} onChange={(e) => setFilter('username', e.target.value)}>
            <option value="">{tr("Усі користувачі")}</option>
            {(data?.users || []).map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
          <select className="form-control" value={filters.category} onChange={(e) => setFilter('category', e.target.value)}>
            <option value="">{tr("Усі категорії")}</option>
            {Object.entries(CATEGORIES).map(([k, c]) => <option key={k} value={k}>{c.label}</option>)}
          </select>
          <select className="form-control" value={filters.status} onChange={(e) => setFilter('status', e.target.value)}>
            <option value="">{tr("Усі результати")}</option>
            <option value="success">{tr("Успішні")}</option>
            <option value="fail">{tr("Невдалі")}</option>
          </select>
          <input type="date" className="form-control" value={filters.date_from} onChange={(e) => setFilter('date_from', e.target.value)} aria-label={tr("Від")} />
          <input type="date" className="form-control" value={filters.date_to} onChange={(e) => setFilter('date_to', e.target.value)} aria-label={tr("До")} />
          <button className="btn btn-text" onClick={reset}>{tr("Скинути")}</button>
        </div>

        {loading && !data ? <Loader text={tr("Завантаження...")} /> : !data?.items.length ? (
          <div className="table-empty">{tr("Подій не знайдено")}</div>
        ) : (
          <>
            <div className="table-wrapper">
              <table className="data-table audit-table">
                <thead>
                  <tr>
                    <th>{tr("Час")}</th><th>{tr("Користувач")}</th><th>{tr("Дія")}</th><th>{tr("Об'єкт")}</th>
                    <th>{tr("Зміни")}</th><th>{tr("IP / пристрій")}</th><th>{tr("Результат")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((e) => {
                    const cat = CATEGORIES[e.category] || { label: e.category, color: '#64748b', icon: '•' }
                    const hasChanges = e.changes?.length > 0
                    const link = LINKS[e.entity_type] && e.entity_id ? LINKS[e.entity_type] + e.entity_id : null
                    return (
                      <Fragment key={e._id}>
                        <tr className={`${e.status === 'fail' ? 'audit-fail' : ''} ${hasChanges ? 'audit-clickable' : ''}`}
                          onClick={() => hasChanges && setOpen(open === e._id ? null : e._id)}>
                          <td className="audit-time">
                            <div>{formatDate(e.ts, 'dd.MM.yyyy')}</div>
                            <div className="text-muted">{formatDate(e.ts, 'HH:mm:ss')}</div>
                          </td>
                          <td>
                            <div className="font-medium">{e.full_name || e.username || '—'}</div>
                            <div className="text-muted">{e.username}{e.role ? ` · ${ROLES[e.role]}` : ''}</div>
                          </td>
                          <td>
                            <span className="audit-cat" style={{ '--cat': cat.color }}>{cat.icon} {cat.label}</span>
                            <div>{tr(e.action)}</div>
                          </td>
                          <td>{link ? <Link to={link} onClick={(ev) => ev.stopPropagation()}>{e.entity_label}</Link> : (e.entity_label || '—')}</td>
                          <td>
                            {hasChanges
                              ? <button type="button" className="audit-changes-btn">{e.changes.length} {pluralize(e.changes.length, [tr("зміна"), tr("зміни"), tr("змін")])} {open === e._id ? '▲' : '▼'}</button>
                              : <span className="text-muted">—</span>}
                          </td>
                          <td><div>{e.ip}</div><div className="text-muted">{e.agent}</div></td>
                          <td>
                            {e.status === 'success'
                              ? <span className="status-badge status-success">{tr("Успішно")}</span>
                              : <span className="status-badge status-danger" title={e.error ? tr(e.error) : ''}>{tr("Помилка")}</span>}
                            {e.status === 'fail' && e.error && <div className="audit-error">{tr(e.error)}</div>}
                          </td>
                        </tr>
                        {open === e._id && (
                          <tr className="audit-diff-row">
                            <td colSpan={7}>
                              <table className="audit-diff">
                                <thead><tr><th>{tr("Поле")}</th><th>{tr("Було")}</th><th></th><th>{tr("Стало")}</th></tr></thead>
                                <tbody>
                                  {e.changes.map((c) => (
                                    <tr key={c.field}>
                                      <td>{FIELDS[c.field] || c.field}</td>
                                      <td><span className="audit-old">{val(c.old)}</span></td>
                                      <td className="text-muted">→</td>
                                      <td><span className="audit-new">{val(c.new)}</span></td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="audit-pager">
              <span className="text-muted">{tr("Знайдено подій: {0}", data.total)}</span>
              <div>
                <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>←</button>
                <span className="audit-page">{tr("Сторінка {0} з {1}", data.page, data.pages)}</span>
                <button className="btn btn-secondary btn-sm" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>→</button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default AuditLog
