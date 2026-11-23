import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { partsApi } from '../../api/parts'
import DataTable from '../../components/DataTable'
import Loader from '../../components/Loader'
import { formatCurrency, formatDateTime, formatNumber } from '../../utils/formatters'
import { tr } from '../../i18n'

const CATEGORIES = {
  brakes: tr("Гальма"), filters: tr("Фільтри"), oils: tr("Мастила та рідини"), engine: tr("Двигун"),
  electrical: tr("Електрика"), suspension: tr("Підвіска"), tyres: tr("Шини"), other: tr("Інше"),
}
const UNITS = ['шт', 'л', 'компл.']
const EMPTY_PART = { name: '', article: '', category: 'other', unit: 'шт', quantity: '', min_quantity: '', price: '' }

const num = (v) => (v === '' || v === null || v === undefined ? undefined : Number(v))

function PartsPage() {
  const [parts, setParts] = useState([])
  const [summary, setSummary] = useState(null)
  const [onlyLow, setOnlyLow] = useState(false)
  const [loading, setLoading] = useState(true)
  const [newPart, setNewPart] = useState(null)       // форма нової запчастини
  const [selected, setSelected] = useState(null)     // картка запчастини (надходження + рух)
  const [movements, setMovements] = useState([])
  const [receipt, setReceipt] = useState({ quantity: '', price: '', note: '' })
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await partsApi.getAll(onlyLow ? { low: 'true' } : {})
      setParts(res.data.parts)
      setSummary(res.data.summary)
    } catch (e) { /* обробляється в interceptor */ }
    setLoading(false)
  }

  useEffect(() => { load() }, [onlyLow])

  const openPart = async (part) => {
    setSelected(part)
    setReceipt({ quantity: '', price: part.price ?? '', note: '' })
    setMovements([])
    try {
      const res = await partsApi.getMovements(part._id)
      setMovements(res.data.movements)
    } catch (e) { /* ignore */ }
  }

  const createPart = async () => {
    if (!newPart.name.trim()) { toast.error(tr("Вкажіть назву запчастини")); return }
    setSaving(true)
    try {
      await partsApi.create({
        name: newPart.name.trim(), article: newPart.article.trim() || null, category: newPart.category,
        unit: newPart.unit, quantity: num(newPart.quantity) ?? 0, min_quantity: num(newPart.min_quantity) ?? 0,
        price: num(newPart.price) ?? 0,
      })
      toast.success(tr("Запчастину додано"))
      setNewPart(null)
      load()
    } catch (e) { /* ignore */ }
    setSaving(false)
  }

  const receive = async () => {
    if (!(Number(receipt.quantity) > 0)) { toast.error(tr("Кількість має бути більше 0")); return }
    setSaving(true)
    try {
      const res = await partsApi.receive(selected._id, {
        quantity: Number(receipt.quantity), price: num(receipt.price) ?? null, note: receipt.note || null,
      })
      toast.success(tr("Надходження оформлено"))
      await load()
      openPart(res.data.part)
    } catch (e) { /* ignore */ }
    setSaving(false)
  }

  const columns = [
    {
      key: 'name', label: tr("Найменування"),
      render: (_, row) => (
        <div>
          <div className="font-medium">{row.name}</div>
          {row.article && <div className="text-muted" style={{ fontSize: '0.8125rem' }}>{row.article}</div>}
        </div>
      ),
    },
    { key: 'category', label: tr("Категорія"), render: (v) => CATEGORIES[v] || v, sortValue: (r) => CATEGORIES[r.category] || r.category },
    {
      key: 'quantity', label: tr("Залишок"),
      render: (v, row) => (
        <span className={row.is_low ? 'text-danger font-bold' : ''}>
          {formatNumber(v, Number.isInteger(v) ? 0 : 1)} {tr(row.unit)}
        </span>
      ),
    },
    { key: 'min_quantity', label: tr("Мінімум"), render: (v, row) => `${formatNumber(v)} ${tr(row.unit)}` },
    { key: 'price', label: tr("Ціна"), render: (v) => formatCurrency(v) },
    { key: 'stock_value', label: tr("Вартість залишку"), render: (v) => formatCurrency(v) },
    {
      key: 'is_low', label: tr("Стан"),
      sortValue: (r) => (r.is_low ? 0 : 1),
      render: (v) => <span className={`status-badge status-${v ? 'red' : 'green'}`}>{v ? tr("Закінчується") : tr("Достатньо")}</span>,
    },
  ]

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{tr("Склад запчастин")}</h1>
        <button className="btn btn-primary" onClick={() => setNewPart({ ...EMPTY_PART })}>{tr("Додати запчастину")}</button>
      </div>

      {summary && (
        <div className="dashboard-stats">
          <div className="stat-card">
            <div className="stat-value">{summary.total}</div>
            <div className="stat-label">{tr("Позицій на складі")}</div>
          </div>
          <div className={`stat-card ${summary.low > 0 ? 'danger' : ''}`} onClick={() => setOnlyLow(!onlyLow)} style={{ cursor: 'pointer' }}>
            <div className="stat-value">{summary.low}</div>
            <div className="stat-label">{tr("Закінчуються")}</div>
            <div className="text-muted mt-sm" style={{ fontSize: '0.8125rem' }}>
              {onlyLow ? tr("Показати всі") : tr("Показати лише їх")}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{formatCurrency(summary.stock_value)}</div>
            <div className="stat-label">{tr("Вартість складу")}</div>
          </div>
        </div>
      )}

      <div className="card">
        {loading ? <Loader text={tr("Завантаження...")} /> : (
          <DataTable columns={columns} data={parts} onRowClick={openPart}
            emptyMessage={onlyLow ? tr("Усі запчастини в достатній кількості") : tr("Склад порожній")}
            searchPlaceholder={tr("Пошук за назвою або артикулом...")} />
        )}
      </div>

      {newPart && (
        <div className="modal-overlay" onClick={() => setNewPart(null)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header"><h3>{tr("Нова запчастина")}</h3></div>
            <div className="modal-body">
              <div className="form-row">
                <div className="form-field">
                  <label>{tr("Найменування *")}</label>
                  <input className="form-control" value={newPart.name} onChange={(e) => setNewPart({ ...newPart, name: e.target.value })} />
                </div>
                <div className="form-field">
                  <label>{tr("Артикул")}</label>
                  <input className="form-control" value={newPart.article} onChange={(e) => setNewPart({ ...newPart, article: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-field">
                  <label>{tr("Категорія")}</label>
                  <select className="form-control" value={newPart.category} onChange={(e) => setNewPart({ ...newPart, category: e.target.value })}>
                    {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div className="form-field">
                  <label>{tr("Одиниця виміру")}</label>
                  <select className="form-control" value={newPart.unit} onChange={(e) => setNewPart({ ...newPart, unit: e.target.value })}>
                    {UNITS.map((u) => <option key={u} value={u}>{tr(u)}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-field">
                  <label>{tr("Початковий залишок")}</label>
                  <input type="number" min="0" className="form-control" value={newPart.quantity} onChange={(e) => setNewPart({ ...newPart, quantity: e.target.value })} />
                </div>
                <div className="form-field">
                  <label>{tr("Мінімальний залишок")}</label>
                  <input type="number" min="0" className="form-control" value={newPart.min_quantity} onChange={(e) => setNewPart({ ...newPart, min_quantity: e.target.value })} />
                  <div className="form-hint">{tr("Нижче цього рівня система надішле попередження")}</div>
                </div>
                <div className="form-field">
                  <label>{tr("Ціна за одиницю (грн)")}</label>
                  <input type="number" min="0" className="form-control" value={newPart.price} onChange={(e) => setNewPart({ ...newPart, price: e.target.value })} />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setNewPart(null)}>{tr("Скасувати")}</button>
              <button className="btn btn-primary" onClick={createPart} disabled={saving}>{saving ? tr("Збереження...") : tr("Додати")}</button>
            </div>
          </div>
        </div>
      )}

      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selected.name}</h3>
              <button className="modal-close" onClick={() => setSelected(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <p className="text-muted">
                {tr("Залишок")}: <b className={selected.is_low ? 'text-danger' : ''}>{formatNumber(selected.quantity)} {tr(selected.unit)}</b>
                {' · '}{tr("Мінімум")}: {formatNumber(selected.min_quantity)} {tr(selected.unit)}
                {' · '}{tr("Ціна")}: {formatCurrency(selected.price)}
              </p>
              <h4 className="mt-md">{tr("Надходження на склад")}</h4>
              <div className="form-row">
                <div className="form-field">
                  <label>{tr("Кількість")}</label>
                  <input type="number" min="0" className="form-control" value={receipt.quantity} onChange={(e) => setReceipt({ ...receipt, quantity: e.target.value })} />
                </div>
                <div className="form-field">
                  <label>{tr("Ціна за одиницю (грн)")}</label>
                  <input type="number" min="0" className="form-control" value={receipt.price} onChange={(e) => setReceipt({ ...receipt, price: e.target.value })} />
                </div>
                <div className="form-field">
                  <label>{tr("Примітка")}</label>
                  <input className="form-control" value={receipt.note} onChange={(e) => setReceipt({ ...receipt, note: e.target.value })} placeholder={tr("Постачальник, накладна...")} />
                </div>
              </div>
              <button className="btn btn-success" onClick={receive} disabled={saving}>{tr("Оформити надходження")}</button>

              <h4 className="mt-lg">{tr("Рух запчастини")}</h4>
              {movements.length === 0 ? <div className="empty-state small">{tr("Немає записів")}</div> : (
                <ul className="list">
                  {movements.map((m) => (
                    <li key={m._id} className="list-item">
                      <div className="item-main">
                        <span className={`item-title ${m.type === 'in' ? 'text-success' : 'text-danger'}`}>
                          {m.type === 'in' ? '+' : '−'}{formatNumber(m.quantity)} {tr(selected.unit)}
                          {' '}{m.type === 'in' ? tr("надходження") : tr("списання")}
                          {m.repair_number ? ` · ${tr("ремонт")} ${m.repair_number}` : ''}
                        </span>
                        <span className="item-subtitle">{formatDateTime(m.created_at)}{m.note ? ` · ${tr(m.note)}` : ''}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PartsPage
